#services/ingestion/tests/domains/test_matches_parser.py
import pytest
from pydantic import ValidationError

from services.ingestion.domains.matches.parsers import parse_match


def test_parse_match_valid_contract():
    contract = {
        "match_id": 123,
        "duration": 2000,
        "radiant_win": True,
        "start_time": 111,
        "radiant_score": 30,
        "dire_score": 20,
        "players": [
            {
                "account_id": 1,
                "hero_id": 46,
                "kills": 10,
                "deaths": 2,
                "assists": 8,
                "gpm": 600,
                "xpm": 700,
                "is_radiant": True,
                "win": True,
            }
        ],
    }

    match = parse_match(contract)

    assert match.id == 123
    assert len(match.players) == 1
    assert match.players[0].hero_id == 46


def test_parse_match_invalid_contract_missing_field():
    bad_contract = {
        "match_id": 123,
        "duration": 2000,
        "radiant_win": True,
        "start_time": 111,
        "radiant_score": 30,
        "dire_score": 20,
        "players": [
            {
                "account_id": 1,
                # hero_id missing
                "kills": 10,
                "deaths": 2,
                "assists": 8,
                "gpm": 600,
                "xpm": 700,
                "is_radiant": True,
                "win": True,
            }
        ],
    }

    with pytest.raises(ValidationError):
        parse_match(bad_contract)