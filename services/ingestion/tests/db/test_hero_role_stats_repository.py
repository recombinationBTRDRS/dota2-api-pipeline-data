# services/ingestion/tests/db/test_hero_role_stats_repository.py
"""Unit тести HeroStatsRepository — role-filtered методи (Task 4.2).

Seed-дані вставляються напряму через SQL.
Seed helpers імпортуються зі спільного conftest або дублюються тут
(файл ізольований, не залежить від test_hero_stats_repository.py).
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


def _seed_role_score(conn, hero_id: int, primary_pos: int) -> None:
    """Вставляє мінімальний hero_role_scores запис з вказаним primary_pos."""
    conn.execute(
        """
        INSERT OR IGNORE INTO hero_role_scores
            (hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos)
        VALUES (?, 3, 3, 3, 3, 3, 5, ?)
        """,
        (hero_id, primary_pos),
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
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO match_players
            (match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win)
        VALUES (?, ?, ?, ?, ?, ?, ?, 600, ?)
        """,
        (match_id, slot, hero_id, kills, deaths, assists, gpm, int(win)),
    )


# ── get_hero_stats_by_role ────────────────────────────────────────────────────

def test_get_hero_stats_by_role_returns_none_for_unknown_hero(db) -> None:
    """Герой без hero_role_scores запису → None."""
    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_hero_stats_by_role(
            hero_id=9999, primary_pos=1
        )
    assert result is None


def test_get_hero_stats_by_role_returns_none_wrong_pos(db) -> None:
    """Герой є, але primary_pos в БД інший → None."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, hero_id=1, primary_pos=1)  # carry
        _seed_match(uow.conn, 1)
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True)

    with UnitOfWork() as uow:
        # запитуємо mid (2), але primary_pos=1 (carry)
        result = HeroStatsRepository(uow.conn).get_hero_stats_by_role(
            hero_id=1, primary_pos=2
        )
    assert result is None


def test_get_hero_stats_by_role_correct_winrate(db) -> None:
    """6 wins з 10 матчів на carry → winrate = 0.6."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, hero_id=1, primary_pos=1)  # carry
        for i in range(10):
            _seed_match(uow.conn, i + 1)
            _seed_match_player(uow.conn, i + 1, 0, hero_id=1, win=(i < 6))

    with UnitOfWork() as uow:
        stats = HeroStatsRepository(uow.conn).get_hero_stats_by_role(
            hero_id=1, primary_pos=1
        )

    assert stats is not None
    assert stats.hero_id == 1
    assert stats.primary_pos == 1
    assert stats.matches_played == 10
    assert stats.wins == 6
    assert stats.losses == 4
    assert stats.winrate == 0.6
    assert stats.hero_name == "Anti-Mage"


