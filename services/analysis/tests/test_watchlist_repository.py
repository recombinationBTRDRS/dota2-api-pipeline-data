# services/analysis/tests/test_watchlist_repository.py
import pytest
from services.analysis.db.sqlite import init_db
from services.analysis.db.repositories.watchlist import WatchlistRepository
import sqlite3


@pytest.fixture()
def conn(tmp_path):
    db = str(tmp_path / "test.sqlite")
    init_db(db)
    c = sqlite3.connect(db)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def test_add_and_get(conn):
    repo = WatchlistRepository(conn)
    row = repo.add(12345, label="my match")
    assert row.match_id == 12345
    assert row.status == "pending"
    assert row.label == "my match"

    fetched = repo.get(12345)
    assert fetched is not None
    assert fetched.id == row.id


def test_add_duplicate_returns_existing(conn):
    repo = WatchlistRepository(conn)
    r1 = repo.add(99999)
    r2 = repo.add(99999)
    assert r1.id == r2.id


def test_get_all(conn):
    repo = WatchlistRepository(conn)
    repo.add(1)
    repo.add(2)
    repo.add(3)
    all_rows = repo.get_all()
    assert len(all_rows) == 3


def test_delete(conn):
    repo = WatchlistRepository(conn)
    repo.add(777)
    deleted = repo.delete(777)
    assert deleted is True
    assert repo.get(777) is None


def test_delete_nonexistent(conn):
    repo = WatchlistRepository(conn)
    assert repo.delete(999999) is False


def test_update_status(conn):
    repo = WatchlistRepository(conn)
    repo.add(555)
    repo.update_status(555, "analyzed")
    conn.commit()
    row = repo.get(555)
    assert row.status == "analyzed"
    assert row.error is None


def test_update_status_error(conn):
    repo = WatchlistRepository(conn)
    repo.add(556)
    repo.update_status(556, "error", error="timeout")
    conn.commit()
    row = repo.get(556)
    assert row.status == "error"
    assert row.error == "timeout"
