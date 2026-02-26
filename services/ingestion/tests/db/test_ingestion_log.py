# services/ingestion/tests/db/test_ingestion_log.py
"""Інтеграційні тести IngestionLogRepository з реальним SQLite (tmp_path)."""
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.repositories import IngestionLogRepository
from services.ingestion.db.sqlite import get_connection, init_db
from services.ingestion.db.unit_of_work import UnitOfWork


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def test_is_known_returns_false_for_unknown_match(db) -> None:
    with UnitOfWork() as uow:
        assert IngestionLogRepository(uow.conn).is_known(match_id=999) is False


def test_is_known_returns_true_after_mark_ok(db) -> None:
    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_ok(match_id=1, ingested_at=1000)

    with UnitOfWork() as uow:
        assert IngestionLogRepository(uow.conn).is_known(match_id=1) is True


def test_is_known_returns_false_for_failed_match(db) -> None:
    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_failed(match_id=2, ingested_at=1000, error="timeout")

    with UnitOfWork() as uow:
        assert IngestionLogRepository(uow.conn).is_known(match_id=2) is False


def test_mark_ok_saves_record(db) -> None:
    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_ok(match_id=10, ingested_at=5000)

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=10)

    assert entry is not None
    assert entry.status == "ok"
    assert entry.ingested_at == 5000
    assert entry.error is None


def test_mark_ok_overwrites_failed(db) -> None:
    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_failed(match_id=20, ingested_at=1000, error="err")

    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_ok(match_id=20, ingested_at=2000)

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=20)

    assert entry is not None
    assert entry.status == "ok"
    assert entry.error is None


def test_mark_ok_idempotent(db) -> None:
    with UnitOfWork() as uow:
        repo = IngestionLogRepository(uow.conn)
        repo.mark_ok(match_id=30, ingested_at=1000)
        repo.mark_ok(match_id=30, ingested_at=2000)

    # get_connection() з явним close() через finally
    conn = get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM ingestion_log WHERE match_id = 30"
        ).fetchone()[0]
    finally:
        conn.close()

    assert count == 1


def test_mark_failed_saves_record(db) -> None:
    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_failed(
            match_id=40, ingested_at=3000, error="connection refused"
        )

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=40)

    assert entry is not None
    assert entry.status == "failed"
    assert entry.error == "connection refused"


def test_mark_failed_truncates_long_error(db) -> None:
    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_failed(
            match_id=50, ingested_at=4000, error="x" * 1000
        )

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=50)

    assert entry is not None
    assert len(entry.error or "") == 500


def test_mark_failed_overwrites_previous_failure(db) -> None:
    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_failed(match_id=60, ingested_at=1000, error="first")

    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_failed(match_id=60, ingested_at=2000, error="second")

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=60)

    assert entry is not None
    assert entry.error == "second"
    assert entry.ingested_at == 2000


def test_get_returns_none_for_unknown(db) -> None:
    with UnitOfWork() as uow:
        assert IngestionLogRepository(uow.conn).get(match_id=9999) is None