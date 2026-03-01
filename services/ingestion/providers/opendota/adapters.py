# services/ingestion/providers/opendota/adapters.py
from typing import Any

_ANONYMOUS_ACCOUNT_ID = 4_294_967_295
_ITEM_SLOTS = 6
_VALID_LANE_ROLES = frozenset({1, 2, 3, 4})


def adapt_match(raw: dict[str, Any]) -> dict[str, Any]:
    raw_players = raw.get("players")
    players_list: list[dict[str, Any]] = raw_players if isinstance(raw_players, list) else []

    return {
        "match_id":      raw["match_id"],
        "duration":      raw["duration"],
        "radiant_win":   raw["radiant_win"],
        "start_time":    raw["start_time"],
        "radiant_score": raw.get("radiant_score") or 0,
        "dire_score":    raw.get("dire_score") or 0,
        "patch":         raw.get("patch"),
        "region":        raw.get("region"),
        "players":       [adapt_player(p, idx) for idx, p in enumerate(players_list)],
        "picks_bans":    raw.get("picks_bans", []),
    }


def _parse_lane_role(raw_lane: Any) -> int | None:
    """Безпечно парсить lane_role → int 1-4 або None.

    Повертає None для: None, 0, нечислових рядків, будь-якого значення поза {1,2,3,4}.
    Не кидає виключень.
    """
    if raw_lane is None:
        return None
    try:
        parsed = int(raw_lane)
    except (ValueError, TypeError):
        return None
    return parsed if parsed in _VALID_LANE_ROLES else None


def adapt_player(player: dict[str, Any], slot_index: int) -> dict[str, Any]:
    """Нормалізує raw OpenDota player dict → contract player dict.

    Назви полів OpenDota API:
        gold_per_min  (не gpm)
        xp_per_min    (не xpm)
        lane_role     — тільки в парсених матчах; 0/None/нечислове → None
        is_roaming    — тільки в парсених матчах

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
        "kills":        int(player.get("kills")        or 0),
        "deaths":       int(player.get("deaths")       or 0),
        "assists":      int(player.get("assists")      or 0),
        "gpm":          int(player.get("gold_per_min") or 0),
        "xpm":          int(player.get("xp_per_min")   or 0),
        "is_radiant":   player.get("isRadiant", False),
        "win":          (player.get("win") or 0) == 1,
        "lane_role":    _parse_lane_role(player.get("lane_role")),
        "is_roaming":   bool(player.get("is_roaming") or False),
        "items":        [int(player.get(f"item_{i}") or 0) for i in range(_ITEM_SLOTS)],
    }