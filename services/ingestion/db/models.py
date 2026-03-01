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
class MatchPlayerItemDB:
    """Один предмет гравця у матчі (Task 4.3).

    slot: 0–5 (6 item slots у Dota 2).
    item_id > 0 — item_id=0 (порожній слот) не зберігається, фільтрується в persist.py.
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
    """DB-представлення героя Dota 2 (Task 3.1)."""

    id: int
    name: str
    localized_name: str
    primary_attr: Literal["str", "agi", "int", "all"]
    attack_type: Literal["Melee", "Ranged"]


@dataclass(slots=True)
class ItemDB:
    """DB-представлення предмету Dota 2 (Task 3.2)."""

    id: int
    name: str
    localized_name: str
    cost: int
    secret_shop: bool
    side_shop: bool
    recipe: bool


@dataclass(slots=True)
class HeroRoleScoreDB:
    """DB-представлення бальної оцінки героя по позиціях (Task 3.3)."""

    hero_id: int
    pos1: int
    pos2: int
    pos3: int
    pos4: int
    pos5: int
    flex_score: int
    primary_pos: int