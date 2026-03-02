# services/ingestion/db/repositories/analytics/matchup.py
"""Epic 5.4/5.5 — Read repository for matchup and synergy pre-computed tables."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(slots=True)
class MatchupRow:
    hero_id: int
    opponent_id: int
    matches: int
    wins: int
    losses: int
    winrate: float
    computed_at: int


@dataclass(slots=True)
class SynergyRow:
    hero_id: int
    ally_id: int
    matches: int
    wins: int
    losses: int
    winrate: float
    computed_at: int


class MatchupRepository:
    """Read-only access to hero_matchup_computed and hero_synergy_computed."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    # ── matchups ──────────────────────────────────────────────────────────────

    def get_hero_matchups(
        self,
        hero_id: int,
        *,
        min_matches: int = 1,
        limit: int = 20,
    ) -> list[MatchupRow]:
        """Повертає список суперників відсортованих за winrate DESC.

        Args:
            hero_id: ID героя якого аналізуємо.
            min_matches: Мінімальна кількість матчів проти суперника.
            limit: Максимальна кількість результатів (1-100).

        Raises:
            ValueError: hero_id <= 0, min_matches < 0, limit < 1.
        """
        if hero_id <= 0:
            raise ValueError("hero_id must be int > 0")
        if min_matches < 0:
            raise ValueError("min_matches must be >= 0")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be 1-100")

        rows = self._conn.execute(
            """
            SELECT hero_id, opponent_id, matches, wins, computed_at
            FROM hero_matchup_computed
            WHERE hero_id = ? AND matches >= ?
            ORDER BY CAST(wins AS REAL) / matches DESC
            LIMIT ?
            """,
            (hero_id, min_matches, limit),
        ).fetchall()

        return [_to_matchup(r) for r in rows]

    def get_best_counters(
        self,
        hero_id: int,
        *,
        min_matches: int = 1,
        limit: int = 10,
    ) -> list[MatchupRow]:
        """Топ героїв що добре грають ПРОТИ hero_id (його найгірші matchups).

        Шукаємо з точки зору суперника: де opponent_id = hero_id і winrate суперника високий.
        Тобто: де hero_id програє найчастіше.
        """
        if hero_id <= 0:
            raise ValueError("hero_id must be int > 0")
        if min_matches < 0:
            raise ValueError("min_matches must be >= 0")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be 1-100")

        rows = self._conn.execute(
            """
            SELECT hero_id, opponent_id, matches, wins, computed_at
            FROM hero_matchup_computed
            WHERE hero_id = ? AND matches >= ?
            ORDER BY CAST(wins AS REAL) / matches ASC
            LIMIT ?
            """,
            (hero_id, min_matches, limit),
        ).fetchall()

        return [_to_matchup(r) for r in rows]

    # ── synergies ─────────────────────────────────────────────────────────────

    def get_hero_synergies(
        self,
        hero_id: int,
        *,
        min_matches: int = 1,
        limit: int = 20,
    ) -> list[SynergyRow]:
        """Повертає список союзників відсортованих за winrate DESC.

        Шукає в обох напрямках (hero_id може бути як hero_id так і ally_id).

        Raises:
            ValueError: hero_id <= 0, min_matches < 0, limit < 1.
        """
        if hero_id <= 0:
            raise ValueError("hero_id must be int > 0")
        if min_matches < 0:
            raise ValueError("min_matches must be >= 0")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be 1-100")

        rows = self._conn.execute(
            """
            SELECT
                CASE WHEN hero_id = ? THEN ally_id ELSE hero_id END AS ally_id,
                matches, wins, computed_at
            FROM hero_synergy_computed
            WHERE (hero_id = ? OR ally_id = ?) AND matches >= ?
            ORDER BY CAST(wins AS REAL) / matches DESC
            LIMIT ?
            """,
            (hero_id, hero_id, hero_id, min_matches, limit),
        ).fetchall()

        return [_to_synergy(hero_id, r) for r in rows]

    def get_staleness(self) -> dict[str, int | None]:
        """Повертає computed_at останнього rebuild для кожної таблиці."""
        def _latest(table: str) -> int | None:
            row = self._conn.execute(
                f"SELECT MAX(computed_at) AS ts FROM {table}"  # noqa: S608
            ).fetchone()
            return row["ts"] if row else None

        return {
            "hero_matchup_computed": _latest("hero_matchup_computed"),
            "hero_synergy_computed": _latest("hero_synergy_computed"),
        }


# ── helpers ───────────────────────────────────────────────────────────────────

def _to_matchup(row: sqlite3.Row) -> MatchupRow:
    matches = row["matches"]
    wins = row["wins"]
    winrate = round(wins / matches, 4) if matches > 0 else 0.0
    return MatchupRow(
        hero_id=row["hero_id"],
        opponent_id=row["opponent_id"],
        matches=matches,
        wins=wins,
        losses=matches - wins,
        winrate=winrate,
        computed_at=row["computed_at"],
    )


def _to_synergy(hero_id: int, row: sqlite3.Row) -> SynergyRow:
    matches = row["matches"]
    wins = row["wins"]
    winrate = round(wins / matches, 4) if matches > 0 else 0.0
    ally_id = row["ally_id"]
    return SynergyRow(
        hero_id=hero_id,
        ally_id=ally_id,
        matches=matches,
        wins=wins,
        losses=matches - wins,
        winrate=winrate,
        computed_at=row["computed_at"],
    )