# services/ingestion/tests/e2e/test_domain_model_cycle.py
"""E2E тест: повний цикл domain model — sync → store → enrich (Task 3.5).

Flow:
    sync_heroes(fake)  → heroes table
    sync_role_scores() → hero_role_scores table
    sync_items(fake)   → items table
    enrich_match()     → EnrichedPlayerStats з hero_name і role

Всі тести ізольовані: tmp SQLite через fixture, без реальних HTTP запитів.
"""
from typing import Any

import pytest

from services.ingestion.app.enrich import enrich_match
from services.ingestion.app.sync_heroes import sync_heroes
from services.ingestion.app.sync_items import sync_items
from services.ingestion.app.sync_role_scores import sync_role_scores
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.repositories import HeroRepository, ItemRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.matches.dtos import Match, PlayerMatchStats
from services.ingestion.domains.roles.dtos import Role


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def db(monkeypatch, tmp_path):
    """Ізольована tmp SQLite БД для кожного тесту."""
    db_path = tmp_path / "test_e2e.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


class FakeHeroesClient:
    """Повертає мінімальний набір героїв що є в HERO_META і OPENDOTA_HERO_IDS."""

    def get_heroes(self) -> list[dict[str, Any]]:
        return [
            {
                "id": 1,
                "name": "npc_dota_hero_antimage",
                "localized_name": "Anti-Mage",
                "primary_attr": "agi",
                "attack_type": "Melee",
            },
            {
                "id": 2,
                "name": "npc_dota_hero_axe",
                "localized_name": "Axe",
                "primary_attr": "str",
                "attack_type": "Melee",
            },
            {
                "id": 5,
                "name": "npc_dota_hero_crystal_maiden",
                "localized_name": "Crystal Maiden",
                "primary_attr": "int",
                "attack_type": "Ranged",
            },
        ]


class FakeItemsClient:
    def get_items(self) -> dict[str, Any]:
        return {
            "blink": {"id": 1, "dname": "Blink Dagger", "cost": 2250},
            "tango": {"id": 2, "dname": "Tango", "cost": 90},
        }


def _make_match(players: list[PlayerMatchStats]) -> Match:
    return Match(
        match_id=42,
        duration=2400,
        radiant_win=True,
        start_time=1_700_000_000,
        radiant_score=30,
        dire_score=20,
        players=players,
    )


def _player(slot: int, hero_id: int, win: bool = True) -> PlayerMatchStats:
    return PlayerMatchStats(
        player_slot=slot,
        account_id=slot + 100,
        hero_id=hero_id,
        kills=5, deaths=2, assists=8,
        gpm=450, xpm=520,
        is_radiant=slot < 5,
        win=win,
    )


# ── smoke ─────────────────────────────────────────────────────────────────────


def test_smoke_sync_and_enrich(db) -> None:
    """Smoke: sync_heroes → sync_role_scores → enrich_match → hero_name присутній."""
    sync_heroes(provider=FakeHeroesClient())
    sync_role_scores()

    match = _make_match([_player(slot=0, hero_id=1)])  # Anti-Mage id=1

    with UnitOfWork() as uow:
        results = enrich_match(match, HeroRepository(uow.conn))

    assert len(results) == 1
    assert results[0].hero_name == "Anti-Mage"
    assert results[0].role is not None


# ── hero sync + enrich ────────────────────────────────────────────────────────


def test_enrich_hero_name_after_sync(db) -> None:
    """sync_heroes() → enrich_match() повертає коректний localized_name."""
    sync_heroes(provider=FakeHeroesClient())

    match = _make_match([
        _player(slot=0, hero_id=1),   # Anti-Mage
        _player(slot=1, hero_id=2),   # Axe
        _player(slot=2, hero_id=5),   # Crystal Maiden
    ])

    with UnitOfWork() as uow:
        results = enrich_match(match, HeroRepository(uow.conn))

    names = {r.hero_id: r.hero_name for r in results}
    assert names[1] == "Anti-Mage"
    assert names[2] == "Axe"
    assert names[5] == "Crystal Maiden"


