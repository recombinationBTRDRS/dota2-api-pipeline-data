# services/ingestion/tests/db/test_computed_repository.py
"""Unit + integration тести для Epic 5 pre-computed layer.

Покриває:
  - rebuild_hero_stats()       (Issue 5.2)
  - rebuild_item_builds()      (Issue 5.3)
  - ComputedStatsRepository    (Issue 5.7)
"""
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.repositories.analytics.computed import ComputedStatsRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork

# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


# ── seed helpers ──────────────────────────────────────────────────────────────

def _seed_hero(conn, hero_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO heroes (id, name, localized_name, primary_attr, attack_type) "
        "VALUES (?, ?, ?, 'agi', 'Melee')",
        (hero_id, f"npc_dota_hero_{name}", name),
    )


def _seed_role_score(conn, hero_id: int, primary_pos: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO hero_role_scores "
        "(hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos) "
        "VALUES (?, 3, 3, 3, 3, 3, 5, ?)",
        (hero_id, primary_pos),
    )


def _seed_item(conn, item_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO items (id, name, localized_name, cost) VALUES (?, ?, ?, 0)",
        (item_id, f"item_{name}", name),
    )


def _seed_match(conn, match_id: int, patch: int | None = None, region: int | None = None) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win, patch, region) "
        "VALUES (?, 1700000000, 2400, 1, ?, ?)",
        (match_id, patch, region),
    )


def _seed_mp(
    conn,
    match_id: int,
    slot: int,
    hero_id: int,
    win: bool,
    gpm: int = 500,
    xpm: int = 600,
    kills: int = 5,
    deaths: int = 2,
    assists: int = 8,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_players "
        "(match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (match_id, slot, hero_id, kills, deaths, assists, gpm, xpm, int(win)),
    )


def _seed_item_for_player(conn, match_id: int, slot: int, item_id: int, item_slot: int = 0) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_player_items (match_id, player_slot, slot, item_id) "
        "VALUES (?, ?, ?, ?)",
        (match_id, slot, item_slot, item_id),
    )


def _do_seed(conn, *, heroes: list[tuple], matches: int, win_until: int) -> None:
    """Швидкий seed: список (hero_id, name, pos), N матчів, win для перших win_until."""
    for hero_id, name, pos in heroes:
        _seed_hero(conn, hero_id, name)
        _seed_role_score(conn, hero_id, pos)
    for i in range(1, matches + 1):
        _seed_match(conn, i)
        for slot, (hero_id, _, _) in enumerate(heroes):
            _seed_mp(conn, i, slot, hero_id, win=(i <= win_until))
    conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# rebuild_hero_stats (Issue 5.2)
# ══════════════════════════════════════════════════════════════════════════════

def test_rebuild_hero_stats_returns_zero_no_data(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats
    result = rebuild_hero_stats()
    assert result == 0


def test_rebuild_hero_stats_returns_row_count(db) -> None:
    """1 герой, 1 позиція, без patch/region → 1 рядок."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=5, win_until=3)

    count = rebuild_hero_stats()
    assert count == 1


def test_rebuild_hero_stats_correct_winrate(db) -> None:
    """3 wins з 5 матчів → winrate = 0.6."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=5, win_until=3)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        row = uow.conn.execute(
            "SELECT matches_played, wins FROM hero_stats_computed WHERE hero_id = 1"
        ).fetchone()

    assert row["matches_played"] == 5
    assert row["wins"] == 3


def test_rebuild_hero_stats_groups_by_patch(db) -> None:
    """Різні patch → окремі рядки в hero_stats_computed."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, 1, 1)
        _seed_match(uow.conn, 1, patch=38)
        _seed_match(uow.conn, 2, patch=39)
        _seed_mp(uow.conn, 1, 0, 1, win=True)
        _seed_mp(uow.conn, 2, 0, 1, win=False)
        uow.conn.commit()

    count = rebuild_hero_stats()
    assert count == 2  # patch=38 і patch=39 — два окремих рядки

    with UnitOfWork() as uow:
        rows = uow.conn.execute(
            "SELECT patch, wins FROM hero_stats_computed WHERE hero_id = 1 ORDER BY patch"
        ).fetchall()
    assert rows[0]["patch"] == 38
    assert rows[0]["wins"] == 1
    assert rows[1]["patch"] == 39
    assert rows[1]["wins"] == 0


def test_rebuild_hero_stats_idempotent(db) -> None:
    """Двічі rebuild → той самий результат, не подвоюються рядки."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=5, win_until=3)

    rebuild_hero_stats()
    rebuild_hero_stats()

    with UnitOfWork() as uow:
        count = uow.conn.execute(
            "SELECT COUNT(*) FROM hero_stats_computed WHERE hero_id = 1"
        ).fetchone()[0]
    assert count == 1


