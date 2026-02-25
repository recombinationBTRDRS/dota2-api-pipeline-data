# services/ingestion/db/repositories.py
import sqlite3
from services.ingestion.db.models import MatchDB, PlayerDB, MatchPlayerDB


class MatchRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, match: MatchDB) -> None:
        self.conn.execute(
            """
            INSERT INTO matches (id, start_time, duration, radiant_win, patch, region)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                start_time=excluded.start_time,
                duration=excluded.duration,
                radiant_win=excluded.radiant_win,
                patch=excluded.patch,
                region=excluded.region
            """,
            (
                match.id,
                match.start_time,
                match.duration,
                match.radiant_win,
                match.patch,
                match.region,
            ),
        )


class PlayerRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, player: PlayerDB) -> int:
        self.conn.execute(
            """
            INSERT INTO players (account_id, rank_tier, mmr)
            VALUES (?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                rank_tier=excluded.rank_tier,
                mmr=excluded.mmr
            """,
            (player.account_id, player.rank_tier, player.mmr),
        )

        row = self.conn.execute(
            "SELECT id FROM players WHERE account_id = ?",
            (player.account_id,),
        ).fetchone()

        return int(row["id"])


class MatchPlayerRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, mp: MatchPlayerDB) -> None:
        self.conn.execute(
            """
            INSERT INTO match_players
            (match_id, player_id, hero_id, kills, deaths, assists, gpm, xpm, win)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, player_id) DO UPDATE SET
                hero_id=excluded.hero_id,
                kills=excluded.kills,
                deaths=excluded.deaths,
                assists=excluded.assists,
                gpm=excluded.gpm,
                xpm=excluded.xpm,
                win=excluded.win
            """,
            (
                mp.match_id,
                mp.player_id,
                mp.hero_id,
                mp.kills,
                mp.deaths,
                mp.assists,
                mp.gpm,
                mp.xpm,
                mp.win,
            ),
        )
