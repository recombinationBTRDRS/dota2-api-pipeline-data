#services/ingestion/providers/opendota/adapters.py
from typing import Any


def adapt_match(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "match_id": raw["match_id"],
        "duration": raw["duration"],
        "radiant_win": raw["radiant_win"],
        "start_time": raw["start_time"],
        "radiant_score": raw["radiant_score"],
        "dire_score": raw["dire_score"],
        "players": [adapt_player(p) for p in raw.get("players", [])],
        "picks_bans": raw.get("picks_bans", []),
    }


def adapt_player(player: dict[str, Any]) -> dict[str, Any]:
    return {
        "account_id": player.get("account_id"),
        "hero_id": player["hero_id"],
        "kills": player["kills"],
        "deaths": player["deaths"],
        "assists": player["assists"],
        "gpm": player["gpm"],
        "xpm": player["xpm"],
        "is_radiant": player["isRadiant"],
        "win": player["win"] == 1,
    }