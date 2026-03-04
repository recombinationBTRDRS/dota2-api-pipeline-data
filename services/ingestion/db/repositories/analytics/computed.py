# services/ingestion/db/repositories/analytics/computed.py
"""Epic 5 — Read репозиторій для pre-computed таблиць.

Читає ТІЛЬКИ з hero_stats_computed і hero_item_build_computed.
Не читає з match_players — це відповідальність batch jobs.
"""
import sqlite3
from dataclasses import dataclass


@dataclass(slots=True)
class ComputedHeroStatsRow:
    """Агрегована статистика героя з pre-computed таблиці."""
    hero_id: int
    hero_name: str | None
    primary_pos: int
    patch: int | None
    region: int | None
    matches_played: int
    wins: int
    losses: int
    winrate: float
    avg_kills: float
    avg_deaths: float
    avg_assists: float
    avg_gpm: float
    avg_xpm: float
    computed_at: int


@dataclass(slots=True)
class ComputedItemBuildRow:
    """Агрегований item build з pre-computed таблиці."""
    hero_id: int
    primary_pos: int
    item_id: int
    item_name: str | None
    times_bought: int
    times_won: int
    win_rate: float       # times_won / times_bought
    computed_at: int


def _build_hero_stats(row: sqlite3.Row) -> ComputedHeroStatsRow:
    m = int(row["matches_played"])
    w = int(row["wins"])
    return ComputedHeroStatsRow(
        hero_id=row["hero_id"],
        hero_name=row["localized_name"],
        primary_pos=int(row["primary_pos"]),
        patch=row["patch"],
        region=row["region"],
        matches_played=m,
        wins=w,
        losses=m - w,
        winrate=round(w / m, 4) if m > 0 else 0.0,
        avg_kills=round(row["total_kills"] / m, 2) if m > 0 else 0.0,
        avg_deaths=round(row["total_deaths"] / m, 2) if m > 0 else 0.0,
        avg_assists=round(row["total_assists"] / m, 2) if m > 0 else 0.0,
        avg_gpm=round(row["total_gpm"] / m, 2) if m > 0 else 0.0,
        avg_xpm=round(row["total_xpm"] / m, 2) if m > 0 else 0.0,
        computed_at=int(row["computed_at"]),
    )


def _build_item_build(row: sqlite3.Row) -> ComputedItemBuildRow:
    bought = int(row["times_bought"])
    won = int(row["times_won"])
    return ComputedItemBuildRow(
        hero_id=row["hero_id"],
        primary_pos=int(row["primary_pos"]),
        item_id=row["item_id"],
        item_name=row["localized_name"],
        times_bought=bought,
        times_won=won,
        win_rate=round(won / bought, 4) if bought > 0 else 0.0,
        computed_at=int(row["computed_at"]),
    )


class ComputedStatsRepository:
    """Read-only репозиторій pre-computed аналітики."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def get_hero_stats(
        self,
        hero_id: int,
        *,
        patch: int | None = None,
        region: int | None = None,
    ) -> list[ComputedHeroStatsRow]:
        """Повертає статистику героя по всіх ролях.

        patch=None  → повертає всі рядки включно з rollups (patch IS NULL)
        patch=59    → тільки рядки з patch=59
        Аналогічно для region.
        """
        if not isinstance(hero_id, int) or hero_id <= 0:
            raise ValueError(f"hero_id must be int > 0, got {hero_id!r}")

        rows = self.conn.execute(
            """
            SELECT hsc.*, h.localized_name
            FROM hero_stats_computed hsc
            LEFT JOIN heroes h ON h.id = hsc.hero_id
            WHERE hsc.hero_id = ?
              AND (? IS NULL OR hsc.patch = ?)
              AND (? IS NULL OR hsc.region = ?)
            ORDER BY hsc.primary_pos
            """,
            (hero_id, patch, patch, region, region),
        ).fetchall()
        return [_build_hero_stats(r) for r in rows]

    def get_top_by_winrate(
        self,
        *,
        primary_pos: int | None = None,
        patch: int | None = None,
        min_matches: int = 20,
        limit: int = 10,
    ) -> list[ComputedHeroStatsRow]:
        """Топ героїв по winrate.

        Завжди повертає тільки глобальні агрегати (patch IS NULL AND region IS NULL).
        Параметр patch фільтрує по patch — але тільки серед глобальних агрегатів
        це не має сенсу, тому patch тут зарезервований для майбутнього і ігнорується.

        primary_pos=None → всі позиції (один рядок на героя — найкраща позиція).
        primary_pos=2    → тільки pos=2.
        """
        if not isinstance(min_matches, int) or min_matches < 0:
            raise ValueError(f"min_matches must be int >= 0, got {min_matches!r}")
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"limit must be int > 0, got {limit!r}")
        if primary_pos is not None and primary_pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"primary_pos must be 1-5 or None, got {primary_pos}")

        rows = self.conn.execute(
            """
            SELECT hsc.*, h.localized_name
            FROM hero_stats_computed hsc
            LEFT JOIN heroes h ON h.id = hsc.hero_id
            WHERE hsc.matches_played >= ?
              AND (? IS NULL OR hsc.primary_pos = ?)
              AND hsc.patch IS NULL
              AND hsc.region IS NULL
            ORDER BY (hsc.wins * 1.0 / hsc.matches_played) DESC
            LIMIT ?
            """,
            (min_matches, primary_pos, primary_pos, limit),
        ).fetchall()
        return [_build_hero_stats(r) for r in rows]

    def get_item_build(
        self,
        hero_id: int,
        primary_pos: int,
        *,
        limit: int = 6,
    ) -> list[ComputedItemBuildRow]:
        """Топ items для героя на позиції з pre-computed таблиці."""
        if not isinstance(hero_id, int) or hero_id <= 0:
            raise ValueError(f"hero_id must be int > 0, got {hero_id!r}")
        if primary_pos not in (1, 2, 3, 4, 5):
            raise ValueError(f"primary_pos must be 1-5, got {primary_pos}")
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"limit must be int > 0, got {limit!r}")

        rows = self.conn.execute(
            """
            SELECT hibc.*, i.localized_name
            FROM hero_item_build_computed hibc
            LEFT JOIN items i ON i.id = hibc.item_id
            WHERE hibc.hero_id = ? AND hibc.primary_pos = ?
            ORDER BY hibc.times_bought DESC
            LIMIT ?
            """,
            (hero_id, primary_pos, limit),
        ).fetchall()
        return [_build_item_build(r) for r in rows]

    def get_staleness(self) -> dict[str, int | None]:
        """Повертає unix timestamp останнього rebuild кожної таблиці."""
        def _latest(table: str) -> int | None:
            row = self.conn.execute(
                f"SELECT MAX(computed_at) as t FROM {table}"
            ).fetchone()
            return int(row["t"]) if row and row["t"] is not None else None

        return {
            "hero_stats_computed": _latest("hero_stats_computed"),
            "hero_item_build_computed": _latest("hero_item_build_computed"),
        }