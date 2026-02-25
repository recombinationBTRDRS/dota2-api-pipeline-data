# services/ingestion/tests/app/test_persist_match.py

import pytest

from services.ingestion.app.persist import persist_match
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import get_connection, init_db
from services.ingestion.domains.matches.dtos import Match, PlayerMatchStats


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def make_match() -> Match:
    return Match(
        id=1,
        duration=222,
        radiant_win=True,
        start_time=111,
        radiant_score=30,
        dire_score=20,
        players=[
            PlayerMatchStats(
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
                account_id=456,
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


def test_persist_match_saves_correctly(db):
    persist_match(make_match())

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0] == 2


def test_persist_match_idempotent(db):
    match = make_match()
    persist_match(match)
    persist_match(match)  # повторний виклик не дублює

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0] == 2