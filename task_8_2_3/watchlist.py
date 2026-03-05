# services/analysis/db/repositories/watchlist.py
import sqlite3
import time
from dataclasses import dataclass


@dataclass
class WatchlistRow:
    id: int
    match_id: int
    added_at: int
    label: str | None
    status: str
    error: str | None


class WatchlistRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, match_id: int, label: str | None = None) -> WatchlistRow:
        """Додати match_id у watchlist. Якщо вже є — повернути існуючий."""
        existing = self.get(match_id)
        if existing:
            return existing
        now = int(time.time())
        cur = self._conn.execute(
            "INSERT INTO watchlist (match_id, added_at, label) VALUES (?, ?, ?)",
            (match_id, now, label),
        )
        return WatchlistRow(
            id=cur.lastrowid,
            match_id=match_id,
            added_at=now,
            label=label,
            status="pending",
            error=None,
        )

    def get(self, match_id: int) -> WatchlistRow | None:
        row = self._conn.execute(
            "SELECT id, match_id, added_at, label, status, error "
            "FROM watchlist WHERE match_id = ?",
            (match_id,),
        ).fetchone()
        return self._row(row) if row else None

    def get_all(self) -> list[WatchlistRow]:
        rows = self._conn.execute(
            "SELECT id, match_id, added_at, label, status, error "
            "FROM watchlist ORDER BY added_at DESC"
        ).fetchall()
        return [self._row(r) for r in rows]

    def delete(self, match_id: int) -> bool:
        cur = self._conn.execute(
            "DELETE FROM watchlist WHERE match_id = ?", (match_id,)
        )
        return cur.rowcount > 0

    def update_status(
        self, match_id: int, status: str, error: str | None = None
    ) -> None:
        self._conn.execute(
            "UPDATE watchlist SET status = ?, error = ? WHERE match_id = ?",
            (status, error, match_id),
        )

    @staticmethod
    def _row(r: sqlite3.Row) -> WatchlistRow:
        return WatchlistRow(
            id=r["id"],
            match_id=r["match_id"],
            added_at=r["added_at"],
            label=r["label"],
            status=r["status"],
            error=r["error"],
        )
