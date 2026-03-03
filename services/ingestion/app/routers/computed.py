# services/ingestion/app/routers/computed.py
"""Epic 5 — API endpoints for pre-computed analytics.

Endpoints:
    GET  /computed/heroes/top                        → list[HeroStatsResponse]
    GET  /computed/heroes/{hero_id}/stats            → list[HeroStatsResponse]
    GET  /computed/heroes/{hero_id}/items/{pos}      → list[ItemBuildResponse]
    GET  /computed/heroes/{hero_id}/matchups         → list[MatchupResponse]
    GET  /computed/heroes/{hero_id}/counters         → list[MatchupResponse]
    GET  /computed/heroes/{hero_id}/synergies        → list[SynergyResponse]
    GET  /computed/staleness                         → StalenessResponse
    POST /computed/rebuild                           → RebuildResponse
"""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from services.ingestion.db.repositories.analytics.computed import (
    ComputedHeroStatsRow,
    ComputedItemBuildRow,
    ComputedStatsRepository,
)
from services.ingestion.db.repositories.analytics.matchup import (
    MatchupRepository,
    MatchupRow,
    SynergyRow,
)
from services.ingestion.db.sqlite import get_connection

router = APIRouter(prefix="/computed", tags=["computed"])


# ── Response models ───────────────────────────────────────────────────────────

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


class MatchupResponse(BaseModel):
    hero_id: int
    opponent_id: int
    matches: int
    wins: int
    losses: int
    winrate: float
    computed_at: int


class SynergyResponse(BaseModel):
    hero_id: int
    ally_id: int
    matches: int
    wins: int
    losses: int
    winrate: float
    computed_at: int


class StalenessResponse(BaseModel):
    hero_stats_computed: int | None
    hero_item_build_computed: int | None
    hero_matchup_computed: int | None
    hero_synergy_computed: int | None


class RebuildResponse(BaseModel):
    status: str
    hero_stats_rows: int
    item_build_rows: int
    matchup_rows: int
    synergy_rows: int


# ── Mappers ───────────────────────────────────────────────────────────────────

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


def _matchup_to_response(row: MatchupRow) -> MatchupResponse:
    return MatchupResponse(
        hero_id=row.hero_id, opponent_id=row.opponent_id,
        matches=row.matches, wins=row.wins, losses=row.losses,
        winrate=row.winrate, computed_at=row.computed_at,
    )


def _synergy_to_response(row: SynergyRow) -> SynergyResponse:
    return SynergyResponse(
        hero_id=row.hero_id, ally_id=row.ally_id,
        matches=row.matches, wins=row.wins, losses=row.losses,
        winrate=row.winrate, computed_at=row.computed_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/heroes/top", response_model=list[HeroStatsResponse])
def get_top_heroes(
    primary_pos: Annotated[int | None, Query(ge=1, le=5)] = None,
    patch: int | None = Query(default=None),
    min_matches: Annotated[int, Query(ge=0)] = 20,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[HeroStatsResponse]:
    """Топ героїв за winrate DESC. Читається з hero_stats_computed."""
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


@router.get("/heroes/{hero_id}/stats", response_model=list[HeroStatsResponse])
def get_hero_stats(
    hero_id: Annotated[int, Path(ge=1)],
    patch: int | None = Query(default=None),
    region: int | None = Query(default=None),
) -> list[HeroStatsResponse]:
    """Stats героя з rollups по patch/region. NULL = aggregate over all."""
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
            detail=f"No computed stats for hero_id={hero_id}. Run /computed/rebuild first.",
        )
    return [_hero_stats_to_response(r) for r in rows]


@router.get("/heroes/{hero_id}/items/{primary_pos}", response_model=list[ItemBuildResponse])
def get_hero_items(
    hero_id: Annotated[int, Path(ge=1)],
    primary_pos: Annotated[int, Path(ge=1, le=5)],
    limit: Annotated[int, Query(ge=1, le=20)] = 6,
) -> list[ItemBuildResponse]:
    """Item build для героя на позиції. Відсортовано за times_bought DESC."""
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
            detail=f"No item build data for hero_id={hero_id}, pos={primary_pos}. Run rebuild first.",
        )
    return [_item_build_to_response(r) for r in rows]


@router.get("/heroes/{hero_id}/matchups", response_model=list[MatchupResponse])
def get_hero_matchups(
    hero_id: Annotated[int, Path(ge=1)],
    min_matches: Annotated[int, Query(ge=0)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[MatchupResponse]:
    """Matchups героя відсортовані за winrate DESC (кращі для hero_id зверху)."""
    conn = get_connection()
    try:
        rows = MatchupRepository(conn).get_hero_matchups(
            hero_id, min_matches=min_matches, limit=limit
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No matchup data for hero_id={hero_id}. Run /computed/rebuild first.",
        )
    return [_matchup_to_response(r) for r in rows]


@router.get("/heroes/{hero_id}/counters", response_model=list[MatchupResponse])
def get_hero_counters(
    hero_id: Annotated[int, Path(ge=1)],
    min_matches: Annotated[int, Query(ge=0)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[MatchupResponse]:
    """Hardest counters для hero_id — герої проти яких він програє найчастіше.

    Відсортовано за winrate ASC (найнижчий winrate = найгірший matchup для hero_id).
    """
    conn = get_connection()
    try:
        rows = MatchupRepository(conn).get_best_counters(
            hero_id, min_matches=min_matches, limit=limit
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No matchup data for hero_id={hero_id}. Run /computed/rebuild first.",
        )
    return [_matchup_to_response(r) for r in rows]


@router.get("/heroes/{hero_id}/synergies", response_model=list[SynergyResponse])
def get_hero_synergies(
    hero_id: Annotated[int, Path(ge=1)],
    min_matches: Annotated[int, Query(ge=0)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[SynergyResponse]:
    """Synergy союзників для hero_id відсортовані за winrate DESC."""
    conn = get_connection()
    try:
        rows = MatchupRepository(conn).get_hero_synergies(
            hero_id, min_matches=min_matches, limit=limit
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        conn.close()
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No synergy data for hero_id={hero_id}. Run /computed/rebuild first.",
        )
    return [_synergy_to_response(r) for r in rows]


@router.get("/staleness", response_model=StalenessResponse)
def get_staleness() -> StalenessResponse:
    """Час останнього rebuild для кожної pre-computed таблиці (Unix timestamp)."""
    conn = get_connection()
    try:
        hero_data = ComputedStatsRepository(conn).get_staleness()
        matchup_data = MatchupRepository(conn).get_staleness()
    finally:
        conn.close()
    return StalenessResponse(
        hero_stats_computed=hero_data.get("hero_stats_computed"),
        hero_item_build_computed=hero_data.get("hero_item_build_computed"),
        hero_matchup_computed=matchup_data.get("hero_matchup_computed"),
        hero_synergy_computed=matchup_data.get("hero_synergy_computed"),
    )


@router.post("/rebuild", status_code=200, response_model=RebuildResponse)
def trigger_rebuild() -> RebuildResponse:
    """Синхронний rebuild всіх pre-computed таблиць.

    Порядок: hero_stats → item_builds → matchups → synergies.
    200 OK — rebuild виконано синхронно.
    """
    from services.ingestion.app.rebuild_all import rebuild_all_computed

    result = rebuild_all_computed()
    return RebuildResponse(status="ok", **result)