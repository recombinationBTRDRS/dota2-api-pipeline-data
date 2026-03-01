# services/ingestion/providers/opendota/adapters.py
from typing import Any


def adapt_match(raw: dict[str, Any]) -> dict[str, Any]:
    """Нормалізує raw OpenDota match JSON → contract dict для parse_match().

    Захищає від None у полі players — коерсить до пустого списку.
    """
    raw_players = raw.get("players")
    players_list: list[dict[str, Any]] = raw_players if isinstance(raw_players, list) else []

    return {
        "match_id": raw["match_id"],
        "duration": raw["duration"],
        "radiant_win": raw["radiant_win"],
        "start_time": raw["start_time"],
        "radiant_score": raw["radiant_score"],
        "dire_score": raw["dire_score"],
        "players": [adapt_player(p, idx) for idx, p in enumerate(players_list)],
        "picks_bans": raw.get("picks_bans", []),
    }


def adapt_player(player: dict[str, Any], slot_index: int) -> dict[str, Any]:
    """Нормалізує raw OpenDota player dict → contract player dict.

    player_slot нормалізується до 0–9:
    OpenDota повертає 0-4 для Radiant і 128-132 для Dire.
    slot_index (позиція у списку) вже 0–9 після enumerate.

    items: витягує item_0..item_5 → list[int] довжиною 6.
    Відсутні або None поля замінюються 0 (порожній слот).
    item_id=0 фільтрується при збереженні в persist.py.

    Args:
        player: raw гравець з OpenDota API.
        slot_index: індекс у списку players (0–9).
    """
    return {
        "player_slot": slot_index,
        "account_id": player.get("account_id"),
        "hero_id": player["hero_id"],
        "kills": player["kills"],
        "deaths": player["deaths"],
        "assists": player["assists"],
        "gpm": player["gpm"],
        "xpm": player["xpm"],
        "is_radiant": player["isRadiant"],
        "win": player["win"] == 1,
        "items": [int(player.get(f"item_{i}") or 0) for i in range(6)],
    }