from dataclasses import dataclass
from typing import List


@dataclass
class PlayerMatchStats:
    account_id: int | None
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
    match_id: int
    duration: int
    radiant_win: bool
    start_time: int
    radiant_score: int
    dire_score: int
    players: List[PlayerMatchStats]