# services/ingestion/tests/db/test_computed_repository.py
"""Unit + integration тести для Epic 5 pre-computed layer."""
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.repositories.analytics.computed import ComputedStatsRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.tests.seed_helpers import (
    seed_hero,
    seed_item,
    seed_item_slot,
    seed_match,
    seed_mp,
    seed_role_score,
)


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def _do_seed(conn, *, heroes: list[tuple], matches: int, win_until: int) -> None:
    for hero_id, name, pos in heroes:
        seed_hero(conn, hero_id, name)
        seed_role_score(conn, hero_id, pos)
    for i in range(1, matches + 1):
        seed_match(conn, i)
        for slot, (hero_id, _, _) in enumerate(heroes):
            seed_mp(conn, i, slot, hero_id, win=(i <= win_until))
    conn.commit()


# ── rebuild_hero_stats ────────────────────────────────────────────────────────

def test_rebuild_hero_stats_returns_zero_no_data(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats
    assert rebuild_hero_stats() == 0


def test_rebuild_hero_stats_clears_stale_data_on_empty_source(db) -> None:
    """Навіть якщо нових даних немає — stale рядки видаляються."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=3, win_until=2)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        count_before = uow.conn.execute("SELECT COUNT(*) FROM hero_stats_computed").fetchone()[0]
    assert count_before > 0

    # Видаляємо всі матчі — source порожній
    with UnitOfWork() as uow:
        uow.conn.execute("DELETE FROM match_players")
        uow.conn.execute("DELETE FROM matches")
        uow.conn.commit()

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        count_after = uow.conn.execute("SELECT COUNT(*) FROM hero_stats_computed").fetchone()[0]
    assert count_after == 0  # stale дані очищені


def test_rebuild_hero_stats_rollup_rows_generated(db) -> None:
    """UNION ALL rollups: для 1 героя з patch і region маємо 4 рядки (granular + 3 rollups)."""
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_role_score(uow.conn, 1, 1)
        seed_match(uow.conn, 1, patch=38, region=3)
        seed_mp(uow.conn, 1, 0, 1, win=True)
        uow.conn.commit()

    count = rebuild_hero_stats()
    # granular(38,3) + rollup(38,NULL) + rollup(NULL,3) + rollup(NULL,NULL) = 4
    assert count == 4

    with UnitOfWork() as uow:
        global_row = uow.conn.execute(
            "SELECT matches_played, wins FROM hero_stats_computed "
            "WHERE hero_id=1 AND patch IS NULL AND region IS NULL"
        ).fetchone()
    assert global_row is not None
    assert global_row["matches_played"] == 1
    assert global_row["wins"] == 1


def test_rebuild_hero_stats_returns_row_count(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=5, win_until=3)

    count = rebuild_hero_stats()
    assert count >= 1  # мінімум rollup (NULL, NULL)


def test_rebuild_hero_stats_correct_winrate(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=5, win_until=3)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        row = uow.conn.execute(
            "SELECT matches_played, wins FROM hero_stats_computed "
            "WHERE hero_id=1 AND patch IS NULL AND region IS NULL"
        ).fetchone()

    assert row["matches_played"] == 5
    assert row["wins"] == 3


def test_rebuild_hero_stats_idempotent(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=5, win_until=3)

    rebuild_hero_stats()
    rebuild_hero_stats()

    with UnitOfWork() as uow:
        count = uow.conn.execute(
            "SELECT COUNT(*) FROM hero_stats_computed "
            "WHERE hero_id=1 AND patch IS NULL AND region IS NULL"
        ).fetchone()[0]
    assert count == 1


def test_rebuild_hero_stats_computed_at_set(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=3, win_until=2)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        row = uow.conn.execute("SELECT computed_at FROM hero_stats_computed LIMIT 1").fetchone()
    assert row["computed_at"] > 0


def test_rebuild_hero_stats_hero_without_role_scores_excluded(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_match(uow.conn, 1)
        seed_mp(uow.conn, 1, 0, 1, win=True)
        uow.conn.commit()

    count = rebuild_hero_stats()
    assert count == 0


# ── rebuild_item_builds ───────────────────────────────────────────────────────

def test_rebuild_item_builds_returns_zero_no_data(db) -> None:
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds
    assert rebuild_item_builds() == 0


def test_rebuild_item_builds_clears_stale_data(db) -> None:
    """При порожньому source stale рядки видаляються."""
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_role_score(uow.conn, 1, 1)
        seed_item(uow.conn, 10, "Blink Dagger")
        seed_match(uow.conn, 1)
        seed_mp(uow.conn, 1, 0, 1, win=True)
        seed_item_slot(uow.conn, 1, 0, 10)
        uow.conn.commit()

    rebuild_item_builds()

    with UnitOfWork() as uow:
        count_before = uow.conn.execute("SELECT COUNT(*) FROM hero_item_build_computed").fetchone()[0]
    assert count_before == 1

    with UnitOfWork() as uow:
        uow.conn.execute("DELETE FROM match_player_items")
        uow.conn.commit()

    rebuild_item_builds()

    with UnitOfWork() as uow:
        count_after = uow.conn.execute("SELECT COUNT(*) FROM hero_item_build_computed").fetchone()[0]
    assert count_after == 0


def test_rebuild_item_builds_times_bought_and_won(db) -> None:
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_role_score(uow.conn, 1, 1)
        seed_item(uow.conn, 10, "Blink Dagger")
        for i in range(1, 3):
            seed_match(uow.conn, i)
            seed_mp(uow.conn, i, 0, 1, win=(i == 1))
            seed_item_slot(uow.conn, i, 0, 10)
        uow.conn.commit()

    rebuild_item_builds()

    with UnitOfWork() as uow:
        row = uow.conn.execute(
            "SELECT times_bought, times_won FROM hero_item_build_computed "
            "WHERE hero_id=1 AND item_id=10"
        ).fetchone()

    assert row["times_bought"] == 2
    assert row["times_won"] == 1


def test_rebuild_item_builds_idempotent(db) -> None:
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_role_score(uow.conn, 1, 1)
        seed_item(uow.conn, 10, "Blink Dagger")
        seed_match(uow.conn, 1)
        seed_mp(uow.conn, 1, 0, 1, win=True)
        seed_item_slot(uow.conn, 1, 0, 10)
        uow.conn.commit()

    rebuild_item_builds()
    rebuild_item_builds()

    with UnitOfWork() as uow:
        count = uow.conn.execute("SELECT COUNT(*) FROM hero_item_build_computed").fetchone()[0]
    assert count == 1


# ── ComputedStatsRepository ───────────────────────────────────────────────────

def test_computed_repo_get_hero_stats_empty_before_rebuild(db) -> None:
    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_hero_stats(1)
    assert rows == []


def test_computed_repo_get_hero_stats_after_rebuild(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=4, win_until=3)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        # global rollup (NULL, NULL)
        rows = ComputedStatsRepository(uow.conn).get_hero_stats(1)

    global_rows = [r for r in rows if r.patch is None and r.region is None]
    assert len(global_rows) == 1
    row = global_rows[0]
    assert row.matches_played == 4
    assert row.wins == 3
    assert row.winrate == 0.75


def test_computed_repo_get_hero_stats_invalid_id_raises(db) -> None:
    with UnitOfWork() as uow:
        with pytest.raises(ValueError, match="hero_id must be int > 0"):
            ComputedStatsRepository(uow.conn).get_hero_stats(0)


def test_computed_repo_get_top_by_winrate_sorted(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=5, win_until=3)
        seed_hero(uow.conn, 2, "Axe")
        seed_role_score(uow.conn, 2, 3)
        for i in range(10, 15):
            seed_match(uow.conn, i)
            seed_mp(uow.conn, i, 1, 2, win=(i < 14))
        uow.conn.commit()

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_top_by_winrate(min_matches=1)

    assert rows[0].winrate >= rows[1].winrate


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
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_role_score(uow.conn, 1, 1)
        seed_item(uow.conn, 10, "Blink Dagger")
        for i in range(1, 4):
            seed_match(uow.conn, i)
            seed_mp(uow.conn, i, 0, 1, win=(i <= 2))
            seed_item_slot(uow.conn, i, 0, 10)
        uow.conn.commit()

    rebuild_item_builds()

    with UnitOfWork() as uow:
        rows = ComputedStatsRepository(uow.conn).get_item_build(1, primary_pos=1)

    assert len(rows) == 1
    assert rows[0].times_bought == 3
    assert rows[0].times_won == 2
    assert rows[0].win_rate == round(2 / 3, 4)


def test_computed_repo_staleness_none_before_rebuild(db) -> None:
    with UnitOfWork() as uow:
        staleness = ComputedStatsRepository(uow.conn).get_staleness()
    assert staleness["hero_stats_computed"] is None
    assert staleness["hero_item_build_computed"] is None


def test_computed_repo_staleness_set_after_rebuild(db) -> None:
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats

    with UnitOfWork() as uow:
        _do_seed(uow.conn, heroes=[(1, "Anti-Mage", 1)], matches=2, win_until=1)

    rebuild_hero_stats()

    with UnitOfWork() as uow:
        staleness = ComputedStatsRepository(uow.conn).get_staleness()
    assert staleness["hero_stats_computed"] is not None
    assert staleness["hero_stats_computed"] > 0