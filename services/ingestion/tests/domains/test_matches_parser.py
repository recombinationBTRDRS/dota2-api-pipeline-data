from services.ingestion.domains.matches.parsers import parse_match


def test_parse_match_contract():
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
                "gold_per_min": 600,
                "xp_per_min": 700,
                "is_radiant": True,
                "win": True,
            }
        ],
    }

    match = parse_match(contract)

    assert match.match_id == 123
    assert len(match.players) == 1
    assert match.players[0].hero_id == 46