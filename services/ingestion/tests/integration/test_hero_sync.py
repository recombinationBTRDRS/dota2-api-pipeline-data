# services/ingestion/tests/integration/test_hero_sync.py
"""Інтеграційні тести HeroRepository і sync_heroes з реальним SQLite."""
from typing import Any

import pytest

from services.ingestion.app.sync_heroes import sync_heroes
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.models import HeroDB
from services.ingestion.db.repositories import HeroRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


class FakeHeroesClient:
    """Stub — повертає фіксований список героїв без HTTP."""

    def get_heroes(self) -> list[dict[str, Any]]:
        return [
            {"id": 1, "name": "npc_dota_hero_antimage", "localized_name": "Anti-Mage"},
            {"id": 2, "name": "npc_dota_hero_axe", "localized_name": "Axe"},
        ]


# ── HeroRepository unit tests ─────────────────────────────────────────────────


def test_upsert_and_get(db) -> None:
    """upsert + get повертає збережений HeroDB."""
    hero = HeroDB(id=1, name="npc_dota_hero_antimage", localized_name="Anti-Mage",
                  primary_attr="agi", attack_type="Melee")
    with UnitOfWork() as uow:
        HeroRepository(uow.conn).upsert(hero)

    with UnitOfWork() as uow:
        result = HeroRepository(uow.conn).get(1)

    assert result is not None
    assert result.id == 1
    assert result.localized_name == "Anti-Mage"
    assert result.primary_attr == "agi"


def test_get_returns_none_for_unknown(db) -> None:
    """get() для невідомого hero_id → None."""
    with UnitOfWork() as uow:
        assert HeroRepository(uow.conn).get(9999) is None


def test_upsert_idempotent(db) -> None:
    """Повторний upsert не дублює запис, оновлює дані."""
    from dataclasses import asdict
    hero = HeroDB(id=1, name="npc_dota_hero_antimage", localized_name="Anti-Mage",
                  primary_attr="agi", attack_type="Melee")
    with UnitOfWork() as uow:
        repo = HeroRepository(uow.conn)
        repo.upsert(hero)
        repo.upsert(HeroDB(**{**asdict(hero), "localized_name": "AM"}))

    with UnitOfWork() as uow:
        result = HeroRepository(uow.conn).get(1)

    assert result is not None
    assert result.localized_name == "AM"


def test_get_all_returns_all_heroes(db) -> None:
    """get_all() повертає всіх збережених героїв."""
    heroes = [
        HeroDB(id=1, name="npc_dota_hero_antimage", localized_name="Anti-Mage",
               primary_attr="agi", attack_type="Melee"),
        HeroDB(id=2, name="npc_dota_hero_axe", localized_name="Axe",
               primary_attr="str", attack_type="Melee"),
    ]
    with UnitOfWork() as uow:
        HeroRepository(uow.conn).upsert_batch(heroes)

    with UnitOfWork() as uow:
        result = HeroRepository(uow.conn).get_all()

    assert len(result) == 2
    assert {h.id for h in result} == {1, 2}


# ── sync_heroes integration tests ─────────────────────────────────────────────


def test_sync_heroes_saves_all(db) -> None:
    """sync_heroes() зберігає всіх героїв від провайдера."""
    count = sync_heroes(provider=FakeHeroesClient())
    assert count == 2

    with UnitOfWork() as uow:
        heroes = HeroRepository(uow.conn).get_all()
    assert len(heroes) == 2


def test_sync_heroes_idempotent(db) -> None:
    """Повторний виклик sync_heroes() не дублює дані."""
    sync_heroes(provider=FakeHeroesClient())
    sync_heroes(provider=FakeHeroesClient())

    with UnitOfWork() as uow:
        heroes = HeroRepository(uow.conn).get_all()
    assert len(heroes) == 2


def test_sync_heroes_updates_existing(db) -> None:
    """sync_heroes() оновлює дані якщо герой вже існує."""
    sync_heroes(provider=FakeHeroesClient())

    # FIX: Protocol HeroesProvider.get_heroes() → list[dict[str, Any]]
    # parse_hero() всередині sync_heroes вміє обробляти неповні dict-и
    class UpdatedClient:
        def get_heroes(self) -> list[dict[str, Any]]:
            return [{"id": 1, "name": "npc_dota_hero_antimage",
                     "localized_name": "Anti-Mage (Updated)"}]

    sync_heroes(provider=UpdatedClient())

    with UnitOfWork() as uow:
        hero = HeroRepository(uow.conn).get(1)
    assert hero is not None
    assert hero.localized_name == "Anti-Mage (Updated)"