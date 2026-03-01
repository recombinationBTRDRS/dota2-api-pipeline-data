# services/ingestion/db/repositories/players.py
"""Репозиторій для гравців."""
import sqlite3

from services.ingestion.db.models import PlayerDB


class PlayerRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, player: PlayerDB) -> int:
        """Зберігає гравця і повертає його внутрішній id.

        Якщо account_id is None (anonymous) — завжди INSERT новий рядок.
        Якщо account_id відомий — upsert по account_id.
        """
        if player.account_id is None:
            cur = self.conn.execute(
                "INSERT INTO players (rank_tier, mmr) VALUES (?, ?)",
                (player.rank_tier, player.mmr),
            )
            lastrowid = cur.lastrowid
            if lastrowid is None:
                raise RuntimeError("INSERT INTO players did not return a lastrowid")
            return int(lastrowid)

        self.conn.execute(
            "INSERT OR IGNORE INTO players (account_id, rank_tier, mmr) VALUES (?, ?, ?)",
            (player.account_id, player.rank_tier, player.mmr),
        )
        self.conn.execute(
            "UPDATE players SET rank_tier = ?, mmr = ? WHERE account_id = ?",
            (player.rank_tier, player.mmr, player.account_id),
        )
        row = self.conn.execute(
            "SELECT id FROM players WHERE account_id = ?",
            (player.account_id,),
        ).fetchone()
        return int(row["id"])