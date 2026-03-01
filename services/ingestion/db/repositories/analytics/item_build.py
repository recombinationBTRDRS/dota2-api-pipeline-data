# services/ingestion/db/repositories/analytics/item_build.py
"""Analytics: популярність item builds по герою (Epic 4.3)."""
import sqlite3
from dataclasses import dataclass


@dataclass(slots=True)
class ItemBuildEntry:
    """Агрегований запис популярності предмету (db-layer, не domain DTO).

    times_bought: кількість матчів де герой мав цей item.
    pickrate: times_bought / total_matches, округлено 4 знаки.
    win_pickrate: times in wins / total_wins, округлено 4 знаки. 0.0 якщо wins=0.
    """
    item_id: int
    item_name: str | None
    times_bought: int
    pickrate: float
    win_pickrate: float


class ItemBuildRepository:
    """Read-only аналітика: популярність items по герою."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_hero_item_build(
        self,
        hero_id: int,
        win_only: bool = False,
        limit: int = 6,
    ) -> list[ItemBuildEntry]:
        """Топ items для героя за pickrate DESC.

        win_only: рахувати тільки виграні матчі.
        limit: max записів (default 6 = повний build).
        Один SQL запит — без N+1 (win_times через LEFT JOIN subquery).
        """
        win_filter = "AND mp.win = 1" if win_only else ""

        total_row = self.conn.execute(
            f"SELECT COUNT(DISTINCT mp.match_id) FROM match_players mp "
            f"WHERE mp.hero_id = ? {win_filter}",
            (hero_id,),
        ).fetchone()
        total = int(total_row[0]) if total_row else 0
        if total == 0:
            return []

        total_wins_row = self.conn.execute(
            "SELECT COUNT(DISTINCT match_id) FROM match_players "
            "WHERE hero_id = ? AND win = 1",
            (hero_id,),
        ).fetchone()
        total_wins = int(total_wins_row[0]) if total_wins_row else 0

        rows = self.conn.execute(
            f"""
            SELECT
                mpi.item_id,
                i.localized_name,
                COUNT(DISTINCT mpi.match_id)        AS times_bought,
                COALESCE(win_counts.win_times, 0)   AS win_times
            FROM match_player_items mpi
            JOIN match_players mp
                ON mp.match_id = mpi.match_id
               AND mp.player_slot = mpi.player_slot
            LEFT JOIN items i ON i.id = mpi.item_id
            LEFT JOIN (
                SELECT mpi2.item_id, COUNT(DISTINCT mpi2.match_id) AS win_times
                FROM match_player_items mpi2
                JOIN match_players mp2
                    ON mp2.match_id = mpi2.match_id
                   AND mp2.player_slot = mpi2.player_slot
                WHERE mp2.hero_id = ? AND mp2.win = 1
                GROUP BY mpi2.item_id
            ) win_counts ON win_counts.item_id = mpi.item_id
            WHERE mp.hero_id = ? {win_filter}
            GROUP BY mpi.item_id
            ORDER BY times_bought DESC
            LIMIT ?
            """,
            (hero_id, hero_id, limit),
        ).fetchall()

        return [
            ItemBuildEntry(
                item_id=row["item_id"],
                item_name=row["localized_name"],
                times_bought=int(row["times_bought"]),
                pickrate=round(int(row["times_bought"]) / total, 4),
                win_pickrate=round(int(row["win_times"]) / total_wins, 4)
                if total_wins > 0 else 0.0,
            )
            for row in rows
        ]