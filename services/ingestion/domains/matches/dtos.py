# services/ingestion/domains/matches/dtos.py
from pydantic import BaseModel, Field


class PlayerMatchStats(BaseModel):
    """Статистика гравця в матчі.

    player_slot — raw OpenDota значення:
        Radiant: 0-4, Dire: 128-132
    is_radiant = player_slot < 128 (критично для matchup rebuild).

    lane_role: реальна позиція (1-4), None якщо матч не парсений OpenDota.
    is_roaming: розрізняє pos4 (False) vs pos5/roaming (True).

    Task 7.6 — performance поля (None якщо API не повернув):
        net_worth, hero_damage, tower_damage, hero_healing, last_hits
    """

    player_slot: int = Field(..., ge=0, le=132)
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
    lane_role: int | None = Field(default=None, ge=1, le=4)
    is_roaming: bool = False
    # Task 7.6
    net_worth: int | None = None
    hero_damage: int | None = None
    tower_damage: int | None = None
    hero_healing: int | None = None
    last_hits: int | None = None


class Match(BaseModel):
    """Domain DTO матчу після валідації."""

    match_id: int = Field(..., alias="match_id")
    duration: int
    radiant_win: bool
    start_time: int
    radiant_score: int
    dire_score: int
    patch: int | None = None
    region: int | None = None
    players: list[PlayerMatchStats]

    model_config = {"populate_by_name": True}

    @property
    def id(self) -> int:
        return self.match_id