# services/ingestion/tests/db/test_ingestion_log.py
"""Інтеграційні тести IngestionLogRepository з реальним SQLite (tmp_path)."""
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.repositories import IngestionLogRepository
from services.ingestion.db.sqlite import get_connection, init_db
from services.ingestion.db.unit_of_work import UnitOfWork


@pytest.fixture()
def db(monkeypatch, tmp_path):
    """Тимчасова SQLite БД на час одного тесту."""
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


# ── is_known ────────────────────────────────────────────────────────────────


def test_is_known_returns_false_for_unknown_match(db) -> None:
    """Матч якого немає в журналі — is_known повертає False."""
    with UnitOfWork() as uow:
        repo = IngestionLogRepository(uow.conn)
        assert repo.is_known(match_id=999) is False


def test_is_known_returns_true_after_mark_ok(db) -> None:
    """Після mark_ok — is_known повертає True."""
    with UnitOfWork() as uow:
        repo = IngestionLogRepository(uow.conn)
        repo.mark_ok(match_id=1, ingested_at=1000)

    with UnitOfWork() as uow:
        assert IngestionLogRepository(uow.conn).is_known(match_id=1) is True


def test_is_known_returns_false_for_failed_match(db) -> None:
    """Failed матч — is_known повертає False (має бути оброблений повторно)."""
    with UnitOfWork() as uow:
        repo = IngestionLogRepository(uow.conn)
        repo.mark_failed(match_id=2, ingested_at=1000, error="timeout")

    with UnitOfWork() as uow:
        assert IngestionLogRepository(uow.conn).is_known(match_id=2) is False


# ── mark_ok ─────────────────────────────────────────────────────────────────


def test_mark_ok_saves_record(db) -> None:
    """mark_ok зберігає запис зі статусом 'ok' і без error."""
    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_ok(match_id=10, ingested_at=5000)

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=10)

    assert entry is not None
    assert entry.status == "ok"
    assert entry.ingested_at == 5000
    assert entry.error is None


def test_mark_ok_overwrites_failed(db) -> None:
    """mark_ok після mark_failed — статус змінюється на 'ok', error очищується."""
    with UnitOfWork() as uow:
        repo = IngestionLogRepository(uow.conn)
        repo.mark_failed(match_id=20, ingested_at=1000, error="network error")

    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_ok(match_id=20, ingested_at=2000)

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=20)

    assert entry is not None
    assert entry.status == "ok"
    assert entry.error is None


def test_mark_ok_idempotent(db) -> None:
    """Подвійний mark_ok — не дублює запис."""
    with UnitOfWork() as uow:
        repo = IngestionLogRepository(uow.conn)
        repo.mark_ok(match_id=30, ingested_at=1000)
        repo.mark_ok(match_id=30, ingested_at=2000)

    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM ingestion_log WHERE match_id = 30"
        ).fetchone()[0]
    assert count == 1


# ── mark_failed ──────────────────────────────────────────────────────────────


def test_mark_failed_saves_record(db) -> None:
    """mark_failed зберігає запис зі статусом 'failed' та текстом помилки."""
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
    """Довгий текст помилки truncate до 500 символів."""
    long_error = "x" * 1000

    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_failed(
            match_id=50, ingested_at=4000, error=long_error
        )

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=50)

    assert entry is not None
    assert len(entry.error or "") == 500


def test_mark_failed_overwrites_previous_failure(db) -> None:
    """Повторний mark_failed оновлює error і timestamp."""
    with UnitOfWork() as uow:
        repo = IngestionLogRepository(uow.conn)
        repo.mark_failed(match_id=60, ingested_at=1000, error="first error")

    with UnitOfWork() as uow:
        IngestionLogRepository(uow.conn).mark_failed(
            match_id=60, ingested_at=2000, error="second error"
        )

    with UnitOfWork() as uow:
        entry = IngestionLogRepository(uow.conn).get(match_id=60)

    assert entry is not None
    assert entry.error == "second error"
    assert entry.ingested_at == 2000


# ── get ──────────────────────────────────────────────────────────────────────


def test_get_returns_none_for_unknown(db) -> None:
    """get() для невідомого match_id повертає None."""
    with UnitOfWork() as uow:
        result = IngestionLogRepository(uow.conn).get(match_id=9999)
    assert result is None