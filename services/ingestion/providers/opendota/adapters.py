# services/ingestion/providers/opendota/adapters.py
from typing import Any

# OpenDota anonymous account_id sentinel value (max uint32).
# Гравці без публічного профілю отримують це значення замість None.
_ANONYMOUS_ACCOUNT_ID = 4_294_967_295

# Кількість основних item slots (не враховуючи backpack і neutral).
# BL1.3: backpack (6-8) і item_neutral додадуться пізніше.
_ITEM_SLOTS = 6


def adapt_match(raw: dict[str, Any]) -> dict[str, Any]:
    """Нормалізує raw OpenDota match JSON → contract dict для parse_match().

    Нові поля (BL1.1):
        patch  — версія гри (int або None)
        region — регіон матчу (int або None)
    """
    raw_players = raw.get("players")
    players_list: list[dict[str, Any]] = raw_players if isinstance(raw_players, list) else []

    return {
        "match_id": raw["match_id"],
        "duration": raw["duration"],
        "radiant_win": raw["radiant_win"],
        "start_time": raw["start_time"],
        "radiant_score": raw.get("radiant_score") or 0,
        "dire_score": raw.get("dire_score") or 0,
        # BL1.1: patch і region тепер збираємо
        "patch": raw.get("patch"),
        "region": raw.get("region"),
        "players": [adapt_player(p, idx) for idx, p in enumerate(players_list)],
        "picks_bans": raw.get("picks_bans", []),
    }


def adapt_player(player: dict[str, Any], slot_index: int) -> dict[str, Any]:
    """Нормалізує raw OpenDota player dict → contract player dict.

    Зміни (BL1.1 / BL1.2):
        account_id: 4294967295 (anonymous sentinel) → None
        lane_role:  реальна позиція гравця в матчі (1-4 або None)
        is_roaming: чи був гравець роумером (bool, None → False)

    lane_role mapping (OpenDota):
        1 = Safe Lane (carry / pos1)
        2 = Mid       (pos2)
        3 = Off Lane  (pos3)
        4 = Jungle / Support (pos4 або pos5 — розрізняємо через is_roaming)

    lane_role=4 + is_roaming=False → soft support (pos4)
    lane_role=4 + is_roaming=True  → hard support / roaming (pos5)

    items: item_0..item_5 → list[int] довжиною 6.
    item_id=0 = порожній слот, фільтрується при збереженні в persist.py.
    """
    raw_account_id = player.get("account_id")
    account_id = (
        None
        if raw_account_id is None or raw_account_id == _ANONYMOUS_ACCOUNT_ID
        else int(raw_account_id)
    )

    return {
        "player_slot": slot_index,
        "account_id": account_id,
        "hero_id": player["hero_id"],
        "kills": player["kills"],
        "deaths": player["deaths"],
        "assists": player["assists"],
        "gpm": player["gpm"],
        "xpm": player["xpm"],
        "is_radiant": player["isRadiant"],
        "win": player["win"] == 1,
        # BL1.2: реальна позиція з матчу
        "lane_role": player.get("lane_role"),       # int 1-4 або None
        "is_roaming": bool(player.get("is_roaming") or False),
        "items": [int(player.get(f"item_{i}") or 0) for i in range(_ITEM_SLOTS)],
    }