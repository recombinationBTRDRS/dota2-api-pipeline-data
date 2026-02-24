#services/ingestion/db/models.py
from dataclasses import dataclass
from typing import List

@dataclass
class PlayerMatchStats:
    account_id: int
    hero_id: int
    kills: int
    deaths: int
    assists: int
    gpm: int
    xpm: int
    is_radiant: bool
    win: bool


@dataclass
class Match:
    id: int
    duration: int
    radiant_win: bool
    start_time: int
    radiant_score: int | None = None
    dire_score: int | None = None

@dataclass
class Player:
    account_id: int
    rank_tier: int | None
    mmr: float | None


@dataclass
class MatchPlayer:
    match_id: int
    player_id: int
    hero_id: int
    kills: int
    deaths: int
    assists: int
    gpm: int
    xpm: int
    win: bool