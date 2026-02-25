# services/ingestion/tests/integration/test_smoke.py
import tempfile
from pathlib import Path

from services.ingestion.app.ingest_match import ingest_match
from services.ingestion.db.sqlite import init_db, get_connection
from services.ingestion.providers.opendota.client import MatchProvider


class FakeProvider(MatchProvider):
    def get_match(self, match_id: int) -> dict:
        return {
            "match_id": match_id,
            "duration": 100,
            "radiant_win": True,
            "start_time": 123,
            "radiant_score": 10,
            "dire_score": 5,
            "players": [
                {
                    "account_id": 1,
                    "hero_id": 1,
                    "kills": 5,
                    "deaths": 1,
                    "assists": 2,
                    "gpm": 400,
                    "xpm": 500,
                    "isRadiant": True,
                    "win": True,
                }
            ],
        }


def test_full_ingest_pipeline(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "smoke.sqlite"

        from services.ingestion.db import sqlite as sqlite_module
        monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)

        init_db()

        match = ingest_match(42, provider=FakeProvider())

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as c FROM matches")
        assert cur.fetchone()["c"] == 1

        cur.execute("SELECT COUNT(*) as c FROM players")
        assert cur.fetchone()["c"] == 1

        cur.execute("SELECT COUNT(*) as c FROM match_players")
        assert cur.fetchone()["c"] == 1

        assert match.id == 42
        conn.close()