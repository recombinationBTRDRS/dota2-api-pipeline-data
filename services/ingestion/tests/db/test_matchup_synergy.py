# services/ingestion/tests/db/test_matchup_synergy.py
"""Unit + integration тести для Epic 5.4 (matchup) і 5.5 (synergy).

Seed: player_slot 0-4 = Radiant, 128-132 = Dire (OpenDota convention).
"""
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.repositories.analytics.matchup import MatchupRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.tests.seed_helpers import (
    seed_hero,
    seed_mp,
)


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


# ── seed helpers ──────────────────────────────────────────────────────────────

def _seed_5v5(conn, match_id: int, radiant_win: bool, radiant_heroes: list[int], dire_heroes: list[int]) -> None:
    """Seed матч з 5 Radiant (slot 0-4) і 5 Dire (slot 128-132) героями."""
    conn.execute(
        "INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win) VALUES (?, 1700000000, 2400, ?)",
        (match_id, int(radiant_win)),
    )
    for i, hero_id in enumerate(radiant_heroes):
        seed_mp(conn, match_id, slot=i, hero_id=hero_id, win=radiant_win)
    for i, hero_id in enumerate(dire_heroes):
        seed_mp(conn, match_id, slot=128 + i, hero_id=hero_id, win=not radiant_win)
    conn.commit()


# ══════════════════════════════════════════════════════════════════════════════
# rebuild_matchups (Epic 5.4)
# ══════════════════════════════════════════════════════════════════════════════

def test_rebuild_matchups_returns_zero_no_data(db) -> None:
    from services.ingestion.app.rebuild_matchups import rebuild_matchups
    assert rebuild_matchups() == 0


def test_rebuild_matchups_clears_stale_on_empty(db) -> None:
    """При порожньому source stale рядки видаляються."""
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Axe")
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1], dire_heroes=[2])

    rebuild_matchups()

    with UnitOfWork() as uow:
        count = uow.conn.execute("SELECT COUNT(*) FROM hero_matchup_computed").fetchone()[0]
    assert count > 0

    with UnitOfWork() as uow:
        uow.conn.execute("DELETE FROM match_players")
        uow.conn.execute("DELETE FROM matches")
        uow.conn.commit()

    rebuild_matchups()

    with UnitOfWork() as uow:
        count = uow.conn.execute("SELECT COUNT(*) FROM hero_matchup_computed").fetchone()[0]
    assert count == 0


def test_rebuild_matchups_both_directions(db) -> None:
    """Зберігаємо (A vs B) і (B vs A) — обидва напрямки."""
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Axe")
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1], dire_heroes=[2])

    rebuild_matchups()

    with UnitOfWork() as uow:
        row_ab = uow.conn.execute(
            "SELECT * FROM hero_matchup_computed WHERE hero_id=1 AND opponent_id=2"
        ).fetchone()
        row_ba = uow.conn.execute(
            "SELECT * FROM hero_matchup_computed WHERE hero_id=2 AND opponent_id=1"
        ).fetchone()

    assert row_ab is not None
    assert row_ba is not None


def test_rebuild_matchups_correct_winrate(db) -> None:
    """AM wins 2/3 проти Axe."""
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Axe")
        # AM (Radiant) wins 2 out of 3
        for i, radiant_win in enumerate([True, True, False], start=1):
            _seed_5v5(uow.conn, i, radiant_win=radiant_win, radiant_heroes=[1], dire_heroes=[2])

    rebuild_matchups()

    with UnitOfWork() as uow:
        row = uow.conn.execute(
            "SELECT matches, wins FROM hero_matchup_computed WHERE hero_id=1 AND opponent_id=2"
        ).fetchone()

    assert row["matches"] == 3
    assert row["wins"] == 2


def test_rebuild_matchups_idempotent(db) -> None:
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Axe")
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1], dire_heroes=[2])

    rebuild_matchups()
    rebuild_matchups()

    with UnitOfWork() as uow:
        count = uow.conn.execute(
            "SELECT COUNT(*) FROM hero_matchup_computed WHERE hero_id=1 AND opponent_id=2"
        ).fetchone()[0]
    assert count == 1


