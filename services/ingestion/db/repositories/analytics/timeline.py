# services/ingestion/db/repositories/analytics/timeline.py
"""Analytics: match timeline (early/mid/late) і meta snapshot (Epic 4.4)."""
import sqlite3
from dataclasses import dataclass

from services.ingestion.db.repositories.base import _EARLY_MAX, _MID_MAX


@dataclass(slots=True)
class MatchPhaseStatsRow:
    """Статистика героя в фазі гри (db-layer, не domain DTO).

    phase: 'early' | 'mid' | 'late' — по matches.duration.
    """
    hero_id: int
    phase: str
    matches_played: int
    wins: int
    winrate: float
    avg_gpm: float
    avg_kills: float


@dataclass(slots=True)
class MetaHeroRow:
    """Meta snapshot — герой + позиція + meta_score (db-layer, не domain DTO).

    meta_score = winrate * pickrate * 100, округлено 2 знаки.
    primary_pos: int 1–5. Маппінг → Role enum виконується в app-шарі.
    """
    hero_id: int
    hero_name: str | None
    primary_pos: int
    matches_played: int
    wins: int
    winrate: float
    pickrate: float
    meta_score: float


class MatchTimelineRepository:
    """Read-only аналітика: фази гри і meta snapshot."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_hero_phase_stats(self, hero_id: int) -> list[MatchPhaseStatsRow]:
        """Статистика героя по фазах (до 3 записів, порядок early→mid→late).

        Фази без матчів не повертаються.
        Пороги: early ≤ {_EARLY_MAX}s, mid ≤ {_MID_MAX}s, late > {_MID_MAX}s.
        """
        rows = self.conn.execute(
            f"""
            SELECT
                mp.hero_id,
                CASE
                    WHEN m.duration <= {_EARLY_MAX} THEN 'early'
                    WHEN m.duration <= {_MID_MAX}   THEN 'mid'
                    ELSE 'late'
                END AS phase,
                COUNT(*)    AS matches_played,
                SUM(mp.win) AS wins,
                AVG(mp.gpm) AS avg_gpm,
                AVG(mp.kills) AS avg_kills
            FROM match_players mp
            JOIN matches m ON m.id = mp.match_id
            WHERE mp.hero_id = ?
            GROUP BY phase
            ORDER BY
                CASE phase
                    WHEN 'early' THEN 1
                    WHEN 'mid'   THEN 2
                    ELSE              3
                END
            """,
            (hero_id,),
        ).fetchall()

        result = []
        for row in rows:
            matches = int(row["matches_played"])
            wins = int(row["wins"])
            result.append(MatchPhaseStatsRow(
                hero_id=hero_id,
                phase=row["phase"],
                matches_played=matches,
                wins=wins,
                winrate=round(wins / matches, 4) if matches > 0 else 0.0,
                avg_gpm=round(float(row["avg_gpm"]), 2),
                avg_kills=round(float(row["avg_kills"]), 2),
            ))
        return result

    def get_meta_snapshot(
        self,
        primary_pos: int | None = None,
        limit: int = 10,
    ) -> list[MetaHeroRow]:
        """Топ героїв за meta_score = winrate * pickrate * 100.

        primary_pos: None = всі позиції, 1-5 = фільтр.
        Герої без hero_role_scores виключаються (INNER JOIN).
        """
        if primary_pos is not None and primary_pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"primary_pos must be 1-5 or None, got {primary_pos}")

        total_row = self.conn.execute(
            "SELECT COUNT(DISTINCT match_id) FROM match_players"
        ).fetchone()
        total = int(total_row[0]) if total_row else 0
        if total == 0:
            return []

        pos_filter = "AND hrs.primary_pos = ?" if primary_pos is not None else ""
        params: tuple[int, ...] = (primary_pos, limit) if primary_pos is not None else (limit,)

        rows = self.conn.execute(
            f"""
            SELECT
                mp.hero_id,
                h.localized_name,
                hrs.primary_pos,
                COUNT(*)    AS matches_played,
                SUM(mp.win) AS wins
            FROM match_players mp
            JOIN heroes h ON h.id = mp.hero_id
            JOIN hero_role_scores hrs ON hrs.hero_id = mp.hero_id
            WHERE 1=1 {pos_filter}
            GROUP BY mp.hero_id
            ORDER BY
                (SUM(mp.win) * 1.0 / COUNT(*))
                * (COUNT(*) * 1.0 / {total})
                * 100 DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        result = []
        for row in rows:
            matches = int(row["matches_played"])
            wins = int(row["wins"])
            winrate = round(wins / matches, 4) if matches > 0 else 0.0
            pickrate = round(matches / total, 4)
            result.append(MetaHeroRow(
                hero_id=row["hero_id"],
                hero_name=row["localized_name"],
                primary_pos=int(row["primary_pos"]),
                matches_played=matches,
                wins=wins,
                winrate=winrate,
                pickrate=pickrate,
                meta_score=round(winrate * pickrate * 100, 2),
            ))
        return result