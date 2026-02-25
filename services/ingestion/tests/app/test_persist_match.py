# services/ingestion/tests/app/test_persist_match.py
import tempfile
from pathlib import Path

from services.ingestion.app.persist import persist_match
from services.ingestion.domains.matches.dtos import Match, PlayerMatchStats
from services.ingestion.db.sqlite import init_db, get_connection


def test_persist_match(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.sqlite"

        from services.ingestion.db import sqlite as sqlite_module

        monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)

        init_db()

        match = Match(
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

        persist_match(match)
        persist_match(match)  # ідемпотентно

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM matches")
        assert cur.fetchone()["c"] == 1

        cur.execute("SELECT COUNT(*) as c FROM players")
        assert cur.fetchone()["c"] == 2

        cur.execute("SELECT COUNT(*) as c FROM match_players")
        assert cur.fetchone()["c"] == 2

        conn.close()