# services/ingestion/app/routers/computed.py
"""Epic 5 — API endpoints для pre-computed аналітики.

Читає з hero_stats_computed і hero_item_build_computed.
Окремий router — підключається в main.py.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.ingestion.db.repositories.analytics.computed import (
    ComputedHeroStatsRow,
    ComputedItemBuildRow,
    ComputedStatsRepository,
)
from services.ingestion.db.sqlite import get_connection

router = APIRouter(prefix="/computed", tags=["computed"])


# ── Response schemas ──────────────────────────────────────────────────────────

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


def _hero_stats_to_response(row: ComputedHeroStatsRow) -> HeroStatsResponse:
    return HeroStatsResponse(
        hero_id=row.hero_id,
        hero_name=row.hero_name,
        primary_pos=row.primary_pos,
        patch=row.patch,
        region=row.region,
        matches_played=row.matches_played,
        wins=row.wins,
        losses=row.losses,
        winrate=row.winrate,
        avg_kills=row.avg_kills,
        avg_deaths=row.avg_deaths,
        avg_assists=row.avg_assists,
        avg_gpm=row.avg_gpm,
        avg_xpm=row.avg_xpm,
        computed_at=row.computed_at,
    )


def _item_build_to_response(row: ComputedItemBuildRow) -> ItemBuildResponse:
    return ItemBuildResponse(
        item_id=row.item_id,
        item_name=row.item_name,
        times_bought=row.times_bought,
        times_won=row.times_won,
        win_rate=row.win_rate,
        computed_at=row.computed_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/heroes/{hero_id}/stats", response_model=list[HeroStatsResponse])
def get_hero_stats(
    hero_id: int,
    patch: int | None = Query(default=None, description="Фільтр по патчу"),
    region: int | None = Query(default=None, description="Фільтр по регіону"),
) -> list[HeroStatsResponse]:
    """Статистика героя по ролях (з pre-computed таблиці).

    Повертає список рядків — по одному на кожну primary_pos.
    patch/region=None → агрегат по всіх патчах/регіонах.
    """
    conn = get_connection()
    try:
        rows = ComputedStatsRepository(conn).get_hero_stats(
            hero_id, patch=patch, region=region
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No computed stats for hero_id={hero_id}. Run rebuild first."
        )
    return [_hero_stats_to_response(r) for r in rows]


@router.get("/heroes/top", response_model=list[HeroStatsResponse])
def get_top_heroes(
    primary_pos: int | None = Query(default=None, ge=1, le=5),
    patch: int | None = Query(default=None),
    min_matches: int = Query(default=20, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
) -> list[HeroStatsResponse]:
    """Топ героїв по winrate (з pre-computed таблиці)."""
    conn = get_connection()
    try:
        rows = ComputedStatsRepository(conn).get_top_by_winrate(
            primary_pos=primary_pos,
            patch=patch,
            min_matches=min_matches,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()

    return [_hero_stats_to_response(r) for r in rows]


@router.get("/heroes/{hero_id}/items/{primary_pos}", response_model=list[ItemBuildResponse])
def get_hero_items(
    hero_id: int,
    primary_pos: int,
    limit: int = Query(default=6, ge=1, le=20),
) -> list[ItemBuildResponse]:
    """Популярні items героя на позиції (з pre-computed таблиці)."""
    if primary_pos not in (1, 2, 3, 4, 5):
        raise HTTPException(status_code=422, detail="primary_pos must be 1-5")

    conn = get_connection()
    try:
        rows = ComputedStatsRepository(conn).get_item_build(
            hero_id, primary_pos, limit=limit
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No item build data for hero_id={hero_id}, pos={primary_pos}."
        )
    return [_item_build_to_response(r) for r in rows]


@router.get("/staleness", response_model=StalenessResponse)
def get_staleness() -> StalenessResponse:
    """Повертає unix timestamp останнього rebuild кожної pre-computed таблиці.

    None = rebuild ще не запускався.
    """
    conn = get_connection()
    try:
        data = ComputedStatsRepository(conn).get_staleness()
    finally:
        conn.close()

    return StalenessResponse(**data)


@router.post("/rebuild", status_code=202)
def trigger_rebuild() -> dict:
    """Запускає синхронний rebuild всіх pre-computed таблиць.

    202 Accepted — rebuild виконується синхронно в цьому запиті.
    Для async rebuild використовуй scheduler (Epic 5.3).
    """
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    stats_count = rebuild_hero_stats()
    items_count = rebuild_item_builds()

    return {
        "status": "ok",
        "hero_stats_rows": stats_count,
        "item_build_rows": items_count,
    }