# services/ingestion/tests/db/test_repositories.py
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.models import MatchDB, MatchPlayerDB, PlayerDB
from services.ingestion.db.repositories import (
    MatchPlayerRepository,
    MatchRepository,
    PlayerRepository,
)
from services.ingestion.db.sqlite import get_connection, init_db
from services.ingestion.db.unit_of_work import UnitOfWork


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def _make_mp(
    *,
    match_id: int,
    player_id: int | None,
    hero_id: int,
    kills: int,
    deaths: int,
    assists: int,
    gpm: int,
    xpm: int,
    win: bool,
    player_slot: int,
    lane_role: int | None,
    is_roaming: bool,
    net_worth: int | None = None,
    hero_damage: int | None = None,
    tower_damage: int | None = None,
    hero_healing: int | None = None,
    last_hits: int | None = None,
) -> MatchPlayerDB:
    return MatchPlayerDB(
        match_id=match_id,
        player_id=player_id,
        hero_id=hero_id,
        kills=kills,
        deaths=deaths,
        assists=assists,
        gpm=gpm,
        xpm=xpm,
        win=win,
        player_slot=player_slot,
        lane_role=lane_role,
        is_roaming=is_roaming,
        net_worth=net_worth,
        hero_damage=hero_damage,
        tower_damage=tower_damage,
        hero_healing=hero_healing,
        last_hits=last_hits,
    )


def test_match_upsert_idempotent(db):
    match = MatchDB(id=1, start_time=111, duration=222, radiant_win=True, patch=7, region=2)

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
    match = MatchDB(id=1, start_time=0, duration=100, radiant_win=True, patch=None, region=None)
    player = PlayerDB(id=None, account_id=42, rank_tier=None, mmr=None)

    with UnitOfWork() as uow:
        MatchRepository(uow.conn).upsert(match)
        player_id = PlayerRepository(uow.conn).upsert(player)

        mp = _make_mp(
            match_id=1, player_id=player_id, hero_id=46,
            kills=10, deaths=2, assists=5,
            gpm=600, xpm=700, win=True,
            player_slot=0, lane_role=1, is_roaming=False,
        )
        repo = MatchPlayerRepository(uow.conn)
        repo.upsert(mp)
        repo.upsert(mp)

    with get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM players").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM match_players").fetchone()[0] == 1


def test_match_player_lane_role_stored(db):
    """lane_role і is_roaming зберігаються і читаються коректно."""
    match = MatchDB(id=2, start_time=0, duration=2000, radiant_win=False, patch=38, region=1)
    player = PlayerDB(id=None, account_id=99, rank_tier=None, mmr=None)

    with UnitOfWork() as uow:
        MatchRepository(uow.conn).upsert(match)
        player_id = PlayerRepository(uow.conn).upsert(player)
        MatchPlayerRepository(uow.conn).upsert(_make_mp(
            match_id=2, player_id=player_id, hero_id=10,
            kills=3, deaths=1, assists=4,
            gpm=450, xpm=500, win=False,
            player_slot=1, lane_role=4, is_roaming=True,
        ))

    with get_connection() as conn:
        row = conn.execute(
            "SELECT lane_role, is_roaming FROM match_players WHERE player_slot = 1"
        ).fetchone()
        assert row["lane_role"] == 4
        assert bool(row["is_roaming"]) is True


def test_match_player_lane_role_nullable(db):
    """lane_role може бути NULL (старі матчі або API не повернув)."""
    match = MatchDB(id=3, start_time=0, duration=1500, radiant_win=True, patch=None, region=None)
    player = PlayerDB(id=None, account_id=77, rank_tier=None, mmr=None)

    with UnitOfWork() as uow:
        MatchRepository(uow.conn).upsert(match)
        player_id = PlayerRepository(uow.conn).upsert(player)
        MatchPlayerRepository(uow.conn).upsert(_make_mp(
            match_id=3, player_id=player_id, hero_id=5,
            kills=0, deaths=5, assists=2,
            gpm=300, xpm=350, win=True,
            player_slot=2, lane_role=None, is_roaming=False,
        ))

    with get_connection() as conn:
        row = conn.execute(
            "SELECT lane_role FROM match_players WHERE player_slot = 2"
        ).fetchone()
        assert row["lane_role"] is None


def test_match_player_performance_fields_stored(db):
    """net_worth, hero_damage і інші performance поля зберігаються коректно."""
    match = MatchDB(id=4, start_time=0, duration=2500, radiant_win=True, patch=59, region=3)
    player = PlayerDB(id=None, account_id=55, rank_tier=None, mmr=None)

    with UnitOfWork() as uow:
        MatchRepository(uow.conn).upsert(match)
        player_id = PlayerRepository(uow.conn).upsert(player)
        MatchPlayerRepository(uow.conn).upsert(_make_mp(
            match_id=4, player_id=player_id, hero_id=1,
            kills=5, deaths=3, assists=7,
            gpm=550, xpm=620, win=True,
            player_slot=0, lane_role=1, is_roaming=False,
            net_worth=18500, hero_damage=24000,
            tower_damage=3200, hero_healing=0, last_hits=180,
        ))

    with get_connection() as conn:
        row = conn.execute(
            "SELECT net_worth, hero_damage, tower_damage, hero_healing, last_hits "
            "FROM match_players WHERE player_slot = 0"
        ).fetchone()
        assert row["net_worth"] == 18500
        assert row["hero_damage"] == 24000
        assert row["tower_damage"] == 3200
        assert row["hero_healing"] == 0
        assert row["last_hits"] == 180


def test_match_player_performance_fields_nullable(db):
    """Performance поля можуть бути NULL для старих або непарсених матчів."""
    match = MatchDB(id=5, start_time=0, duration=1800, radiant_win=False, patch=None, region=None)
    player = PlayerDB(id=None, account_id=66, rank_tier=None, mmr=None)

    with UnitOfWork() as uow:
        MatchRepository(uow.conn).upsert(match)
        player_id = PlayerRepository(uow.conn).upsert(player)
        MatchPlayerRepository(uow.conn).upsert(_make_mp(
            match_id=5, player_id=player_id, hero_id=2,
            kills=2, deaths=4, assists=1,
            gpm=400, xpm=450, win=False,
            player_slot=3, lane_role=None, is_roaming=False,
        ))

    with get_connection() as conn:
        row = conn.execute(
            "SELECT net_worth, hero_damage FROM match_players WHERE player_slot = 3"
        ).fetchone()
        assert row["net_worth"] is None
        assert row["hero_damage"] is None


def test_rollback_on_error(db):
    match = MatchDB(id=99, start_time=0, duration=100, radiant_win=True, patch=None, region=None)

    with pytest.raises(RuntimeError):
        with UnitOfWork() as uow:
            MatchRepository(uow.conn).upsert(match)
            raise RuntimeError("щось пішло не так")

    with get_connection() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM matches WHERE id = 99"
        ).fetchone()[0] == 0