def test_rebuild_hero_stats_computed_at_set(db) -> None:
    """computed_at заповнений і є unix timestamp > 0."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=3, win_until=2)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        row = uow.conn.execute(
            "SELECT computed_at FROM hero_stats_computed"
        ).fetchone()
    assert row["computed_at"] > 0


def test_rebuild_hero_stats_hero_without_role_scores_excluded(db) -> None:
    """Герой без hero_role_scores не потрапляє в computed таблицю."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        # Без role scores
        _seed_match(uow.conn, 1)
        _seed_mp(uow.conn, 1, 0, 1, win=True)
        uow.conn.commit()

    count = rebuild_hero_stats()
    assert count == 0


# ══════════════════════════════════════════════════════════════════════════════
# rebuild_item_builds (Issue 5.3)
# ══════════════════════════════════════════════════════════════════════════════

def test_rebuild_item_builds_returns_zero_no_data(db) -> None:
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds
    assert rebuild_item_builds() == 0


def test_rebuild_item_builds_returns_row_count(db) -> None:
    """1 герой, 1 item → 1 рядок."""
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, 1, 1)
        _seed_item(uow.conn, 10, "Blink Dagger")
        _seed_match(uow.conn, 1)
        _seed_mp(uow.conn, 1, 0, 1, win=True)
        _seed_item_for_player(uow.conn, 1, 0, 10)
        uow.conn.commit()

    count = rebuild_item_builds()
    assert count == 1


def test_rebuild_item_builds_times_bought_and_won(db) -> None:
    """2 матчі, item в обох, win тільки в першому → times_bought=2, times_won=1."""
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, 1, 1)
        _seed_item(uow.conn, 10, "Blink Dagger")
        for i in range(1, 3):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 0, 1, win=(i == 1))
            _seed_item_for_player(uow.conn, i, 0, 10)
        uow.conn.commit()

    rebuild_item_builds()

    with UnitOfWork() as uow:
        row = uow.conn.execute(
            "SELECT times_bought, times_won FROM hero_item_build_computed "
            "WHERE hero_id = 1 AND item_id = 10"
        ).fetchone()

    assert row["times_bought"] == 2
    assert row["times_won"] == 1


def test_rebuild_item_builds_idempotent(db) -> None:
    """Двічі rebuild → рядки не подвоюються."""
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, 1, 1)
        _seed_item(uow.conn, 10, "Blink Dagger")
        _seed_match(uow.conn, 1)
        _seed_mp(uow.conn, 1, 0, 1, win=True)
        _seed_item_for_player(uow.conn, 1, 0, 10)
        uow.conn.commit()

    rebuild_item_builds()
    rebuild_item_builds()

    with UnitOfWork() as uow:
        count = uow.conn.execute(
            "SELECT COUNT(*) FROM hero_item_build_computed"
        ).fetchone()[0]
    assert count == 1


def test_rebuild_item_builds_multiple_items(db) -> None:
    """Герой з 3 різними items → 3 рядки."""
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, 1, 1)
        for i in range(1, 4):
            _seed_item(uow.conn, i, f"item_{i}")
        _seed_match(uow.conn, 1)
        _seed_mp(uow.conn, 1, 0, 1, win=True)
        for i in range(1, 4):
            _seed_item_for_player(uow.conn, 1, 0, i, item_slot=i - 1)
        uow.conn.commit()

    count = rebuild_item_builds()
    assert count == 3


# ══════════════════════════════════════════════════════════════════════════════
# ComputedStatsRepository (Issue 5.7)
# ══════════════════════════════════════════════════════════════════════════════

def test_computed_repo_get_hero_stats_empty_before_rebuild(db) -> None:
    """Перед rebuild — пусто."""
    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_hero_stats(1)
    assert rows == []


