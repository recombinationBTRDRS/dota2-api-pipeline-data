# services/ingestion/db/repositories/matches.py
"""Репозиторії для матчів і логу інгестації.

Класи:
    MatchRepository          — matches table
    MatchPlayerRepository    — match_players table
    MatchPlayerItemRepository— match_player_items table
    IngestionLogRepository   — ingestion_log table
"""
import sqlite3

from services.ingestion.db.models import (
    IngestionLogDB,
    MatchPlayerDB,
    MatchPlayerItemDB,
)
from services.ingestion.db.models import (
    MatchDB as DBMatch,
)
from services.ingestion.db.repositories.base import _MAX_ERROR_LEN


class MatchRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, match: DBMatch) -> None:
        self.conn.execute(
            """
            INSERT INTO matches (id, start_time, duration, radiant_win, patch, region)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                start_time  = excluded.start_time,
                duration    = excluded.duration,
                radiant_win = excluded.radiant_win,
                patch       = excluded.patch,
                region      = excluded.region
            """,
            (match.id, match.start_time, match.duration,
             match.radiant_win, match.patch, match.region),
        )


class MatchPlayerRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, mp: MatchPlayerDB) -> None:
        self.conn.execute(
            """
            INSERT INTO match_players
                (match_id, player_slot, player_id, hero_id,
                 kills, deaths, assists, gpm, xpm, win)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id, player_slot) DO UPDATE SET
                player_id = excluded.player_id,
                hero_id   = excluded.hero_id,
                kills     = excluded.kills,
                deaths    = excluded.deaths,
                assists   = excluded.assists,
                gpm       = excluded.gpm,
                xpm       = excluded.xpm,
                win       = excluded.win
            """,
            (mp.match_id, mp.player_slot, mp.player_id, mp.hero_id,
             mp.kills, mp.deaths, mp.assists, mp.gpm, mp.xpm, mp.win),
        )


class MatchPlayerItemRepository:
    """Зберігає предмети гравців у матчі.

    Write-only — читання через ItemBuildRepository (analytics/item_build.py).
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert_batch(self, items: list[MatchPlayerItemDB]) -> None:
        """Ідемпотентне збереження.

        DO UPDATE — відповідає архітектурному правилу upsert.
        Items є immutable після матчу (snapshot кінцевого стану).
        """
        self.conn.executemany(
            """
            INSERT INTO match_player_items (match_id, player_slot, slot, item_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(match_id, player_slot, slot) DO UPDATE SET
                item_id = excluded.item_id
            """,
            [(i.match_id, i.player_slot, i.slot, i.item_id) for i in items],
        )


class IngestionLogRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def is_known(self, match_id: int) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM ingestion_log WHERE match_id = ? AND status = 'ok'",
            (match_id,),
        ).fetchone()
        return row is not None

    def mark_ok(self, match_id: int, ingested_at: int) -> None:
        self.conn.execute(
            """
            INSERT INTO ingestion_log (match_id, status, ingested_at, error)
            VALUES (?, 'ok', ?, NULL)
            ON CONFLICT(match_id) DO UPDATE SET
                status      = 'ok',
                ingested_at = excluded.ingested_at,
                error       = NULL
            """,
            (match_id, ingested_at),
        )

    def mark_failed(self, match_id: int, ingested_at: int, error: str) -> None:
        self.conn.execute(
            """
            INSERT INTO ingestion_log (match_id, status, ingested_at, error)
            VALUES (?, 'failed', ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                status      = 'failed',
                ingested_at = excluded.ingested_at,
                error       = excluded.error
            """,
            (match_id, ingested_at, error[:_MAX_ERROR_LEN]),
        )

    def get(self, match_id: int) -> IngestionLogDB | None:
        row = self.conn.execute(
            "SELECT match_id, status, ingested_at, error "
            "FROM ingestion_log WHERE match_id = ?",
            (match_id,),
        ).fetchone()
        if row is None:
            return None
        return IngestionLogDB(
            match_id=row["match_id"],
            status=row["status"],
            ingested_at=row["ingested_at"],
            error=row["error"],
        )