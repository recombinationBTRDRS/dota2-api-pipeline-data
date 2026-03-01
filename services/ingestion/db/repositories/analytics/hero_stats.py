# services/ingestion/db/repositories/analytics/hero_stats.py
"""Analytics: winrate / pickrate / KDA по героях і ролях (Epic 4.1, 4.2)."""
import sqlite3
from dataclasses import dataclass


@dataclass(slots=True)
class HeroStatsRow:
    """Агрегована статистика героя (db-layer, не domain DTO)."""
    hero_id: int
    hero_name: str | None
    matches_played: int
    wins: int
    losses: int
    winrate: float
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_gpm: float
    avg_xpm: float


@dataclass(slots=True)
class HeroRoleStatsRow:
    """Агрегована статистика героя на позиції (db-layer, не domain DTO).

    primary_pos: int 1–5. Маппінг → Role enum виконується в app-шарі.
    """
    hero_id: int
    hero_name: str | None
    primary_pos: int
    matches_played: int
    wins: int
    losses: int
    winrate: float
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_gpm: float


def _build_hero_stats_row(row: sqlite3.Row) -> HeroStatsRow:
    matches = int(row["matches_played"])
    wins = int(row["wins"])
    return HeroStatsRow(
        hero_id=row["hero_id"],
        hero_name=row["localized_name"],
        matches_played=matches,
        wins=wins,
        losses=matches - wins,
        winrate=round(wins / matches, 4) if matches > 0 else 0.0,
        avg_kills=round(float(row["avg_kills"]), 2),
        avg_deaths=round(float(row["avg_deaths"]), 2),
        avg_assists=round(float(row["avg_assists"]), 2),
        avg_gpm=round(float(row["avg_gpm"]), 2),
        avg_xpm=round(float(row["avg_xpm"]), 2),
    )


def _build_hero_role_stats_row(row: sqlite3.Row) -> HeroRoleStatsRow:
    matches = int(row["matches_played"])
    wins = int(row["wins"])
    return HeroRoleStatsRow(
        hero_id=row["hero_id"],
        hero_name=row["localized_name"],
        primary_pos=int(row["primary_pos"]),
        matches_played=matches,
        wins=wins,
        losses=matches - wins,
        winrate=round(wins / matches, 4) if matches > 0 else 0.0,
        avg_kills=round(float(row["avg_kills"]), 2),
        avg_deaths=round(float(row["avg_deaths"]), 2),
        avg_assists=round(float(row["avg_assists"]), 2),
        avg_gpm=round(float(row["avg_gpm"]), 2),
    )


_HERO_STATS_SQL = """
    SELECT
        mp.hero_id,
        h.localized_name,
        COUNT(*)        AS matches_played,
        SUM(mp.win)     AS wins,
        AVG(mp.kills)   AS avg_kills,
        AVG(mp.deaths)  AS avg_deaths,
        AVG(mp.assists) AS avg_assists,
        AVG(mp.gpm)     AS avg_gpm,
        AVG(mp.xpm)     AS avg_xpm
    FROM match_players mp
    LEFT JOIN heroes h ON h.id = mp.hero_id
"""

_HERO_ROLE_STATS_SQL = """
    SELECT
        mp.hero_id,
        h.localized_name,
        hrs.primary_pos,
        COUNT(*)        AS matches_played,
        SUM(mp.win)     AS wins,
        AVG(mp.kills)   AS avg_kills,
        AVG(mp.deaths)  AS avg_deaths,
        AVG(mp.assists) AS avg_assists,
        AVG(mp.gpm)     AS avg_gpm
    FROM match_players mp
    JOIN heroes h ON h.id = mp.hero_id
    JOIN hero_role_scores hrs ON hrs.hero_id = mp.hero_id
"""


class HeroStatsRepository:
    """Read-only аналітика по героях і ролях."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_hero_stats(self, hero_id: int) -> HeroStatsRow | None:
        row = self.conn.execute(
            _HERO_STATS_SQL + "WHERE mp.hero_id = ? GROUP BY mp.hero_id",
            (hero_id,),
        ).fetchone()
        return _build_hero_stats_row(row) if row is not None else None

    def get_all_heroes_stats(self, min_matches: int = 10) -> list[HeroStatsRow]:
        rows = self.conn.execute(
            _HERO_STATS_SQL + """
            GROUP BY mp.hero_id
            HAVING COUNT(*) >= ?
            ORDER BY mp.hero_id
            """,
            (min_matches,),
        ).fetchall()
        return [_build_hero_stats_row(r) for r in rows]

    def get_top_by_winrate(self, limit: int = 10, min_matches: int = 20) -> list[HeroStatsRow]:
        rows = self.conn.execute(
            _HERO_STATS_SQL + """
            GROUP BY mp.hero_id
            HAVING COUNT(*) >= ?
            ORDER BY (SUM(mp.win) * 1.0 / COUNT(*)) DESC
            LIMIT ?
            """,
            (min_matches, limit),
        ).fetchall()
        return [_build_hero_stats_row(r) for r in rows]

    def get_hero_stats_by_role(self, hero_id: int, primary_pos: int) -> HeroRoleStatsRow | None:
        if primary_pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"primary_pos must be 1-5, got {primary_pos}")
        row = self.conn.execute(
            _HERO_ROLE_STATS_SQL + """
            WHERE mp.hero_id = ? AND hrs.primary_pos = ?
            GROUP BY mp.hero_id
            """,
            (hero_id, primary_pos),
        ).fetchone()
        return _build_hero_role_stats_row(row) if row is not None else None

    def get_role_leaderboard(
        self, primary_pos: int, min_matches: int = 10, limit: int = 20,
    ) -> list[HeroRoleStatsRow]:
        if primary_pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"primary_pos must be 1-5, got {primary_pos}")
        rows = self.conn.execute(
            _HERO_ROLE_STATS_SQL + """
            WHERE hrs.primary_pos = ?
            GROUP BY mp.hero_id
            HAVING COUNT(*) >= ?
            ORDER BY (SUM(mp.win) * 1.0 / COUNT(*)) DESC
            LIMIT ?
            """,
            (primary_pos, min_matches, limit),
        ).fetchall()
        return [_build_hero_role_stats_row(r) for r in rows]