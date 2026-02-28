# services/ingestion/app/routers/analytics.py
"""Analytics API endpoints (Task 4.5).

Endpoints:
    GET /heroes/{hero_id}/stats                  → HeroStatsRow
    GET /heroes/{hero_id}/stats/role/{pos}       → HeroRoleStatsRow
    GET /heroes/{hero_id}/items                  → list[ItemBuildEntry]
    GET /analytics/meta                          → list[MetaHeroRow]
    GET /analytics/leaderboard/{pos}             → list[HeroRoleStatsRow]
    GET /analytics/hero/{hero_id}/timeline       → list[MatchPhaseStatsRow]

Архітектурні рішення:
    - DB connection через FastAPI Depends (get_db) — одне з'єднання на запит
    - 404 якщо hero_id або дані не знайдені
    - Репозиторії отримують conn напряму — без UnitOfWork (read-only, no transactions needed)
    - Response моделі — Pydantic (окремі від db-layer dataclasses)
    - primary_pos приймається як int 1–5, валідується через Path(..., ge=1, le=5)
"""
import sqlite3
from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel

from services.ingestion.db.repositories import (
    HeroRoleStatsRow,
    HeroStatsRepository,
    HeroStatsRow,
    ItemBuildEntry,
    ItemBuildRepository,
    MatchPhaseStatsRow,
    MatchTimelineRepository,
    MetaHeroRow,
)
from services.ingestion.db.sqlite import get_connection

router = APIRouter()


# ── DB dependency ─────────────────────────────────────────────────────────────

def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency: відкриває і закриває DB з'єднання на кожен запит."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


DBConn = Annotated[sqlite3.Connection, Depends(get_db)]


# ── Response models ───────────────────────────────────────────────────────────
# Окремі від db-layer dataclasses — не повертаємо internal поля назовні.

class HeroStatsResponse(BaseModel):
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


class HeroRoleStatsResponse(BaseModel):
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


class ItemBuildResponse(BaseModel):
    item_id: int
    item_name: str | None
    times_bought: int
    pickrate: float
    win_pickrate: float


class MetaHeroResponse(BaseModel):
    hero_id: int
    hero_name: str | None
    primary_pos: int
    matches_played: int
    wins: int
    winrate: float
    pickrate: float
    meta_score: float


class MatchPhaseStatsResponse(BaseModel):
    hero_id: int
    phase: str
    matches_played: int
    wins: int
    winrate: float
    avg_gpm: float
    avg_kills: float


# ── mappers db-layer → response ───────────────────────────────────────────────

def _hero_stats_to_response(row: HeroStatsRow) -> HeroStatsResponse:
    return HeroStatsResponse(
        hero_id=row.hero_id, hero_name=row.hero_name,
        matches_played=row.matches_played, wins=row.wins, losses=row.losses,
        winrate=row.winrate, avg_kills=row.avg_kills, avg_deaths=row.avg_deaths,
        avg_assists=row.avg_assists, avg_gpm=row.avg_gpm, avg_xpm=row.avg_xpm,
    )


def _role_stats_to_response(row: HeroRoleStatsRow) -> HeroRoleStatsResponse:
    return HeroRoleStatsResponse(
        hero_id=row.hero_id, hero_name=row.hero_name, primary_pos=row.primary_pos,
        matches_played=row.matches_played, wins=row.wins, losses=row.losses,
        winrate=row.winrate, avg_kills=row.avg_kills, avg_deaths=row.avg_deaths,
        avg_assists=row.avg_assists, avg_gpm=row.avg_gpm,
    )


def _item_to_response(row: ItemBuildEntry) -> ItemBuildResponse:
    return ItemBuildResponse(
        item_id=row.item_id, item_name=row.item_name,
        times_bought=row.times_bought, pickrate=row.pickrate,
        win_pickrate=row.win_pickrate,
    )


def _meta_to_response(row: MetaHeroRow) -> MetaHeroResponse:
    return MetaHeroResponse(
        hero_id=row.hero_id, hero_name=row.hero_name, primary_pos=row.primary_pos,
        matches_played=row.matches_played, wins=row.wins,
        winrate=row.winrate, pickrate=row.pickrate, meta_score=row.meta_score,
    )


