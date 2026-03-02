# services/ingestion/app/routers/computed.py
"""Epic 5 — API endpoints for pre-computed analytics."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from services.ingestion.db.repositories.analytics.computed import (
    ComputedHeroStatsRow,
    ComputedItemBuildRow,
    ComputedStatsRepository,
)
from services.ingestion.db.sqlite import get_connection

router = APIRouter(prefix="/computed", tags=["computed"])


class HeroStatsResponse(BaseModel):
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


class ItemBuildResponse(BaseModel):
    item_id: int
    item_name: str | None
    times_bought: int
    times_won: int
    win_rate: float
    computed_at: int


class StalenessResponse(BaseModel):
    hero_stats_computed: int | None
    hero_item_build_computed: int | None


class RebuildResponse(BaseModel):
    status: str
    hero_stats_rows: int
    item_build_rows: int


def _hero_stats_to_response(row: ComputedHeroStatsRow) -> HeroStatsResponse:
    return HeroStatsResponse(
        hero_id=row.hero_id, hero_name=row.hero_name, primary_pos=row.primary_pos,
        patch=row.patch, region=row.region, matches_played=row.matches_played,
        wins=row.wins, losses=row.losses, winrate=row.winrate,
        avg_kills=row.avg_kills, avg_deaths=row.avg_deaths, avg_assists=row.avg_assists,
        avg_gpm=row.avg_gpm, avg_xpm=row.avg_xpm, computed_at=row.computed_at,
    )


def _item_build_to_response(row: ComputedItemBuildRow) -> ItemBuildResponse:
    return ItemBuildResponse(
        item_id=row.item_id, item_name=row.item_name,
        times_bought=row.times_bought, times_won=row.times_won,
        win_rate=row.win_rate, computed_at=row.computed_at,
    )


@router.get("/heroes/{hero_id}/stats", response_model=list[HeroStatsResponse])
def get_hero_stats(
    hero_id: Annotated[int, Path(ge=1)],
    patch: int | None = Query(default=None),
    region: int | None = Query(default=None),
) -> list[HeroStatsResponse]:
    conn = get_connection()
    try:
        rows = ComputedStatsRepository(conn).get_hero_stats(hero_id, patch=patch, region=region)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No computed stats for hero_id={hero_id}. Run rebuild first.",
        )
    return [_hero_stats_to_response(r) for r in rows]


@router.get("/heroes/top", response_model=list[HeroStatsResponse])
def get_top_heroes(
    primary_pos: Annotated[int | None, Query(ge=1, le=5)] = None,
    patch: int | None = Query(default=None),
    min_matches: Annotated[int, Query(ge=0)] = 20,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[HeroStatsResponse]:
    conn = get_connection()
    try:
        rows = ComputedStatsRepository(conn).get_top_by_winrate(
            primary_pos=primary_pos, patch=patch, min_matches=min_matches, limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()
    return [_hero_stats_to_response(r) for r in rows]


@router.get("/heroes/{hero_id}/items/{primary_pos}", response_model=list[ItemBuildResponse])
def get_hero_items(
    hero_id: Annotated[int, Path(ge=1)],
    primary_pos: Annotated[int, Path(ge=1, le=5)],
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
) -> list[ItemBuildResponse]:
    conn = get_connection()
    try:
        rows = ComputedStatsRepository(conn).get_item_build(hero_id, primary_pos, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No item build data for hero_id={hero_id}, pos={primary_pos}.",
        )
    return [_item_build_to_response(r) for r in rows]


@router.get("/staleness", response_model=StalenessResponse)
def get_staleness() -> StalenessResponse:
    conn = get_connection()
    try:
        data = ComputedStatsRepository(conn).get_staleness()
    finally:
        conn.close()
    return StalenessResponse(**data)


@router.post("/rebuild", status_code=200, response_model=RebuildResponse)
def trigger_rebuild() -> RebuildResponse:
    """Синхронний атомарний rebuild всіх pre-computed таблиць.

    Обидві таблиці оновлюються в одній транзакції.
    200 OK — rebuild виконано синхронно в цьому запиті.
    """
    from services.ingestion.app.rebuild_all import rebuild_all_computed

    result = rebuild_all_computed()
    return RebuildResponse(status="ok", **result)