def test_computed_repo_get_hero_stats_after_rebuild(db) -> None:
    """Після rebuild повертає правильний winrate."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=4, win_until=3)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_hero_stats(1)

    assert len(rows) == 1
    row = rows[0]
    assert row.hero_id == 1
    assert row.matches_played == 4
    assert row.wins == 3
    assert row.losses == 1
    assert row.winrate == 0.75
    assert row.primary_pos == 1


def test_computed_repo_get_hero_stats_invalid_id_raises(db) -> None:
    with UnitOfWork() as uow:
        with pytest.raises(ValueError, match="hero_id must be int > 0"):
            ComputedStatsRepository(uow.conn).get_hero_stats(0)

    with UnitOfWork() as uow:
        with pytest.raises(ValueError, match="hero_id must be int > 0"):
            ComputedStatsRepository(uow.conn).get_hero_stats(-1)


def test_computed_repo_get_hero_stats_filter_by_patch(db) -> None:
    """patch фільтр повертає тільки рядки з вказаним patch."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, 1, 1)
        _seed_match(uow.conn, 1, patch=38)
        _seed_match(uow.conn, 2, patch=39)
        _seed_mp(uow.conn, 1, 0, 1, win=True)
        _seed_mp(uow.conn, 2, 0, 1, win=True)
        uow.conn.commit()

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_hero_stats(1, patch=38)

    assert len(rows) == 1
    assert rows[0].patch == 38


def test_computed_repo_get_top_by_winrate_sorted(db) -> None:
    """Топ відсортований winrate DESC."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        # Anti-Mage: 3/5 = 0.6
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=5, win_until=3)
        # Axe: 4/5 = 0.8
        _seed_hero(uow.conn, 2, "Axe")
        _seed_role_score(uow.conn, 2, 3)
        for i in range(10, 15):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 1, 2, win=(i < 14))
        uow.conn.commit()

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_top_by_winrate(min_matches=1)

    assert len(rows) == 2
    assert rows[0].hero_id == 2   # Axe: 0.8
    assert rows[1].hero_id == 1   # AM: 0.6
    assert rows[0].winrate > rows[1].winrate


def test_computed_repo_get_top_by_winrate_min_matches_filter(db) -> None:
    """min_matches виключає героїв з малою вибіркою."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=3, win_until=3)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_top_by_winrate(min_matches=5)

    assert rows == []


def test_computed_repo_get_top_by_winrate_invalid_args_raise(db) -> None:
    with UnitOfWork() as uow:
        repo = ComputedStatsRepository(uow.conn)
        with pytest.raises(ValueError):
            repo.get_top_by_winrate(min_matches=-1)
        with pytest.raises(ValueError):
            repo.get_top_by_winrate(limit=0)
        with pytest.raises(ValueError):
            repo.get_top_by_winrate(primary_pos=6)


def test_computed_repo_get_item_build_after_rebuild(db) -> None:
    """Після rebuild item build повертає правильні counts."""
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, 1, 1)
        _seed_item(uow.conn, 10, "Blink Dagger")
        for i in range(1, 4):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 0, 1, win=(i <= 2))
            _seed_item_for_player(uow.conn, i, 0, 10)
        uow.conn.commit()

    rebuild_item_builds()

    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_item_build(1, primary_pos=1)

    assert len(rows) == 1
    assert rows[0].item_id == 10
    assert rows[0].times_bought == 3
    assert rows[0].times_won == 2
    assert rows[0].win_rate == round(2 / 3, 4)


def test_computed_repo_get_item_build_invalid_args_raise(db) -> None:
    with UnitOfWork() as uow:
        repo = ComputedStatsRepository(uow.conn)
        with pytest.raises(ValueError):
            repo.get_item_build(0, primary_pos=1)
        with pytest.raises(ValueError):
            repo.get_item_build(1, primary_pos=6)
        with pytest.raises(ValueError):
            repo.get_item_build(1, primary_pos=1, limit=0)


def test_computed_repo_staleness_none_before_rebuild(db) -> None:
    """computed_at = None якщо rebuild не запускався."""
    with UnitOfWork() as uow:
        staleness = ComputedStatsRepository(uow.conn).get_staleness()

    assert staleness["hero_stats_computed"] is None
    assert staleness["hero_item_build_computed"] is None


def test_computed_repo_staleness_set_after_rebuild(db) -> None:
    """Після rebuild computed_at > 0."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=2, win_until=1)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        staleness = ComputedStatsRepository(uow.conn).get_staleness()

    assert staleness["hero_stats_computed"] is not None
    assert staleness["hero_stats_computed"] > 0