# services/ingestion/app/rebuild_item_builds.py
"""Epic 5.2 — Batch job: перебудова hero_item_build_computed.

Читає з match_player_items + match_players + hero_role_scores.
Записує агреговані item build рядки в hero_item_build_computed.

times_bought = скільки разів item був у гравця в матчі
times_won    = скільки разів item був у переможця
"""
import logging
import time

from services.ingestion.db.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


def rebuild_item_builds() -> int:
    """Перебудовує hero_item_build_computed з нуля.

    Returns:
        Кількість збережених рядків.
    """
    now = int(time.time())

    with UnitOfWork() as uow:
        conn = uow.conn

        rows = conn.execute("""
            SELECT
                mp.hero_id,
                hrs.primary_pos,
                mpi.item_id,
                COUNT(*)        AS times_bought,
                SUM(mp.win)     AS times_won
            FROM match_player_items mpi
            JOIN match_players mp
                ON mp.match_id = mpi.match_id
               AND mp.player_slot = mpi.player_slot
            JOIN hero_role_scores hrs ON hrs.hero_id = mp.hero_id
            GROUP BY mp.hero_id, hrs.primary_pos, mpi.item_id
        """).fetchall()

        if not rows:
            logger.info("rebuild_item_builds: no item data yet, skipping")
            return 0

        conn.execute("DELETE FROM hero_item_build_computed")

        conn.executemany(
            """
            INSERT INTO hero_item_build_computed
                (hero_id, primary_pos, item_id, times_bought, times_won, computed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    row["hero_id"],
                    row["primary_pos"],
                    row["item_id"],
                    row["times_bought"],
                    row["times_won"],
                    now,
                )
                for row in rows
            ),
        )

    count = len(rows)
    logger.info("rebuild_item_builds: saved %d rows, computed_at=%d", count, now)
    return count


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    n = rebuild_item_builds()
    print(f"Done: {n} rows written to hero_item_build_computed")