def test_rebuild_matchups_5v5_pair_count(db) -> None:
    """1 матч 5v5 = 5*5=25 пар у кожному напрямку = 50 рядків."""
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        for i in range(1, 11):
            seed_hero(uow.conn, i, f"hero_{i}")
        _seed_5v5(uow.conn, 1,
                  radiant_win=True,
                  radiant_heroes=[1, 2, 3, 4, 5],
                  dire_heroes=[6, 7, 8, 9, 10])

    count = rebuild_matchups()
    assert count == 50  # 5*5 пар * 2 напрямки


# ══════════════════════════════════════════════════════════════════════════════
# rebuild_synergies (Epic 5.5)
# ══════════════════════════════════════════════════════════════════════════════

def test_rebuild_synergies_returns_zero_no_data(db) -> None:
    from services.ingestion.app.rebuild_synergies import rebuild_synergies
    assert rebuild_synergies() == 0


def test_rebuild_synergies_clears_stale_on_empty(db) -> None:
    from services.ingestion.app.rebuild_synergies import rebuild_synergies

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Crystal-Maiden")
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1, 2], dire_heroes=[])

    rebuild_synergies()

    with UnitOfWork() as uow:
        uow.conn.execute("DELETE FROM match_players")
        uow.conn.execute("DELETE FROM matches")
        uow.conn.commit()

    rebuild_synergies()

    with UnitOfWork() as uow:
        count = uow.conn.execute("SELECT COUNT(*) FROM hero_synergy_computed").fetchone()[0]
    assert count == 0


def test_rebuild_synergies_hero_id_lt_ally_id(db) -> None:
    """Завжди hero_id < ally_id — дублів немає."""
    from services.ingestion.app.rebuild_synergies import rebuild_synergies

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 5, "Crystal-Maiden")
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1, 5], dire_heroes=[])

    rebuild_synergies()

    with UnitOfWork() as uow:
        rows = uow.conn.execute(
            "SELECT hero_id, ally_id FROM hero_synergy_computed WHERE hero_id IN (1,5)"
        ).fetchall()

    assert len(rows) == 1
    assert rows[0]["hero_id"] == 1
    assert rows[0]["ally_id"] == 5


def test_rebuild_synergies_correct_winrate(db) -> None:
    """AM + CM разом виграють 2/3."""
    from services.ingestion.app.rebuild_synergies import rebuild_synergies

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 5, "Crystal-Maiden")
        for i, radiant_win in enumerate([True, True, False], start=1):
            _seed_5v5(uow.conn, i, radiant_win=radiant_win, radiant_heroes=[1, 5], dire_heroes=[])

    rebuild_synergies()

    with UnitOfWork() as uow:
        row = uow.conn.execute(
            "SELECT matches, wins FROM hero_synergy_computed WHERE hero_id=1 AND ally_id=5"
        ).fetchone()

    assert row["matches"] == 3
    assert row["wins"] == 2


def test_rebuild_synergies_only_same_team(db) -> None:
    """Гравці різних команд не рахуються як synergy."""
    from services.ingestion.app.rebuild_synergies import rebuild_synergies

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")   # Radiant
        seed_hero(uow.conn, 2, "Axe")          # Dire
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1], dire_heroes=[2])

    count = rebuild_synergies()
    # Лише 1 гравець в кожній команді — пар немає
    assert count == 0


# ══════════════════════════════════════════════════════════════════════════════
# MatchupRepository (Epic 5.4)
# ══════════════════════════════════════════════════════════════════════════════

def test_matchup_repo_get_hero_matchups_empty(db) -> None:
    with UnitOfWork() as uow:
        rows = MatchupRepository(uow.conn).get_hero_matchups(1)
    assert rows == []


def test_matchup_repo_get_hero_matchups_after_rebuild(db) -> None:
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Axe")
        for i, win in enumerate([True, True, False], start=1):
            _seed_5v5(uow.conn, i, radiant_win=win, radiant_heroes=[1], dire_heroes=[2])

    rebuild_matchups()

    with UnitOfWork() as uow:
        rows = MatchupRepository(uow.conn).get_hero_matchups(1, min_matches=1)

    assert len(rows) == 1
    assert rows[0].hero_id == 1
    assert rows[0].opponent_id == 2
    assert rows[0].matches == 3
    assert rows[0].wins == 2
    assert rows[0].losses == 1
    assert rows[0].winrate == round(2 / 3, 4)


