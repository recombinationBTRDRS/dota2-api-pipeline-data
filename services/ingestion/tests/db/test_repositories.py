# services/ingestion/tests/db/test_repositories.py
import tempfile
from pathlib import Path

from services.ingestion.db.sqlite import init_db, get_connection
from services.ingestion.db.repositories import (
    MatchRepository,
    PlayerRepository,
    MatchPlayerRepository,
)
from services.ingestion.db.models import MatchDB, PlayerDB, MatchPlayerDB


def test_repositories_upsert(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.sqlite"

        # підміняємо шлях до DB
        from services.ingestion.db import sqlite as sqlite_module

        monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)

        init_db()

        match_repo = MatchRepository()
        player_repo = PlayerRepository()
        mp_repo = MatchPlayerRepository()

        match = MatchDB(
            id=1,
            start_time=111,
            duration=222,
            radiant_win=True,
            patch=7,
            region=2,
        )

        match_repo.upsert(match)
        match_repo.upsert(match)  # ідемпотентність

        player = PlayerDB(id=None, account_id=123, rank_tier=5, mmr=4500.0)
        player_id = player_repo.upsert(player)
        player_id2 = player_repo.upsert(player)

        assert player_id == player_id2

        mp = MatchPlayerDB(
            match_id=1,
            player_id=player_id,
            hero_id=46,
            kills=10,
            deaths=2,
            assists=5,
            gpm=600,
            xpm=700,
            win=True,
        )

        mp_repo.upsert(mp)
        mp_repo.upsert(mp)  # ідемпотентність

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM match_players")
        count = cur.fetchone()["c"]
        conn.close()

        assert count == 1