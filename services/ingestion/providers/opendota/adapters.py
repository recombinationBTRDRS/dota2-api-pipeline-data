# services/ingestion/providers/opendota/adapters.py
from typing import Any

# OpenDota anonymous account_id sentinel value (max uint32).
_ANONYMOUS_ACCOUNT_ID = 4_294_967_295

# Кількість основних item slots (не враховуючи backpack і neutral).
_ITEM_SLOTS = 6


def adapt_match(raw: dict[str, Any]) -> dict[str, Any]:
    """Нормалізує raw OpenDota match JSON → contract dict для parse_match()."""
    raw_players = raw.get("players")
    players_list: list[dict[str, Any]] = raw_players if isinstance(raw_players, list) else []

    return {
        "match_id": raw["match_id"],
        "duration": raw["duration"],
        "radiant_win": raw["radiant_win"],
        "start_time": raw["start_time"],
        "radiant_score": raw.get("radiant_score") or 0,
        "dire_score": raw.get("dire_score") or 0,
        "patch": raw.get("patch"),
        "region": raw.get("region"),
        "players": [adapt_player(p, idx) for idx, p in enumerate(players_list)],
        "picks_bans": raw.get("picks_bans", []),
    }


def adapt_player(player: dict[str, Any], slot_index: int) -> dict[str, Any]:
    """Нормалізує raw OpenDota player dict → contract player dict.

    Назви полів OpenDota API:
        gold_per_min  (не gpm)  — підтверджено документацією
        xp_per_min    (не xpm)  — підтверджено документацією
        lane_role               — тільки в парсених матчах, None якщо replay не парсений
        is_roaming              — тільки в парсених матчах

    Всі числові поля через .get() з fallback 0 —
    непарсені матчі можуть не мати gold_per_min/xp_per_min.

    account_id=4294967295 (anonymous sentinel) → None.
    """
    raw_account_id = player.get("account_id")
    account_id = (
        None
        if raw_account_id is None or raw_account_id == _ANONYMOUS_ACCOUNT_ID
        else int(raw_account_id)
    )

    return {
        "player_slot":  slot_index,
        "account_id":   account_id,
        "hero_id":      player["hero_id"],
        "kills":        int(player.get("kills")         or 0),
        "deaths":       int(player.get("deaths")        or 0),
        "assists":      int(player.get("assists")       or 0),
        "gpm":          int(player.get("gold_per_min")  or 0),  # API: gold_per_min
        "xpm":          int(player.get("xp_per_min")    or 0),  # API: xp_per_min
        "is_radiant":   player.get("isRadiant", False),
        "win":          (player.get("win") or 0) == 1,
        "lane_role":    player.get("lane_role"),                 # None якщо матч не парсений
        "is_roaming":   bool(player.get("is_roaming") or False),
        "items":        [int(player.get(f"item_{i}") or 0) for i in range(_ITEM_SLOTS)],
    }