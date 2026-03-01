# services/ingestion/domains/matches/dtos.py
from pydantic import BaseModel, Field


class PlayerMatchStats(BaseModel):
    """Статистика гравця в матчі.

    player_slot (0–9) — унікальний слот у матчі, PK в match_players.
    items: list[int] довжиною до 6 — item_id для кожного слоту.
           item_id=0 означає порожній слот.
           Default [] — зворотна сумісність з тестами що не передають items.
    """

    player_slot: int = Field(..., ge=0, le=9)
    account_id: int | None = None
    hero_id: int
    kills: int
    deaths: int
    assists: int
    gpm: int
    xpm: int
    is_radiant: bool
    win: bool
    items: list[int] = Field(default_factory=list)


class Match(BaseModel):
    """Domain DTO матчу після валідації."""

    match_id: int = Field(..., alias="match_id")
    duration: int
    radiant_win: bool
    start_time: int
    radiant_score: int
    dire_score: int
    players: list[PlayerMatchStats]

    model_config = {"populate_by_name": True}

    @property
    def id(self) -> int:
        return self.match_id