# services/ingestion/db/repositories/players.py
"""Репозиторій для гравців."""
import sqlite3

from services.ingestion.db.models import PlayerDB


class PlayerRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def upsert(self, player: PlayerDB) -> int:
        """Зберігає гравця і повертає його внутрішній id.

        Анонімні гравці (account_id is None) — завжди INSERT новий рядок
        (кожен анонімний слот унікальний в межах матчу).

        Відомі гравці — атомарний ON CONFLICT upsert по account_id.
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

        # Атомарний upsert — відповідає архітектурному правилу ON CONFLICT DO UPDATE.
        # Замість non-atomic INSERT OR IGNORE + UPDATE + SELECT (3 statements).
        cur = self.conn.execute(
            """
            INSERT INTO players (account_id, rank_tier, mmr)
            VALUES (?, ?, ?)
            ON CONFLICT(account_id) DO UPDATE SET
                rank_tier = excluded.rank_tier,
                mmr       = excluded.mmr
            RETURNING id
            """,
            (player.account_id, player.rank_tier, player.mmr),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(
                f"Upsert players did not return id for account_id={player.account_id}"
            )
        return int(row[0])