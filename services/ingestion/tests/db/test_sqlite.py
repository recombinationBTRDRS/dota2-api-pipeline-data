# services/ingestion/tests/db/test_sqlite.py
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import init_db, get_connection


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    return db_path


def test_init_db_creates_tables(db):
    init_db()

    with get_connection() as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert "matches" in tables
    assert "players" in tables
    assert "match_players" in tables


def test_init_db_idempotent(db):
    """Подвійний виклик init_db не ламає схему."""
    init_db()
    init_db()

    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]

    assert count >= 3