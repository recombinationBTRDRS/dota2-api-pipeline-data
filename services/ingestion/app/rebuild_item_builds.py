# services/ingestion/app/rebuild_item_builds.py
"""Epic 5.2 — Batch job: rebuild hero_item_build_computed.

DELETE always runs first to clear stale data even when source is empty.
"""
import logging
import time

from services.ingestion.db.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


def rebuild_item_builds() -> int:
    now = int(time.time())
    with UnitOfWork() as uow:
        conn = uow.conn
        conn.execute("DELETE FROM hero_item_build_computed")
        rows = conn.execute("""
            SELECT mp.hero_id, hrs.primary_pos, mpi.item_id,
                COUNT(*) AS times_bought, SUM(mp.win) AS times_won
            FROM match_player_items mpi
            JOIN match_players mp ON mp.match_id = mpi.match_id AND mp.player_slot = mpi.player_slot
            JOIN hero_role_scores hrs ON hrs.hero_id = mp.hero_id
            GROUP BY mp.hero_id, hrs.primary_pos, mpi.item_id
        """).fetchall()
        if not rows:
            logger.info("rebuild_item_builds: no item data, table cleared")
            return 0
        conn.executemany(
            """INSERT INTO hero_item_build_computed
               (hero_id, primary_pos, item_id, times_bought, times_won, computed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                (row["hero_id"], row["primary_pos"], row["item_id"],
                 row["times_bought"], row["times_won"], now)
                for row in rows
            ),
        )
    count = len(rows)
    logger.info("rebuild_item_builds: saved %d rows", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    print(f"Done: {rebuild_item_builds()} rows written to hero_item_build_computed")