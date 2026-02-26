# services/ingestion/db/models.py
from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class MatchDB:
    id: int
    start_time: int
    duration: int
    radiant_win: bool
    patch: int | None
    region: int | None


@dataclass(slots=True)
class PlayerDB:
    id: int | None
    account_id: int | None
    rank_tier: int | None
    mmr: float | None


@dataclass(slots=True)
class MatchPlayerDB:
    match_id: int
    player_id: int | None
    hero_id: int
    kills: int
    deaths: int
    assists: int
    gpm: int
    xpm: int
    win: bool
    player_slot: int


@dataclass(slots=True)
class IngestionLogDB:
    match_id: int
    status: Literal["ok", "failed"]
    ingested_at: int
    error: str | None


@dataclass(slots=True)
class HeroDB:
    """DB-представлення героя Dota 2 (Task 3.1)."""

    id: int
    name: str
    localized_name: str
    primary_attr: Literal["str", "agi", "int", "all"]
    attack_type: Literal["Melee", "Ranged"]


@dataclass(slots=True)
class ItemDB:
    """DB-представлення предмету Dota 2 (Task 3.2).

    id = OpenDota item id.
    cost: ціна в золоті (0 для рецептів і базових предметів).
    secret_shop / side_shop / recipe — булеві прапори.
    """

    id: int
    name: str           # internal key: 'blink'
    localized_name: str  # display name: 'Blink Dagger'
    cost: int
    secret_shop: bool
    side_shop: bool
    recipe: bool