# services/ingestion/domains/matches/dtos.py
from pydantic import BaseModel, Field


class PlayerMatchStats(BaseModel):
    """Статистика гравця в матчі.

    player_slot — raw OpenDota значення:
        Radiant: 0-4 (або 0, 1, 2, 3, 4)
        Dire:    128-132
    Це критично для matchup rebuild: is_radiant = player_slot < 128.

    items: list[int] довжиною до 6 — item_id для кожного слоту.
           item_id=0 означає порожній слот.

    lane_role (BL1.2): реальна позиція в матчі (OpenDota):
        1 = Safe Lane, 2 = Mid, 3 = Off Lane, 4 = Support/Jungle
        None якщо OpenDota не повернув (матч не парсений).
    is_roaming (BL1.2): розрізняє pos4 (False) vs pos5/roaming (True).
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