# services/ingestion/domains/matches/dtos.py
from pydantic import BaseModel, Field


class PlayerMatchStats(BaseModel):
    """Статистика гравця в матчі.

    player_slot (0–9) — унікальний слот у матчі, PK в match_players.
    Адаптер adapt_player завжди проставляє його через enumerate.
    Якщо контракт приходить без player_slot (тести без адаптера) — default=-1.
    account_id може бути None для анонімних гравців.
    """

    player_slot: int = Field(default=-1, ge=-1, le=9)
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
    """Доменна модель матчу після парсингу та валідації."""

    id: int = Field(..., alias="match_id", ge=1)
    duration: int = Field(..., ge=0)
    radiant_win: bool
    start_time: int = Field(..., ge=0)
    radiant_score: int = Field(..., ge=0)
    dire_score: int = Field(..., ge=0)
    players: list[PlayerMatchStats]

    model_config = {"populate_by_name": True}