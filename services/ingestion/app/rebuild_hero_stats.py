# services/ingestion/app/rebuild_hero_stats.py
"""Epic 5.1 — Batch job: rebuild hero_stats_computed.

Стратегія: повний DELETE + INSERT.
DELETE завжди виконується — навіть якщо source порожній, щоб очистити stale дані.

Rollup логіка:
  Замість UNION ALL в SQL (що дає дублікати коли patch/region вже NULL),
  агрегуємо granular рядки в Python і будуємо rollups програмно.
  Для кожного унікального (hero_id, primary_pos) генеруємо 4 рядки:
    (patch, region)  — granular
    (patch, None)    — rollup по регіонах
    (None,  region)  — rollup по патчах
    (None,  None)    — глобальний агрегат

  Дублікати при групуванні (напр. patch вже NULL в source) усуваються
  через dict-ключ (hero_id, patch_key, region_key, primary_pos).
"""
import logging
import sqlite3
import time
from collections import defaultdict

from services.ingestion.db.unit_of_work import UnitOfWork

logger = logging.getLogger(__name__)

# Тип агрегату: (hero_id, patch|None, region|None, primary_pos) -> [mp, wins, k, d, a, gpm, xpm]
_Agg = dict

_GRANULAR_SQL = """
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
"""

_INSERT_SQL = """
    INSERT INTO hero_stats_computed
        (hero_id, patch, region, primary_pos,
         matches_played, wins,
         total_kills, total_deaths, total_assists,
         total_gpm, total_xpm, computed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _make_agg() -> list:
    return [0, 0, 0, 0, 0, 0, 0]  # mp, wins, kills, deaths, assists, gpm, xpm


def _add(agg: list, row: sqlite3.Row) -> None:
    agg[0] += row["matches_played"]
    agg[1] += row["wins"]
    agg[2] += row["total_kills"]
    agg[3] += row["total_deaths"]
    agg[4] += row["total_assists"]
    agg[5] += row["total_gpm"]
    agg[6] += row["total_xpm"]


def _build_rollups(granular_rows: list) -> dict:
    """Будує всі rollup варіанти в Python.

    Повертає dict: (hero_id, patch, region, primary_pos) -> [mp, wins, ...]
    де patch/region можуть бути None (rollup sentinel).

    Дублікати автоматично складаються — якщо granular patch вже None,
    rollup (None, region) і granular (None, region) дадуть один ключ.
    """
    aggs: _Agg = defaultdict(_make_agg)

    for row in granular_rows:
        h = row["hero_id"]
        p = row["patch"]    # може бути None
        r = row["region"]   # може бути None
        pos = row["primary_pos"]

        # granular
        _add(aggs[(h, p, r, pos)], row)
        # rollup: patch зберігаємо, region=None
        if r is not None:
            _add(aggs[(h, p, None, pos)], row)
        # rollup: patch=None, region зберігаємо
        if p is not None:
            _add(aggs[(h, None, r, pos)], row)
        # rollup: обидва None (глобальний агрегат)
        if p is not None and r is not None:
            _add(aggs[(h, None, None, pos)], row)

    return aggs


def rebuild_hero_stats() -> int:
    """Перебудовує hero_stats_computed з нуля.

    Returns:
        Кількість збережених рядків.
    """
    now = int(time.time())

    with UnitOfWork() as uow:
        conn = uow.conn

        # DELETE завжди — гарантує чисту таблицю навіть при порожньому source
        conn.execute("DELETE FROM hero_stats_computed")

        granular = conn.execute(_GRANULAR_SQL).fetchall()
        if not granular:
            logger.info("rebuild_hero_stats: no match data, table cleared")
            return 0

        aggs = _build_rollups(granular)

        conn.executemany(
            _INSERT_SQL,
            (
                (hero_id, patch, region, primary_pos,
                 vals[0], vals[1], vals[2], vals[3], vals[4], vals[5], vals[6],
                 now)
                for (hero_id, patch, region, primary_pos), vals in aggs.items()
            ),
        )

    count = len(aggs)
    logger.info("rebuild_hero_stats: saved %d rows", count)
    return count


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    print(f"Done: {rebuild_hero_stats()} rows written to hero_stats_computed")