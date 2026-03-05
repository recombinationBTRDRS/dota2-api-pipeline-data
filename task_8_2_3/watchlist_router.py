# services/analysis/app/routers/watchlist.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from services.analysis.db.repositories.watchlist import WatchlistRepository
from services.analysis.db.unit_of_work import UnitOfWork

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


# ── Pydantic schemas ────────────────────────────────────────────────────────

class WatchlistAddRequest(BaseModel):
    match_id: int
    label: str | None = None


class WatchlistResponse(BaseModel):
    id: int
    match_id: int
    status: str
    label: str | None
    added_at: int
    error: str | None = None


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post(
    "/matches",
    response_model=WatchlistResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_match(body: WatchlistAddRequest) -> WatchlistResponse:
    """Додати матч у watchlist."""
    with UnitOfWork() as uow:
        repo = WatchlistRepository(uow.conn)
        existing = repo.get(body.match_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"match_id {body.match_id} already in watchlist",
            )
        row = repo.add(body.match_id, body.label)
    return WatchlistResponse(
        id=row.id,
        match_id=row.match_id,
        status=row.status,
        label=row.label,
        added_at=row.added_at,
    )


@router.get("/matches", response_model=list[WatchlistResponse])
def list_matches() -> list[WatchlistResponse]:
    """Список усіх матчів у watchlist."""
    with UnitOfWork() as uow:
        rows = WatchlistRepository(uow.conn).get_all()
    return [
        WatchlistResponse(
            id=r.id,
            match_id=r.match_id,
            status=r.status,
            label=r.label,
            added_at=r.added_at,
            error=r.error,
        )
        for r in rows
    ]


@router.get("/matches/{match_id}", response_model=WatchlistResponse)
def get_match(match_id: int) -> WatchlistResponse:
    """Отримати один запис watchlist."""
    with UnitOfWork() as uow:
        row = WatchlistRepository(uow.conn).get(match_id)
    if not row:
        raise HTTPException(status_code=404, detail="not found")
    return WatchlistResponse(
        id=row.id,
        match_id=row.match_id,
        status=row.status,
        label=row.label,
        added_at=row.added_at,
        error=row.error,
    )


@router.delete("/matches/{match_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_match(match_id: int) -> None:
    """Видалити матч з watchlist."""
    with UnitOfWork() as uow:
        deleted = WatchlistRepository(uow.conn).delete(match_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="not found")