def _phase_to_response(row: MatchPhaseStatsRow) -> MatchPhaseStatsResponse:
    return MatchPhaseStatsResponse(
        hero_id=row.hero_id, phase=row.phase,
        matches_played=row.matches_played, wins=row.wins,
        winrate=row.winrate, avg_gpm=row.avg_gpm, avg_kills=row.avg_kills,
    )


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/heroes/{hero_id}/stats", response_model=HeroStatsResponse)
def get_hero_stats(
    hero_id: Annotated[int, Path(ge=1)],
    conn: DBConn,
    min_matches: Annotated[int, Query(ge=1)] = 1,
) -> HeroStatsResponse:
    """Загальна статистика героя: winrate, avg KDA, avg GPM.

    404 якщо hero_id не знайдений або має менше min_matches матчів.
    """
    stats = HeroStatsRepository(conn).get_hero_stats(hero_id)
    if stats is None or stats.matches_played < min_matches:
        raise HTTPException(status_code=404, detail=f"Hero {hero_id} not found or insufficient data")
    return _hero_stats_to_response(stats)


@router.get(
    "/heroes/{hero_id}/stats/role/{primary_pos}",
    response_model=HeroRoleStatsResponse,
)
def get_hero_stats_by_role(
    hero_id: Annotated[int, Path(ge=1)],
    primary_pos: Annotated[int, Path(ge=1, le=5)],
    conn: DBConn,
) -> HeroRoleStatsResponse:
    """Статистика героя на конкретній позиції (1=carry..5=hard_support).

    404 якщо немає даних для цього героя на цій позиції.
    """
    stats = HeroStatsRepository(conn).get_hero_stats_by_role(hero_id, primary_pos)
    if stats is None:
        raise HTTPException(
            status_code=404,
            detail=f"No data for hero {hero_id} at position {primary_pos}",
        )
    return _role_stats_to_response(stats)


@router.get("/heroes/{hero_id}/items", response_model=list[ItemBuildResponse])
def get_hero_items(
    hero_id: Annotated[int, Path(ge=1)],
    conn: DBConn,
    win_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
) -> list[ItemBuildResponse]:
    """Топ предметів для героя за pickrate.

    win_only=true — тільки виграні матчі.
    Порожній список якщо нема даних (не 404).
    """
    entries = ItemBuildRepository(conn).get_hero_item_build(hero_id, win_only, limit)
    return [_item_to_response(e) for e in entries]


@router.get("/analytics/meta", response_model=list[MetaHeroResponse])
def get_meta_snapshot(
    conn: DBConn,
    primary_pos: Annotated[int | None, Query(ge=1, le=5)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[MetaHeroResponse]:
    """Топ героїв по meta_score (winrate * pickrate * 100).

    primary_pos: 1-5 для фільтру по позиції, або без параметру — всі позиції.
    """
    rows = MatchTimelineRepository(conn).get_meta_snapshot(primary_pos, limit)
    return [_meta_to_response(r) for r in rows]


@router.get(
    "/analytics/leaderboard/{primary_pos}",
    response_model=list[HeroRoleStatsResponse],
)
def get_role_leaderboard(
    primary_pos: Annotated[int, Path(ge=1, le=5)],
    conn: DBConn,
    min_matches: Annotated[int, Query(ge=1)] = 10,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> list[HeroRoleStatsResponse]:
    """Топ героїв на позиції primary_pos за winrate DESC."""
    rows = HeroStatsRepository(conn).get_role_leaderboard(primary_pos, min_matches, limit)
    return [_role_stats_to_response(r) for r in rows]


@router.get(
    "/analytics/hero/{hero_id}/timeline",
    response_model=list[MatchPhaseStatsResponse],
)
def get_hero_timeline(
    hero_id: Annotated[int, Path(ge=1)],
    conn: DBConn,
) -> list[MatchPhaseStatsResponse]:
    """Статистика героя по фазах гри (early/mid/late).

    Порожній список якщо нема даних (не 404).
    """
    rows = MatchTimelineRepository(conn).get_hero_phase_stats(hero_id)
    return [_phase_to_response(r) for r in rows]