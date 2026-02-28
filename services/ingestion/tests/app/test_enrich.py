# services/ingestion/tests/app/test_enrich.py
"""Unit-тести для enrich_match() з mock HeroRepository (Task 3.4)."""
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from services.ingestion.app.enrich import enrich_match
from services.ingestion.db.models import HeroDB
from services.ingestion.domains.matches.dtos import Match, PlayerMatchStats
from services.ingestion.domains.roles.dtos import Role

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_player(
    slot: int = 0,
    hero_id: int = 1,
    account_id: int | None = 123,
    is_radiant: bool = True,
    win: bool = True,
) -> PlayerMatchStats:
    return PlayerMatchStats(
        player_slot=slot,
        account_id=account_id,
        hero_id=hero_id,
        kills=5, deaths=2, assists=10,
        gpm=500, xpm=600,
        is_radiant=is_radiant,
        win=win,
    )


def _make_match(players: list[PlayerMatchStats]) -> Match:
    return Match(
        match_id=999,
        duration=2400,
        radiant_win=True,
        start_time=1_700_000_000,
        radiant_score=30,
        dire_score=20,
        players=players,
    )


def _make_hero_db(hero_id: int = 1) -> HeroDB:
    return HeroDB(
        id=hero_id,
        name="npc_dota_hero_antimage",
        localized_name="Anti-Mage",
        primary_attr="agi",
        attack_type="Melee",
    )


def _mock_repo(
    hero_id: int,
    hero_db: HeroDB | None,
    primary_pos: int | None,
) -> MagicMock:
    """Повертає mock HeroRepository.

    get_with_role(hero_id) → (hero_db, primary_pos) або None.
    primary_pos: int 1–5 або None (db-шар не повертає Role).
    """
    repo = MagicMock()
    if hero_db is None:
        repo.get_with_role.return_value = None
    else:
        repo.get_with_role.return_value = (hero_db, primary_pos)
    return repo


# ── tests ─────────────────────────────────────────────────────────────────────

def test_enrich_returns_hero_name_and_role() -> None:
    """Якщо герой знайдений в DB — hero_name і role заповнені коректно."""
    hero = _make_hero_db(hero_id=1)
    repo = _mock_repo(hero_id=1, hero_db=hero, primary_pos=1)  # primary_pos=1 → CARRY

    match = _make_match([_make_player(slot=0, hero_id=1)])
    results = enrich_match(match, repo)

    assert len(results) == 1
    enriched = results[0]
    assert enriched.hero_name == "Anti-Mage"
    assert enriched.role == Role.CARRY
    assert enriched.primary_attr == "agi"
    assert enriched.attack_type == "Melee"


def test_enrich_none_when_hero_not_in_db() -> None:
    """Якщо герой не в DB — graceful degradation: hero_name/role = None, не падає."""
    repo = _mock_repo(hero_id=99, hero_db=None, primary_pos=None)

    match = _make_match([_make_player(slot=0, hero_id=99)])
    results = enrich_match(match, repo)

    assert len(results) == 1
    enriched = results[0]
    assert enriched.hero_name is None
    assert enriched.role is None
    assert enriched.primary_attr is None
    assert enriched.attack_type is None


def test_enrich_preserves_player_stats() -> None:
    """Статистика гравця (kills, gpm тощо) передається без змін."""
    hero = _make_hero_db(hero_id=1)
    repo = _mock_repo(hero_id=1, hero_db=hero, primary_pos=2)  # primary_pos=2 → MID

    player = _make_player(slot=0, hero_id=1, account_id=42)
    match = _make_match([player])
    results = enrich_match(match, repo)

    enriched = results[0]
    assert enriched.match_id == 999
    assert enriched.player_slot == 0
    assert enriched.account_id == 42
    assert enriched.kills == 5
    assert enriched.deaths == 2
    assert enriched.assists == 10
    assert enriched.gpm == 500
    assert enriched.xpm == 600
    assert enriched.is_radiant is True
    assert enriched.win is True


def test_enrich_none_role_when_role_scores_missing() -> None:
    """Герой є в DB, але primary_pos=None → role = None (sync_role_scores не запущений)."""
    hero = _make_hero_db(hero_id=1)
    repo = _mock_repo(hero_id=1, hero_db=hero, primary_pos=None)

    match = _make_match([_make_player(slot=0, hero_id=1)])
    results = enrich_match(match, repo)

    enriched = results[0]
    assert enriched.hero_name == "Anti-Mage"  # герой знайдений
    assert enriched.role is None               # але роль невідома


def test_enrich_multiple_players_mixed() -> None:
    """3 гравці: частина знайдена в DB, частина — ні."""
    hero = _make_hero_db(hero_id=1)

    repo = MagicMock()

    def side_effect(hero_id: int) -> tuple | None:
        if hero_id == 1:
            return (hero, 1)  # primary_pos=1 → CARRY
        return None

    repo.get_with_role.side_effect = side_effect

    players = [
        _make_player(slot=0, hero_id=1),   # знайдений
        _make_player(slot=1, hero_id=99),  # не знайдений
        _make_player(slot=2, hero_id=1),   # знайдений
    ]
    match = _make_match(players)
    results = enrich_match(match, repo)

    assert len(results) == 3
    assert results[0].hero_name == "Anti-Mage"
    assert results[0].role == Role.CARRY
    assert results[1].hero_name is None
    assert results[1].role is None
    assert results[2].hero_name == "Anti-Mage"


def test_enriched_player_stats_is_frozen() -> None:
    """EnrichedPlayerStats є immutable (frozen pydantic model)."""
    hero = _make_hero_db()
    repo = _mock_repo(hero_id=1, hero_db=hero, primary_pos=3)  # OFFLANE

    match = _make_match([_make_player()])
    enriched = enrich_match(match, repo)[0]

    with pytest.raises(ValidationError):
        enriched.kills = 999  # type: ignore[misc]


def test_enrich_calls_repo_once_per_player() -> None:
    """get_with_role викликається рівно по одному разу на кожного гравця."""
    hero = _make_hero_db(hero_id=1)
    repo = _mock_repo(hero_id=1, hero_db=hero, primary_pos=1)

    players = [_make_player(slot=i, hero_id=1) for i in range(5)]
    match = _make_match(players)
    enrich_match(match, repo)

    assert repo.get_with_role.call_count == 5