def test_matchup_repo_get_best_counters_sorted_asc(db) -> None:
    """get_best_counters — герої проти яких hero_id програє найчастіше (winrate ASC)."""
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Axe")          # AM wins 1/3 = 0.33
        seed_hero(uow.conn, 3, "Bane")         # AM wins 2/3 = 0.67
        # vs Axe: AM wins 1/3
        for i, win in enumerate([True, False, False], start=1):
            _seed_5v5(uow.conn, i, radiant_win=win, radiant_heroes=[1], dire_heroes=[2])
        # vs Bane: AM wins 2/3
        for i, win in enumerate([True, True, False], start=10):
            _seed_5v5(uow.conn, i, radiant_win=win, radiant_heroes=[1], dire_heroes=[3])

    rebuild_matchups()

    with UnitOfWork() as uow:
        counters = MatchupRepository(uow.conn).get_best_counters(1, min_matches=1)

    assert counters[0].opponent_id == 2   # Axe: AM winrate 0.33 (worst for AM = best counter)
    assert counters[1].opponent_id == 3   # Bane: AM winrate 0.67


def test_matchup_repo_min_matches_filter(db) -> None:
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Axe")
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1], dire_heroes=[2])

    rebuild_matchups()

    with UnitOfWork() as uow:
        rows = MatchupRepository(uow.conn).get_hero_matchups(1, min_matches=5)
    assert rows == []


def test_matchup_repo_invalid_args_raise(db) -> None:
    with UnitOfWork() as uow:
        repo = MatchupRepository(uow.conn)
        with pytest.raises(ValueError, match="hero_id must be int > 0"):
            repo.get_hero_matchups(0)
        with pytest.raises(ValueError, match="limit must be 1-100"):
            repo.get_hero_matchups(1, limit=0)
        with pytest.raises(ValueError, match="min_matches must be >= 0"):
            repo.get_hero_matchups(1, min_matches=-1)


# ── MatchupRepository synergies ───────────────────────────────────────────────

def test_synergy_repo_get_hero_synergies_after_rebuild(db) -> None:
    from services.ingestion.app.rebuild_synergies import rebuild_synergies

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 5, "Crystal-Maiden")
        for i, win in enumerate([True, True, False], start=1):
            _seed_5v5(uow.conn, i, radiant_win=win, radiant_heroes=[1, 5], dire_heroes=[])

    rebuild_synergies()

    with UnitOfWork() as uow:
        rows = MatchupRepository(uow.conn).get_hero_synergies(1, min_matches=1)

    assert len(rows) == 1
    assert rows[0].hero_id == 1
    assert rows[0].ally_id == 5
    assert rows[0].matches == 3
    assert rows[0].wins == 2
    assert rows[0].winrate == round(2 / 3, 4)


def test_synergy_repo_bidirectional_lookup(db) -> None:
    """get_hero_synergies працює і якщо hero_id > ally_id в таблиці."""
    from services.ingestion.app.rebuild_synergies import rebuild_synergies

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 5, "Crystal-Maiden")
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1, 5], dire_heroes=[])

    rebuild_synergies()

    # Запит від hero_id=5 (більший) — має знайти запис (1,5)
    with UnitOfWork() as uow:
        rows = MatchupRepository(uow.conn).get_hero_synergies(5, min_matches=1)

    assert len(rows) == 1
    assert rows[0].hero_id == 5
    assert rows[0].ally_id == 1


def test_synergy_repo_staleness(db) -> None:
    from services.ingestion.app.rebuild_matchups import rebuild_matchups

    with UnitOfWork() as uow:
        seed_hero(uow.conn, 1, "Anti-Mage")
        seed_hero(uow.conn, 2, "Axe")
        _seed_5v5(uow.conn, 1, radiant_win=True, radiant_heroes=[1], dire_heroes=[2])

    rebuild_matchups()

    with UnitOfWork() as uow:
        staleness = MatchupRepository(uow.conn).get_staleness()

    assert staleness["hero_matchup_computed"] is not None
    assert staleness["hero_matchup_computed"] > 0
    assert staleness["hero_synergy_computed"] is None  # не запускався