def test_enrich_graceful_when_hero_missing(db) -> None:
    """Якщо hero_id не в DB → hero_name=None, не падає."""
    sync_heroes(provider=FakeHeroesClient())

    match = _make_match([
        _player(slot=0, hero_id=1),    # є в DB
        _player(slot=1, hero_id=999),  # нема в DB
    ])

    with UnitOfWork() as uow:
        results = enrich_match(match, HeroRepository(uow.conn))

    assert results[0].hero_name == "Anti-Mage"
    assert results[1].hero_name is None
    assert results[1].role is None


# ── role sync ─────────────────────────────────────────────────────────────────


def test_role_after_sync_role_scores(db) -> None:
    """sync_heroes → sync_role_scores → enrich → role коректна."""
    sync_heroes(provider=FakeHeroesClient())
    saved = sync_role_scores()
    assert saved >= 2  # Anti-Mage і Axe мають бути збережені

    match = _make_match([
        _player(slot=0, hero_id=1),  # Anti-Mage → CARRY (primary_pos=1)
        _player(slot=1, hero_id=2),  # Axe → OFFLANE (primary_pos=3)
    ])

    with UnitOfWork() as uow:
        results = enrich_match(match, HeroRepository(uow.conn))

    by_hero = {r.hero_id: r for r in results}
    assert by_hero[1].role == Role.CARRY     # Anti-Mage primary_pos=1
    assert by_hero[2].role == Role.OFFLANE   # Axe primary_pos=3


def test_role_none_before_sync_role_scores(db) -> None:
    """Без sync_role_scores() — hero знайдений, але role=None."""
    sync_heroes(provider=FakeHeroesClient())
    # НЕ запускаємо sync_role_scores()

    match = _make_match([_player(slot=0, hero_id=1)])

    with UnitOfWork() as uow:
        results = enrich_match(match, HeroRepository(uow.conn))

    assert results[0].hero_name == "Anti-Mage"
    assert results[0].role is None


# ── item sync ─────────────────────────────────────────────────────────────────


def test_item_sync_and_get(db) -> None:
    """sync_items(FakeItemsClient) → DB → get(item_id) → коректні дані."""
    count = sync_items(provider=FakeItemsClient())
    assert count == 2

    with UnitOfWork() as uow:
        repo = ItemRepository(uow.conn)
        blink = repo.get(1)
        tango = repo.get(2)

    assert blink is not None
    assert blink.name == "blink"
    assert blink.localized_name == "Blink Dagger"
    assert blink.cost == 2250

    assert tango is not None
    assert tango.name == "tango"
    assert tango.cost == 90


def test_item_sync_idempotent(db) -> None:
    """Повторний sync_items() не дублює записи."""
    sync_items(provider=FakeItemsClient())
    sync_items(provider=FakeItemsClient())

    with UnitOfWork() as uow:
        all_items = ItemRepository(uow.conn).get_all()
    assert len(all_items) == 2


# ── full cycle ────────────────────────────────────────────────────────────────


def test_full_cycle_sync_enrich_assert(db) -> None:
    """Повний цикл: sync heroes + roles + items → enrich → всі поля заповнені."""
    sync_heroes(provider=FakeHeroesClient())
    sync_role_scores()
    sync_items(provider=FakeItemsClient())

    match = _make_match([
        _player(slot=0, hero_id=1, win=True),   # Anti-Mage, radiant
        _player(slot=1, hero_id=2, win=True),   # Axe, radiant
        _player(slot=5, hero_id=5, win=False),  # Crystal Maiden, dire
    ])

    with UnitOfWork() as uow:
        results = enrich_match(match, HeroRepository(uow.conn))

    assert len(results) == 3

    by_hero = {r.hero_id: r for r in results}

    # Anti-Mage
    am = by_hero[1]
    assert am.hero_name == "Anti-Mage"
    assert am.primary_attr == "agi"
    assert am.attack_type == "Melee"
    assert am.role == Role.CARRY
    assert am.win is True

    # Axe
    axe = by_hero[2]
    assert axe.hero_name == "Axe"
    assert axe.primary_attr == "str"
    assert axe.role == Role.OFFLANE

    # Crystal Maiden
    cm = by_hero[5]
    assert cm.hero_name == "Crystal Maiden"
    assert cm.primary_attr == "int"
    assert cm.attack_type == "Ranged"
    assert cm.role == Role.HARD_SUPPORT
    assert cm.win is False