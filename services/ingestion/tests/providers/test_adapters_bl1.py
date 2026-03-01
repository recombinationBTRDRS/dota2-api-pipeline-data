# services/ingestion/tests/providers/test_adapters_bl1.py
"""Тести нових полів adapter після BL1.1 і BL1.2."""
from services.ingestion.providers.opendota.adapters import adapt_match, adapt_player

# Значення захардкоджене в тесті — не імпортуємо приватну константу з модуля.
# OpenDota повертає max uint32 для анонімних гравців.
_ANON = 4_294_967_295


def _base_match(**kwargs) -> dict:
    base = {
        "match_id": 1,
        "duration": 2400,
        "radiant_win": True,
        "start_time": 1700000000,
        "radiant_score": 30,
        "dire_score": 20,
        "players": [],
    }
    base.update(kwargs)
    return base


def _base_player(**kwargs) -> dict:
    base = {
        "hero_id": 1,
        "kills": 5,
        "deaths": 2,
        "assists": 8,
        "gpm": 500,
        "xpm": 600,
        "isRadiant": True,
        "win": 1,
    }
    base.update(kwargs)
    return base


# ── adapt_match ───────────────────────────────────────────────────────────────

def test_adapt_match_patch_and_region_present() -> None:
    result = adapt_match(_base_match(patch=38, region=2))
    assert result["patch"] == 38
    assert result["region"] == 2


def test_adapt_match_patch_and_region_missing() -> None:
    result = adapt_match(_base_match())
    assert result["patch"] is None
    assert result["region"] is None


def test_adapt_match_radiant_score_none_becomes_zero() -> None:
    raw = _base_match()
    raw["radiant_score"] = None
    result = adapt_match(raw)
    assert result["radiant_score"] == 0


# ── account_id ────────────────────────────────────────────────────────────────

def test_adapt_player_anonymous_sentinel_becomes_none() -> None:
    result = adapt_player(_base_player(account_id=_ANON), slot_index=0)
    assert result["account_id"] is None


def test_adapt_player_none_account_id_stays_none() -> None:
    result = adapt_player(_base_player(account_id=None), slot_index=0)
    assert result["account_id"] is None


def test_adapt_player_real_account_id_preserved() -> None:
    result = adapt_player(_base_player(account_id=123456789), slot_index=0)
    assert result["account_id"] == 123456789


# ── lane_role і is_roaming ────────────────────────────────────────────────────

def test_adapt_player_lane_role_present() -> None:
    result = adapt_player(_base_player(lane_role=1), slot_index=0)
    assert result["lane_role"] == 1


def test_adapt_player_lane_role_missing_is_none() -> None:
    result = adapt_player(_base_player(), slot_index=0)
    assert result["lane_role"] is None


def test_adapt_player_is_roaming_true() -> None:
    result = adapt_player(_base_player(is_roaming=True), slot_index=0)
    assert result["is_roaming"] is True


def test_adapt_player_is_roaming_missing_is_false() -> None:
    result = adapt_player(_base_player(), slot_index=0)
    assert result["is_roaming"] is False


def test_adapt_player_is_roaming_none_is_false() -> None:
    result = adapt_player(_base_player(is_roaming=None), slot_index=0)
    assert result["is_roaming"] is False


def test_adapt_player_lane_role_all_values() -> None:
    for lane in range(1, 5):
        result = adapt_player(_base_player(lane_role=lane), slot_index=0)
        assert result["lane_role"] == lane


# ── items ─────────────────────────────────────────────────────────────────────

def test_adapt_player_items_extracted() -> None:
    player = _base_player(item_0=1, item_1=2, item_2=3, item_3=4, item_4=5, item_5=6)
    result = adapt_player(player, slot_index=0)
    assert result["items"] == [1, 2, 3, 4, 5, 6]


def test_adapt_player_missing_items_become_zero() -> None:
    result = adapt_player(_base_player(), slot_index=0)
    assert result["items"] == [0, 0, 0, 0, 0, 0]


def test_adapt_player_none_item_becomes_zero() -> None:
    player = _base_player(item_0=None, item_1=100)
    result = adapt_player(player, slot_index=0)
    assert result["items"][0] == 0
    assert result["items"][1] == 100