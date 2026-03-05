# services/analysis/app/routers/reports.py
import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from services.analysis.app.analyzers.draft import DraftAnalyzer
from services.analysis.app.analyzers.economy import EconomyAnalyzer
from services.analysis.app.analyzers.teamfight import TeamfightAnalyzer
from services.analysis.app.clients.ingestion import IngestionClient, IngestionUnavailableError
from services.analysis.db.repositories.report import ReportRepository
from services.analysis.db.repositories.watchlist import WatchlistRepository
from services.analysis.db.unit_of_work import UnitOfWork
from services.analysis.domains.reports.dtos import MatchReport

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


# ── Pydantic response schemas ─────────────────────────────────────────────────

class DraftScoreOut(BaseModel):
    synergy_score: float | None
    counter_score: float | None
    overall: float | None
    top_synergies: list[dict[str, Any]]
    top_counters: list[dict[str, Any]]
    data_quality: str


class PlayerEconomyOut(BaseModel):
    hero_id: int
    is_radiant: bool
    gpm: int
    net_worth: int | None
    avg_gpm_for_hero: float | None
    gpm_delta: float | None
    gpm_rating: str


class EconomySnapshotOut(BaseModel):
    players: list[PlayerEconomyOut]
    radiant_total_networth: int
    dire_total_networth: int
    networth_advantage: str
    radiant_avg_gpm: float
    dire_avg_gpm: float


class TeamfightSnapshotOut(BaseModel):
    radiant_kills: int
    dire_kills: int
    kill_ratio: float
    radiant_avg_kda: float
    dire_avg_kda: float
    teamfight_verdict: str


class MatchReportOut(BaseModel):
    match_id: int
    generated_at: int
    draft: DraftScoreOut | None
    economy: EconomySnapshotOut | None
    teamfight: TeamfightSnapshotOut | None
    data_quality: str


# ── helpers ───────────────────────────────────────────────────────────────────

def _data_quality(report: MatchReport) -> str:
    filled = sum([
        report.draft is not None,
        report.economy is not None,
        report.teamfight is not None,
    ])
    return {3: "complete", 2: "partial"}.get(filled, "minimal")


def _to_response(report: MatchReport) -> MatchReportOut:
    draft_out = None
    if report.draft:
        draft_out = DraftScoreOut(
            synergy_score=report.draft.synergy_score,
            counter_score=report.draft.counter_score,
            overall=report.draft.overall,
            top_synergies=report.draft.top_synergies,
            top_counters=report.draft.top_counters,
            data_quality=report.draft.data_quality,
        )

    economy_out = None
    if report.economy:
        economy_out = EconomySnapshotOut(
            players=[PlayerEconomyOut(**p.__dict__) for p in report.economy.players],
            radiant_total_networth=report.economy.radiant_total_networth,
            dire_total_networth=report.economy.dire_total_networth,
            networth_advantage=report.economy.networth_advantage,
            radiant_avg_gpm=report.economy.radiant_avg_gpm,
            dire_avg_gpm=report.economy.dire_avg_gpm,
        )

    teamfight_out = None
    if report.teamfight:
        teamfight_out = TeamfightSnapshotOut(
            radiant_kills=report.teamfight.radiant_kills,
            dire_kills=report.teamfight.dire_kills,
            kill_ratio=report.teamfight.kill_ratio,
            radiant_avg_kda=report.teamfight.radiant_avg_kda,
            dire_avg_kda=report.teamfight.dire_avg_kda,
            teamfight_verdict=report.teamfight.teamfight_verdict,
        )

    return MatchReportOut(
        match_id=report.match_id,
        generated_at=report.generated_at,
        draft=draft_out,
        economy=economy_out,
        teamfight=teamfight_out,
        data_quality=report.data_quality,
    )


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/matches/{match_id}",
    response_model=MatchReportOut,
    status_code=status.HTTP_200_OK,
    summary="Generate (or regenerate) a match report",
)
def generate_report(match_id: int) -> MatchReportOut:
    # 1. Перевірити що match_id є у watchlist
    with UnitOfWork() as uow:
        wl_row = WatchlistRepository(uow.conn).get(match_id)
    if not wl_row:
        raise HTTPException(
            status_code=404,
            detail=f"match_id {match_id} not in watchlist — add it first via POST /watchlist/matches",
        )

    client = IngestionClient()

    # 2. Отримати гравців матчу
    try:
        players = client.get_match_players(match_id)
    except IngestionUnavailableError as exc:
        raise HTTPException(status_code=503, detail=f"Ingestion unavailable: {exc}") from exc

    # 3. Розрахувати герої по командах (із players або з watchlist label як fallback)
    radiant = [p for p in players if p.get("is_radiant")]
    dire    = [p for p in players if not p.get("is_radiant")]
    radiant_ids = [p["hero_id"] for p in radiant]
    dire_ids    = [p["hero_id"] for p in dire]

    # 4. Analyzers
    draft     = DraftAnalyzer(client).analyze(radiant_ids, dire_ids) if radiant_ids and dire_ids else None
    economy   = EconomyAnalyzer(client).analyze(players)             if players else None
    teamfight = TeamfightAnalyzer().analyze(players)                  if players else None

    # 5. Зібрати звіт
    report = MatchReport(
        match_id=match_id,
        generated_at=int(time.time()),
        draft=draft,
        economy=economy,
        teamfight=teamfight,
    )
    report.data_quality = _data_quality(report)

    # 6. Зберегти + оновити watchlist status
    with UnitOfWork() as uow:
        ReportRepository(uow.conn).save(report)
        WatchlistRepository(uow.conn).update_status(match_id, "analyzed")

    logger.info(
        "Report generated: match_id=%d quality=%s draft=%s economy=%s teamfight=%s",
        match_id, report.data_quality,
        "ok" if report.draft else "none",
        "ok" if report.economy else "none",
        "ok" if report.teamfight else "none",
    )
    return _to_response(report)


@router.get(
    "/matches/{match_id}",
    response_model=MatchReportOut,
    summary="Get a previously generated match report",
)
def get_report(match_id: int) -> MatchReportOut:
    with UnitOfWork() as uow:
        report = ReportRepository(uow.conn).get(match_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No report for match_id {match_id} — generate it first via POST /reports/matches/{match_id}",
        )
    return _to_response(report)
