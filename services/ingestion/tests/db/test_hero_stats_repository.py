# services/ingestion/tests/db/test_hero_stats_repository.py
"""Unit тести HeroStatsRepository з реальним tmp SQLite (Task 4.1).

Seed-дані вставляються напряму через SQL щоб не залежати від інших сервісів.
"""
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.repositories import HeroStatsRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork

# ── fixture + seed helpers ────────────────────────────────────────────────────

@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def _seed_hero(conn, hero_id: int, name: str) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO heroes (id, name, localized_name, primary_attr, attack_type)
        VALUES (?, ?, ?, 'agi', 'Melee')
        """,
        (hero_id, f"npc_dota_hero_{name}", name),
    )


def _seed_match(conn, match_id: int, duration: int = 2400) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win)
        VALUES (?, 1700000000, ?, 1)
        """,
        (match_id, duration),
    )


def _seed_match_player(
    conn,
    match_id: int,
    slot: int,
    hero_id: int,
    win: bool,
    kills: int = 5,
    deaths: int = 2,
    assists: int = 8,
    gpm: int = 500,
    xpm: int = 600,
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO match_players
            (match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (match_id, slot, hero_id, kills, deaths, assists, gpm, xpm, int(win)),
    )


# ── get_hero_stats ────────────────────────────────────────────────────────────

def test_get_hero_stats_returns_none_for_unknown(db) -> None:
    """Герой без матчів → None."""
    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_hero_stats(hero_id=9999)
    assert result is None


def test_get_hero_stats_correct_winrate(db) -> None:
    """6 wins з 10 матчів → winrate = 0.6."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        for i in range(10):
            _seed_match(uow.conn, match_id=i + 1)
            _seed_match_player(uow.conn, match_id=i + 1, slot=0, hero_id=1, win=(i < 6))

    with UnitOfWork() as uow:
        stats = HeroStatsRepository(uow.conn).get_hero_stats(hero_id=1)

    assert stats is not None
    assert stats.hero_id == 1
    assert stats.matches_played == 10
    assert stats.wins == 6
    assert stats.losses == 4
    assert stats.winrate == 0.6
    assert stats.hero_name == "Anti-Mage"


def test_get_hero_stats_zero_division_safe(db) -> None:
    """get_hero_stats з 0 матчів → None (не ZeroDivisionError)."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 2, "Axe")
        # hero існує але матчів немає
        result = HeroStatsRepository(uow.conn).get_hero_stats(hero_id=2)
    assert result is None


def test_get_hero_stats_avg_gpm(db) -> None:
    """avg_gpm обчислюється коректно."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match(uow.conn, 1)
        _seed_match(uow.conn, 2)
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True, gpm=400)
        _seed_match_player(uow.conn, 2, 0, hero_id=1, win=False, gpm=600)

    with UnitOfWork() as uow:
        stats = HeroStatsRepository(uow.conn).get_hero_stats(hero_id=1)

    assert stats is not None
    assert stats.avg_gpm == 500.0


def test_get_hero_stats_hero_name_none_when_no_hero_row(db) -> None:
    """hero_name = None якщо герой є в match_players але відсутній в heroes таблиці."""
    with UnitOfWork() as uow:
        # вставляємо match_player без відповідного heroes запису
        # (FK не enforced для hero_id в match_players — лише для match_id і player_id)
        _seed_match(uow.conn, 1)
        uow.conn.execute(
            "INSERT INTO match_players (match_id, player_slot, hero_id, kills, deaths, "
            "assists, gpm, xpm, win) VALUES (1, 0, 999, 5, 2, 8, 500, 600, 1)"
        )

    with UnitOfWork() as uow:
        stats = HeroStatsRepository(uow.conn).get_hero_stats(hero_id=999)

    assert stats is not None
    assert stats.hero_name is None  # LEFT JOIN → NULL


# ── get_all_heroes_stats ──────────────────────────────────────────────────────

def test_get_all_heroes_stats_min_matches_filter(db) -> None:
    """min_matches фільтрує героїв з малою вибіркою."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_hero(uow.conn, 2, "Axe")

        # Anti-Mage: 5 матчів
        for i in range(5):
            _seed_match(uow.conn, i + 1)
            _seed_match_player(uow.conn, i + 1, 0, hero_id=1, win=True)

        # Axe: 2 матчі
        for i in range(2):
            _seed_match(uow.conn, i + 100)
            _seed_match_player(uow.conn, i + 100, 1, hero_id=2, win=False)

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_all_heroes_stats(min_matches=3)

    assert len(result) == 1
    assert result[0].hero_id == 1  # тільки Anti-Mage (5 >= 3)


def test_get_all_heroes_stats_returns_empty_for_no_matches(db) -> None:
    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_all_heroes_stats(min_matches=1)
    assert result == []


# ── get_top_by_winrate ────────────────────────────────────────────────────────

def test_get_top_by_winrate_sorted_desc(db) -> None:
    """Результат відсортований за winrate DESC."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_hero(uow.conn, 2, "Axe")

        # Anti-Mage: 6/10 = 0.6
        for i in range(10):
            _seed_match(uow.conn, i + 1)
            _seed_match_player(uow.conn, i + 1, 0, hero_id=1, win=(i < 6))

        # Axe: 8/10 = 0.8
        for i in range(10):
            _seed_match(uow.conn, i + 100)
            _seed_match_player(uow.conn, i + 100, 1, hero_id=2, win=(i < 8))

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_top_by_winrate(limit=10, min_matches=1)

    assert len(result) == 2
    assert result[0].hero_id == 2   # Axe: 0.8
    assert result[1].hero_id == 1   # Anti-Mage: 0.6
    assert result[0].winrate > result[1].winrate


def test_get_top_by_winrate_limit(db) -> None:
    """limit обрізає результат."""
    with UnitOfWork() as uow:
        for hero_id in range(1, 6):  # 5 героїв
            _seed_hero(uow.conn, hero_id, f"hero_{hero_id}")
            for match_id in range(hero_id * 10, hero_id * 10 + 5):
                _seed_match(uow.conn, match_id)
                _seed_match_player(uow.conn, match_id, 0, hero_id=hero_id, win=True)

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_top_by_winrate(limit=3, min_matches=1)

    assert len(result) == 3


def test_get_top_by_winrate_min_matches_excludes(db) -> None:
    """Герой з 1 матчем не потрапляє в топ при min_matches=5."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match(uow.conn, 1)
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True)

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_top_by_winrate(limit=10, min_matches=5)

    assert result == []


def test_get_top_by_winrate_winrate_calculation(db) -> None:
    """winrate = wins / matches, округлено до 4 знаків."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        for i in range(3):
            _seed_match(uow.conn, i + 1)
            _seed_match_player(uow.conn, i + 1, 0, hero_id=1, win=(i < 1))  # 1/3

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_top_by_winrate(limit=1, min_matches=1)

    assert len(result) == 1
    assert result[0].winrate == round(1 / 3, 4)