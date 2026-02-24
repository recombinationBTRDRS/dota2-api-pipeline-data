from dataclasses import dataclass
from typing import List


@dataclass
class PlayerDTO:
    account_id: int | None
    hero_id: int
    kills: int
    deaths: int
    assists: int
    items: list[int]


@dataclass
class MatchDTO:
    match_id: int
    duration: int
    radiant_win: bool
    start_time: int
    players: List[PlayerDTO]