def test_get_hero_stats_by_role_avg_gpm(db) -> None:
    """avg_gpm обчислюється коректно для role-filtered запиту."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 2, "Axe")
        _seed_role_score(uow.conn, hero_id=2, primary_pos=3)  # offlane
        _seed_match(uow.conn, 1)
        _seed_match(uow.conn, 2)
        _seed_match_player(uow.conn, 1, 0, hero_id=2, win=True, gpm=350)
        _seed_match_player(uow.conn, 2, 0, hero_id=2, win=False, gpm=450)

    with UnitOfWork() as uow:
        stats = HeroStatsRepository(uow.conn).get_hero_stats_by_role(
            hero_id=2, primary_pos=3
        )

    assert stats is not None
    assert stats.avg_gpm == 400.0


def test_get_hero_stats_by_role_invalid_pos_raises(db) -> None:
    """primary_pos поза 1–5 → ValueError."""
    with UnitOfWork() as uow:
        with pytest.raises(ValueError, match="primary_pos must be 1-5"):
            HeroStatsRepository(uow.conn).get_hero_stats_by_role(
                hero_id=1, primary_pos=0
            )

    with UnitOfWork() as uow:
        with pytest.raises(ValueError, match="primary_pos must be 1-5"):
            HeroStatsRepository(uow.conn).get_hero_stats_by_role(
                hero_id=1, primary_pos=6
            )


# ── get_role_leaderboard ──────────────────────────────────────────────────────

def test_get_role_leaderboard_returns_empty_for_no_data(db) -> None:
    """Порожня DB → порожній список."""
    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_role_leaderboard(
            primary_pos=1, min_matches=1
        )
    assert result == []


def test_get_role_leaderboard_sorted_by_winrate_desc(db) -> None:
    """Leaderboard відсортований за winrate DESC."""
    with UnitOfWork() as uow:
        # Anti-Mage carry: 6/10 = 0.6
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, hero_id=1, primary_pos=1)
        for i in range(10):
            _seed_match(uow.conn, i + 1)
            _seed_match_player(uow.conn, i + 1, 0, hero_id=1, win=(i < 6))

        # Drow Ranger carry: 8/10 = 0.8
        _seed_hero(uow.conn, 6, "Drow-Ranger")
        _seed_role_score(uow.conn, hero_id=6, primary_pos=1)
        for i in range(10):
            _seed_match(uow.conn, i + 100)
            _seed_match_player(uow.conn, i + 100, 1, hero_id=6, win=(i < 8))

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_role_leaderboard(
            primary_pos=1, min_matches=1
        )

    assert len(result) == 2
    assert result[0].hero_id == 6    # Drow: 0.8
    assert result[1].hero_id == 1    # AM: 0.6
    assert result[0].winrate > result[1].winrate
    assert result[0].primary_pos == 1
    assert result[1].primary_pos == 1


def test_get_role_leaderboard_excludes_other_roles(db) -> None:
    """Герої з іншим primary_pos не потрапляють в leaderboard."""
    with UnitOfWork() as uow:
        # Anti-Mage carry (pos=1)
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, hero_id=1, primary_pos=1)
        for i in range(5):
            _seed_match(uow.conn, i + 1)
            _seed_match_player(uow.conn, i + 1, 0, hero_id=1, win=True)

        # Axe offlane (pos=3)
        _seed_hero(uow.conn, 2, "Axe")
        _seed_role_score(uow.conn, hero_id=2, primary_pos=3)
        for i in range(5):
            _seed_match(uow.conn, i + 100)
            _seed_match_player(uow.conn, i + 100, 1, hero_id=2, win=True)

    with UnitOfWork() as uow:
        carry_board = HeroStatsRepository(uow.conn).get_role_leaderboard(
            primary_pos=1, min_matches=1
        )
        offlane_board = HeroStatsRepository(uow.conn).get_role_leaderboard(
            primary_pos=3, min_matches=1
        )

    assert len(carry_board) == 1
    assert carry_board[0].hero_id == 1

    assert len(offlane_board) == 1
    assert offlane_board[0].hero_id == 2


def test_get_role_leaderboard_min_matches_filter(db) -> None:
    """min_matches виключає героїв з малою вибіркою."""
    with UnitOfWork() as uow:
        # Anti-Mage: 3 матчі
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_role_score(uow.conn, hero_id=1, primary_pos=1)
        for i in range(3):
            _seed_match(uow.conn, i + 1)
            _seed_match_player(uow.conn, i + 1, 0, hero_id=1, win=True)

        # Drow Ranger: 10 матчів
        _seed_hero(uow.conn, 6, "Drow-Ranger")
        _seed_role_score(uow.conn, hero_id=6, primary_pos=1)
        for i in range(10):
            _seed_match(uow.conn, i + 100)
            _seed_match_player(uow.conn, i + 100, 1, hero_id=6, win=(i < 5))

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_role_leaderboard(
            primary_pos=1, min_matches=5
        )

    assert len(result) == 1
    assert result[0].hero_id == 6  # тільки Drow (10 >= 5)


def test_get_role_leaderboard_limit(db) -> None:
    """limit обрізає результат."""
    with UnitOfWork() as uow:
        for hero_id in range(1, 6):  # 5 carry героїв
            _seed_hero(uow.conn, hero_id, f"carry_hero_{hero_id}")
            _seed_role_score(uow.conn, hero_id=hero_id, primary_pos=1)
            for match_id in range(hero_id * 10, hero_id * 10 + 5):
                _seed_match(uow.conn, match_id)
                _seed_match_player(uow.conn, match_id, 0, hero_id=hero_id, win=True)

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_role_leaderboard(
            primary_pos=1, min_matches=1, limit=3
        )

    assert len(result) == 3


def test_get_role_leaderboard_heroes_without_role_scores_excluded(db) -> None:
    """Герої без hero_role_scores запису не з'являються в leaderboard."""
    with UnitOfWork() as uow:
        # Anti-Mage: є матчі, але НЕМАЄ hero_role_scores
        _seed_hero(uow.conn, 1, "Anti-Mage")
        for i in range(5):
            _seed_match(uow.conn, i + 1)
            _seed_match_player(uow.conn, i + 1, 0, hero_id=1, win=True)

        # Drow Ranger: є матчі і є hero_role_scores
        _seed_hero(uow.conn, 6, "Drow-Ranger")
        _seed_role_score(uow.conn, hero_id=6, primary_pos=1)
        for i in range(5):
            _seed_match(uow.conn, i + 100)
            _seed_match_player(uow.conn, i + 100, 1, hero_id=6, win=True)

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_role_leaderboard(
            primary_pos=1, min_matches=1
        )

    assert len(result) == 1
    assert result[0].hero_id == 6  # тільки Drow (є role_scores)


def test_get_role_leaderboard_invalid_pos_raises(db) -> None:
    """primary_pos поза 1–5 → ValueError."""
    with UnitOfWork() as uow:
        with pytest.raises(ValueError, match="primary_pos must be 1-5"):
            HeroStatsRepository(uow.conn).get_role_leaderboard(primary_pos=6)