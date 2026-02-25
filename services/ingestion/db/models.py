# services/ingestion/db/models.py
from dataclasses import dataclass


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
    player_id: int
    hero_id: int
    kills: int
    deaths: int
    assists: int
    gpm: int
    xpm: int
    win: bool