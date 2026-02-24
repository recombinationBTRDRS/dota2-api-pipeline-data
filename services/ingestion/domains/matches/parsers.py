# services/ingestion/domains/matches/parsers.py
from .dtos import Match, PlayerMatchStats


def parse_match(contract: dict) -> Match:
    players = [
        PlayerMatchStats(
            account_id=p["account_id"],
            hero_id=p["hero_id"],
            kills=p["kills"],
            deaths=p["deaths"],
            assists=p["assists"],
            gpm=p["gold_per_min"],
            xpm=p["xp_per_min"],
            is_radiant=p["is_radiant"],
            win=p["win"],
        )
        for p in contract["players"]
    ]

    return Match(
        id=contract["match_id"],
        duration=contract["duration"],
        radiant_win=contract["radiant_win"],
        start_time=contract["start_time"],
        radiant_score=contract["radiant_score"],
        dire_score=contract["dire_score"],
        players=players,
    )