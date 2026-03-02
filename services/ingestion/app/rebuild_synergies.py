# services/ingestion/app/rebuild_synergies.py
"""Epic 5.5 - Batch job: rebuild hero_synergy_computed (synergy matrix).

hero_id < ally_id always - avoids duplicate pairs (A,B) and (B,A).
is_radiant = player_slot < 128 (OpenDota convention).
DELETE always runs first to clear stale data.
"""
import logging
import time
from collections import defaultdict

from services.ingestion.db.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

_SYNERGY_SQL = """
    SELECT
        a.hero_id AS hero_id,
        b.hero_id AS ally_id,
        a.win     AS win
    FROM match_players a
    JOIN match_players b
        ON  b.match_id = a.match_id
        AND (a.player_slot < 128) = (b.player_slot < 128)
        AND a.hero_id < b.hero_id
"""


def rebuild_synergies() -> int:
    """Rebuild hero_synergy_computed from scratch.

    Returns:
        Number of rows written.
    """
    now = int(time.time())

    with UnitOfWork() as uow:
        conn = uow.conn

        conn.execute("DELETE FROM hero_synergy_computed")

        rows = conn.execute(_SYNERGY_SQL).fetchall()
        if not rows:
            logger.info("rebuild_synergies: no match data, table cleared")
            return 0

        aggs: dict = defaultdict(lambda: [0, 0])
        for row in rows:
            key = (row["hero_id"], row["ally_id"])
            aggs[key][0] += 1
            aggs[key][1] += int(row["win"])

        conn.executemany(
            "INSERT INTO hero_synergy_computed "
            "(hero_id, ally_id, matches, wins, computed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                (hero_id, ally_id, vals[0], vals[1], now)
                for (hero_id, ally_id), vals in aggs.items()
            ),
        )

    count = len(aggs)
    logger.info("rebuild_synergies: saved %d rows", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    print(f"Done: {rebuild_synergies()} rows written to hero_synergy_computed")