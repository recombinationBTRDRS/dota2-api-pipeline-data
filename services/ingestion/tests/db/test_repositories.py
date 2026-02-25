# services/ingestion/tests/db/test_repositories.py
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import init_db, get_connection
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.db.repositories import (
    MatchRepository,
    PlayerRepository,
    MatchPlayerRepository,
)
from services.ingestion.db.models import MatchDB, PlayerDB, MatchPlayerDB


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def test_match_upsert_idempotent(db):
    match = MatchDB(
        id=1,
        start_time=111,
        duration=222,
        radiant_win=True,
        patch=7,
        region=2,
    )

    with UnitOfWork() as uow:
        repo = MatchRepository(uow.conn)
        repo.upsert(match)
        repo.upsert(match)

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1


def test_player_upsert_returns_same_id(db):
    player = PlayerDB(id=None, account_id=123, rank_tier=5, mmr=4500.0)

    with UnitOfWork() as uow:
        repo = PlayerRepository(uow.conn)
        id_first = repo.upsert(player)
        id_second = repo.upsert(player)

    assert id_first == id_second


def test_match_player_upsert_idempotent(db):
    match = MatchDB(
        id=1, start_time=0, duration=100,
        radiant_win=True, patch=None, region=None
    )
    player = PlayerDB(id=None, account_id=42, rank_tier=None, mmr=None)

    with UnitOfWork() as uow:
        MatchRepository(uow.conn).upsert(match)
        player_id = PlayerRepository(uow.conn).upsert(player)

        mp = MatchPlayerDB(
            match_id=1, player_id=player_id, hero_id=46,
            kills=10, deaths=2, assists=5,
            gpm=600, xpm=700, win=True,
        )
        repo = MatchPlayerRepository(uow.conn)
        repo.upsert(mp)
        repo.upsert(mp)

    with get_connection() as conn:
        # перевіряємо всі три таблиці — повна ідемпотентність
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0] == 1


def test_rollback_on_error(db):
    match = MatchDB(
        id=99, start_time=0, duration=100,
        radiant_win=True, patch=None, region=None
    )

    with pytest.raises(RuntimeError):
        with UnitOfWork() as uow:
            MatchRepository(uow.conn).upsert(match)
            raise RuntimeError("щось пішло не так")

    with get_connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM matches WHERE id = 99"
        ).fetchone()[0] == 0