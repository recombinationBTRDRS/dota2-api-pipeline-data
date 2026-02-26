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
    """DB-представлення героя Dota 2 (Task 3.1).

    id = OpenDota hero id.
    primary_attr: 'str' | 'agi' | 'int' | 'all'.
    attack_type: 'Melee' | 'Ranged'.
    """

    id: int
    name: str                                        # 'npc_dota_hero_antimage'
    localized_name: str                              # 'Anti-Mage'
    primary_attr: Literal["str", "agi", "int", "all"]
    attack_type: Literal["Melee", "Ranged"]
