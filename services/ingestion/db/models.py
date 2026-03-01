# services/ingestion/db/models.py
from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class MatchDB:
    id: int
    start_time: int
    duration: int
    radiant_win: bool
    patch: int | None    # BL1.1: тепер заповнюється з API
    region: int | None   # BL1.1: тепер заповнюється з API


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
    lane_role: int | None  # BL1.2: реальна позиція (1-4), None якщо API не повернув
    is_roaming: bool        # BL1.2: pos4 (False) vs pos5/roaming (True)


@dataclass(slots=True)
class MatchPlayerItemDB:
    """Один предмет гравця у матчі.

    slot: 0–5 (6 item slots у Dota 2).
    item_id > 0 — item_id=0 (порожній слот) не зберігається, фільтрується в persist.py.
    BL1.3: backpack (6-8) і item_neutral — майбутнє розширення.
    """
    match_id: int
    player_slot: int
    slot: int     # 0–5
    item_id: int  # > 0


@dataclass(slots=True)
class IngestionLogDB:
    match_id: int
    status: Literal["ok", "failed"]
    ingested_at: int
    error: str | None


@dataclass(slots=True)
class HeroDB:
    id: int
    name: str
    localized_name: str
    primary_attr: Literal["str", "agi", "int", "all"]
    attack_type: Literal["Melee", "Ranged"]


@dataclass(slots=True)
class ItemDB:
    id: int
    name: str
    localized_name: str
    cost: int
    secret_shop: bool
    side_shop: bool
    recipe: bool


@dataclass(slots=True)
class HeroRoleScoreDB:
    hero_id: int
    pos1: int
    pos2: int
    pos3: int
    pos4: int
    pos5: int
    flex_score: int
    primary_pos: int