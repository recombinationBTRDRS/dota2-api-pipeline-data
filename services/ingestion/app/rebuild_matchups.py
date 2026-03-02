# services/ingestion/app/rebuild_matchups.py
"""Epic 5.4 - Batch job: rebuild hero_matchup_computed (counter matrix).

is_radiant = player_slot < 128 (OpenDota convention).
Stores BOTH directions (A vs B) and (B vs A) for O(1) lookups.
DELETE always runs first to clear stale data.
"""
import logging
import time
from collections import defaultdict

from services.ingestion.db.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

_MATCHUP_SQL = """
    SELECT
        a.hero_id  AS hero_id,
        b.hero_id  AS opponent_id,
        a.win      AS hero_win
    FROM match_players a
    JOIN match_players b
        ON  b.match_id = a.match_id
        AND (a.player_slot < 128) != (b.player_slot < 128)
    WHERE a.hero_id != b.hero_id
"""


def rebuild_matchups() -> int:
    """Rebuild hero_matchup_computed from scratch.

    Returns:
        Number of rows written.
    """
    now = int(time.time())

    with UnitOfWork() as uow:
        conn = uow.conn

        conn.execute("DELETE FROM hero_matchup_computed")

        rows = conn.execute(_MATCHUP_SQL).fetchall()
        if not rows:
            logger.info("rebuild_matchups: no match data, table cleared")
            return 0

        aggs: dict = defaultdict(lambda: [0, 0])
        for row in rows:
            key = (row["hero_id"], row["opponent_id"])
            aggs[key][0] += 1
            aggs[key][1] += int(row["hero_win"])

        conn.executemany(
            "INSERT INTO hero_matchup_computed "
            "(hero_id, opponent_id, matches, wins, computed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                (hero_id, opponent_id, vals[0], vals[1], now)
                for (hero_id, opponent_id), vals in aggs.items()
            ),
        )

    count = len(aggs)
    logger.info("rebuild_matchups: saved %d rows", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    print(f"Done: {rebuild_matchups()} rows written to hero_matchup_computed")