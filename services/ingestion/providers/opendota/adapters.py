# services/ingestion/providers/opendota/adapters.py
from typing import Any

_ANONYMOUS_ACCOUNT_ID = 4_294_967_295
_ITEM_SLOTS = 6
_VALID_LANE_ROLES = frozenset({1, 2, 3, 4})
_DIRE_SLOT_OFFSET = 128


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
        "players":       [adapt_player(p) for p in players_list],
        "picks_bans":    raw.get("picks_bans", []),
    }


def _parse_lane_role(raw_lane: Any) -> int | None:
    if raw_lane is None:
        return None
    try:
        parsed = int(raw_lane)
    except (ValueError, TypeError):
        return None
    return parsed if parsed in _VALID_LANE_ROLES else None


def _parse_int_or_none(value: Any) -> int | None:
    """Парсить int або повертає None для відсутніх/нульових значень."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def adapt_player(player: dict[str, Any]) -> dict[str, Any]:
    """Нормалізує raw OpenDota player dict → contract player dict.

    player_slot береться з API як є (0-4 radiant, 128-132 dire).
    Критично для matchup rebuild: is_radiant = player_slot < 128.
    """
    raw_account_id = player.get("account_id")
    account_id = (
        None
        if raw_account_id is None or raw_account_id == _ANONYMOUS_ACCOUNT_ID
        else int(raw_account_id)
    )

    raw_slot = player.get("player_slot")
    if raw_slot is not None:
        player_slot = int(raw_slot)
    else:
        is_radiant_fallback = bool(player.get("isRadiant", True))
        player_slot = 0 if is_radiant_fallback else _DIRE_SLOT_OFFSET

    return {
        "player_slot":   player_slot,
        "account_id":    account_id,
        "hero_id":       player["hero_id"],
        "kills":         int(player.get("kills")        or 0),
        "deaths":        int(player.get("deaths")       or 0),
        "assists":       int(player.get("assists")      or 0),
        "gpm":           int(player.get("gold_per_min") or 0),
        "xpm":           int(player.get("xp_per_min")   or 0),
        "is_radiant":    player_slot < _DIRE_SLOT_OFFSET,
        "win":           (player.get("win") or 0) == 1,
        "lane_role":     _parse_lane_role(player.get("lane_role")),
        "is_roaming":    bool(player.get("is_roaming") or False),
        "items":         [int(player.get(f"item_{i}") or 0) for i in range(_ITEM_SLOTS)],
        # Task 7.6 — performance поля
        "net_worth":     _parse_int_or_none(player.get("net_worth")),
        "hero_damage":   _parse_int_or_none(player.get("hero_damage")),
        "tower_damage":  _parse_int_or_none(player.get("tower_damage")),
        "hero_healing":  _parse_int_or_none(player.get("hero_healing")),
        "last_hits":     _parse_int_or_none(player.get("last_hits")),
    }