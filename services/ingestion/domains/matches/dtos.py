# services/ingestion/domains/matches/dtos.py

from pydantic import BaseModel, Field


class PlayerMatchStats(BaseModel):
    account_id: int | None = None
    hero_id: int = Field(..., ge=1)
    kills: int = Field(..., ge=0)
    deaths: int = Field(..., ge=0)
    assists: int = Field(..., ge=0)
    gpm: int = Field(..., ge=0)
    xpm: int = Field(..., ge=0)
    is_radiant: bool
    win: bool


class Match(BaseModel):
    id: int = Field(..., alias="match_id", ge=1)
    duration: int = Field(..., ge=0)
    radiant_win: bool
    start_time: int = Field(..., ge=0)
    radiant_score: int = Field(..., ge=0)
    dire_score: int = Field(..., ge=0)
    players: list[PlayerMatchStats]

    model_config = {
        "populate_by_name": True
    }