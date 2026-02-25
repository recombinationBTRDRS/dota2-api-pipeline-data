# services/ingestion/domains/matches/parsers.py

from services.ingestion.domains.matches.dtos import Match, PlayerMatchStats


def parse_match(contract: dict) -> Match:
    """
    Перетворює normalized contract dict -> Domain Match DTO.
    Fail-fast: відсутні ключі верхнього рівня викликають KeyError;
    некоректні поля гравців викликають ValidationError (Pydantic).
    """
    players = [PlayerMatchStats(**p) for p in contract["players"]]

    return Match(
        match_id=contract["match_id"],
        duration=contract["duration"],
        radiant_win=contract["radiant_win"],
        start_time=contract["start_time"],
        radiant_score=contract["radiant_score"],
        dire_score=contract["dire_score"],
        players=players,
    )
