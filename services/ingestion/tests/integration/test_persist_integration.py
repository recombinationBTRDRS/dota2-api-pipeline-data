# services/ingestion/tests/integration/test_persist_integration.py
"""Інтеграційні тести persist_match з реальним SQLite."""
import pytest

from services.ingestion.app.persist import persist_match
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import get_connection, init_db
from services.ingestion.domains.matches.dtos import Match, PlayerMatchStats


@pytest.fixture()
def db(monkeypatch, tmp_path):
    """Ініціалізує тимчасову SQLite БД і підміняє DB_PATH."""
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def make_match(match_id: int = 1) -> Match:
    """Фабрика тестового Match DTO."""
    return Match(
        match_id=match_id,
        duration=222,
        radiant_win=True,
        start_time=111,
        radiant_score=30,
        dire_score=20,
        players=[
            PlayerMatchStats(
                player_slot=0,
                account_id=123,
                hero_id=1,
                kills=10,
                deaths=2,
                assists=5,
                gpm=600,
                xpm=700,
                is_radiant=True,
                win=True,
            ),
            PlayerMatchStats(
                player_slot=1,
                account_id=None,
                hero_id=2,
                kills=1,
                deaths=10,
                assists=2,
                gpm=300,
                xpm=400,
                is_radiant=False,
                win=False,
            ),
        ],
    )


def test_persist_match_saves_correctly(db) -> None:
    """persist_match зберігає match + players + match_players."""
    persist_match(make_match())

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0] == 2


def test_persist_match_idempotent(db) -> None:
    """Повторний виклик persist_match не дублює записи."""
    match = make_match()
    persist_match(match)
    persist_match(match)

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0] == 2


def test_persist_anonymous_player_no_duplicate_match_players(db) -> None:
    """Анонімний гравець по player_slot не дублює match_players при реінжесті."""
    match = make_match()
    persist_match(match)
    persist_match(match)

    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0]
        assert count == 2