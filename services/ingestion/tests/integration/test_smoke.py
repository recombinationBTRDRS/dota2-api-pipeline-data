# services/ingestion/tests/integration/test_smoke.py
from typing import Any

import pytest

from services.ingestion.app.ingest_match import ingest_match
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import get_connection, init_db
from services.ingestion.providers.opendota.client import MatchProvider


class FakeProvider(MatchProvider):
    def get_match(self, match_id: int) -> dict[str, Any]:
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


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "smoke.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def test_full_ingest_pipeline(db):
    """
    Інтеграційний тест повного пайплайну:
    FakeProvider → adapt → parse → persist → assert в БД
    """
    match = ingest_match(42, provider=FakeProvider())

    assert match.id == 42

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0] == 1


def test_full_ingest_idempotent(db):
    """Повторний інжест того самого матчу не дублює дані."""
    ingest_match(42, provider=FakeProvider())
    ingest_match(42, provider=FakeProvider())

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0] == 1