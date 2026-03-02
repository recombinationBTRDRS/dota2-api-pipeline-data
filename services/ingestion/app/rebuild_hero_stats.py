# services/ingestion/app/rebuild_hero_stats.py
"""Epic 5.1 — Batch job: перебудова hero_stats_computed.

Читає з match_players + hero_role_scores (raw data).
Записує агреговані рядки в hero_stats_computed (pre-computed layer).

Запускається:
    - вручну: python -m services.ingestion.app.rebuild_hero_stats
    - після кожного ingestion циклу (опціонально, налаштовується)
    - за розкладом через scheduler (Epic 5.3)

Стратегія: повний REPLACE — видаляємо старі рядки героя і вставляємо нові.
Це гарантує консистентність при зміні вхідних даних (нові матчі, зміна схеми).
"""
import logging
import time

from services.ingestion.db.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)


def rebuild_hero_stats() -> int:
    """Перебудовує hero_stats_computed з нуля.

    Returns:
        Кількість збережених рядків.
    """
    now = int(time.time())

    with UnitOfWork() as uow:
        conn = uow.conn

        # Агрегуємо по (hero_id, patch, region, primary_pos).
        # patch/region беруться з matches — можуть бути NULL.
        # primary_pos береться з hero_role_scores (статична роль).
        # NULL patch/region залишаємо як є — окремі рядки агрегату.
        rows = conn.execute("""
            SELECT
                mp.hero_id,
                m.patch,
                m.region,
                hrs.primary_pos,
                COUNT(*)        AS matches_played,
                SUM(mp.win)     AS wins,
                SUM(mp.kills)   AS total_kills,
                SUM(mp.deaths)  AS total_deaths,
                SUM(mp.assists) AS total_assists,
                SUM(mp.gpm)     AS total_gpm,
                SUM(mp.xpm)     AS total_xpm
            FROM match_players mp
            JOIN matches m ON m.id = mp.match_id
            JOIN hero_role_scores hrs ON hrs.hero_id = mp.hero_id
            GROUP BY mp.hero_id, m.patch, m.region, hrs.primary_pos
        """).fetchall()

        if not rows:
            logger.info("rebuild_hero_stats: no match data yet, skipping")
            return 0

        # Повний rebuild: очищаємо і вставляємо заново
        conn.execute("DELETE FROM hero_stats_computed")

        conn.executemany(
            """
            INSERT INTO hero_stats_computed
                (hero_id, patch, region, primary_pos,
                 matches_played, wins,
                 total_kills, total_deaths, total_assists,
                 total_gpm, total_xpm, computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    row["hero_id"],
                    row["patch"],
                    row["region"],
                    row["primary_pos"],
                    row["matches_played"],
                    row["wins"],
                    row["total_kills"],
                    row["total_deaths"],
                    row["total_assists"],
                    row["total_gpm"],
                    row["total_xpm"],
                    now,
                )
                for row in rows
            ),
        )

    count = len(rows)
    logger.info("rebuild_hero_stats: saved %d rows, computed_at=%d", count, now)
    return count


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    n = rebuild_hero_stats()
    print(f"Done: {n} rows written to hero_stats_computed")