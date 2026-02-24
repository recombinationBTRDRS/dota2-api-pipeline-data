import json
from services.shared.dto.match_dto import MatchDTO, PlayerDTO


def parse_match(raw_json: dict) -> MatchDTO:
    players = []

    for p in raw_json.get("players", []):
        items = [
            p.get("item_0"),
            p.get("item_1"),
            p.get("item_2"),
            p.get("item_3"),
            p.get("item_4"),
            p.get("item_5"),
        ]

        players.append(
            PlayerDTO(
                account_id=p.get("account_id"),
                hero_id=p["hero_id"],
                kills=p["kills"],
                deaths=p["deaths"],
                assists=p["assists"],
                items=items,
            )
        )

    return MatchDTO(
        match_id=raw_json["match_id"],
        duration=raw_json["duration"],
        radiant_win=raw_json["radiant_win"],
        start_time=raw_json["start_time"],
        players=players,
    )