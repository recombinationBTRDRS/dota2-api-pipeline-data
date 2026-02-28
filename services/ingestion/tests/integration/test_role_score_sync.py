# services/ingestion/tests/integration/test_role_score_sync.py
"""Інтеграційні тести HeroRoleScoreRepository і sync_role_scores."""
import pytest

from services.ingestion.app.sync_role_scores import sync_role_scores
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.models import HeroDB, HeroRoleScoreDB
from services.ingestion.db.repositories import HeroRepository, HeroRoleScoreRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


@pytest.fixture()
def db_with_heroes(db):
    """DB з кількома верифікованими героями."""
    heroes = [
        HeroDB(id=1,   name="npc_dota_hero_antimage",   localized_name="Anti-Mage",
               primary_attr="agi", attack_type="Melee"),
        HeroDB(id=5,   name="npc_dota_hero_crystal_maiden", localized_name="Crystal Maiden",
               primary_attr="int", attack_type="Ranged"),
        HeroDB(id=21,  name="npc_dota_hero_windrunner",  localized_name="Windranger",
               primary_attr="agi", attack_type="Ranged"),
        HeroDB(id=53,  name="npc_dota_hero_furion",      localized_name="Nature's Prophet",
               primary_attr="int", attack_type="Ranged"),
        HeroDB(id=155, name="npc_dota_hero_largo",       localized_name="Largo",
               primary_attr="str", attack_type="Melee"),
    ]
    with UnitOfWork() as uow:
        HeroRepository(uow.conn).upsert_batch(heroes)
    return db


# ── HeroRoleScoreRepository ───────────────────────────────────────────────────

def test_upsert_and_get(db_with_heroes) -> None:
    """upsert_batch + get повертає коректний HeroRoleScoreDB."""
    score = HeroRoleScoreDB(
        hero_id=1, pos1=4, pos2=3, pos3=3, pos4=1, pos5=1,
        flex_score=3, primary_pos=1,
    )
    with UnitOfWork() as uow:
        HeroRoleScoreRepository(uow.conn).upsert_batch([score])

    with UnitOfWork() as uow:
        result = HeroRoleScoreRepository(uow.conn).get(1)

    assert result is not None
    assert result.pos1 == 4
    assert result.flex_score == 3
    assert result.primary_pos == 1


def test_get_returns_none_for_unknown(db_with_heroes) -> None:
    with UnitOfWork() as uow:
        assert HeroRoleScoreRepository(uow.conn).get(9999) is None


def test_upsert_idempotent(db_with_heroes) -> None:
    score = HeroRoleScoreDB(
        hero_id=1, pos1=4, pos2=3, pos3=3, pos4=1, pos5=1,
        flex_score=3, primary_pos=1,
    )
    with UnitOfWork() as uow:
        repo = HeroRoleScoreRepository(uow.conn)
        repo.upsert_batch([score])
        repo.upsert_batch([score])

    with UnitOfWork() as uow:
        rows = uow.conn.execute("SELECT COUNT(*) FROM hero_role_scores").fetchone()[0]
    assert rows == 1


def test_get_by_pos(db_with_heroes) -> None:
    """get_by_pos(1, min_score=4) → тільки carry герої."""
    scores = [
        HeroRoleScoreDB(hero_id=1,  pos1=4, pos2=3, pos3=3, pos4=1, pos5=1,
                        flex_score=3, primary_pos=1),
        HeroRoleScoreDB(hero_id=5,  pos1=1, pos2=1, pos3=3, pos4=4, pos5=5,
                        flex_score=3, primary_pos=5),
        HeroRoleScoreDB(hero_id=21, pos1=5, pos2=4, pos3=4, pos4=4, pos5=4,
                        flex_score=5, primary_pos=1),
    ]
    with UnitOfWork() as uow:
        HeroRoleScoreRepository(uow.conn).upsert_batch(scores)

    with UnitOfWork() as uow:
        carries = HeroRoleScoreRepository(uow.conn).get_by_pos(1, min_score=4)

    hero_ids = {s.hero_id for s in carries}
    assert 1 in hero_ids   # Anti-Mage pos1=4
    assert 21 in hero_ids  # Windranger pos1=5
    assert 5 not in hero_ids  # CM pos1=1


def test_get_flex_heroes(db_with_heroes) -> None:
    """get_flex_heroes(min_flex=5) → тільки повністю flex герої."""
    scores = [
        HeroRoleScoreDB(hero_id=21, pos1=5, pos2=4, pos3=4, pos4=4, pos5=4,
                        flex_score=5, primary_pos=1),
        HeroRoleScoreDB(hero_id=53, pos1=4, pos2=4, pos3=4, pos4=4, pos5=4,
                        flex_score=5, primary_pos=1),
        HeroRoleScoreDB(hero_id=1,  pos1=4, pos2=3, pos3=3, pos4=1, pos5=1,
                        flex_score=3, primary_pos=1),
    ]
    with UnitOfWork() as uow:
        HeroRoleScoreRepository(uow.conn).upsert_batch(scores)

    with UnitOfWork() as uow:
        flex_heroes = HeroRoleScoreRepository(uow.conn).get_flex_heroes(min_flex=5)

    hero_ids = {s.hero_id for s in flex_heroes}
    assert 21 in hero_ids
    assert 53 in hero_ids
    assert 1 not in hero_ids  # flex=3


# ── sync_role_scores ──────────────────────────────────────────────────────────

def test_sync_saves_heroes_in_db(db_with_heroes) -> None:
    """sync_role_scores() зберігає тільки героїв що є в heroes таблиці."""
    count = sync_role_scores()
    assert count == 5  # тільки 5 героїв є в db_with_heroes

    with UnitOfWork() as uow:
        am = HeroRoleScoreRepository(uow.conn).get(1)  # Anti-Mage
    assert am is not None
    assert am.pos1 == 4
    assert am.flex_score == 3
    assert am.primary_pos == 1


def test_sync_computes_flex_correctly(db_with_heroes) -> None:
    """sync_role_scores() правильно обчислює flex_score."""
    sync_role_scores()

    with UnitOfWork() as uow:
        windranger = HeroRoleScoreRepository(uow.conn).get(21)
        np = HeroRoleScoreRepository(uow.conn).get(53)
        largo = HeroRoleScoreRepository(uow.conn).get(155)

    assert windranger is not None
    assert windranger.flex_score == 5  # 5,4,4,4,4 — всі >= 3

    assert np is not None
    assert np.flex_score == 5  # 4,4,4,4,4

    assert largo is not None
    assert largo.flex_score == 3  # 2,2,4,4,4


def test_sync_idempotent(db_with_heroes) -> None:
    """Повторний sync_role_scores() не дублює записи."""
    sync_role_scores()
    sync_role_scores()

    with UnitOfWork() as uow:
        rows = uow.conn.execute("SELECT COUNT(*) FROM hero_role_scores").fetchone()[0]
    assert rows == 5


def test_sync_skips_heroes_not_in_db(db) -> None:
    """sync_role_scores() без героїв в DB → 0 записів, не падає."""
    count = sync_role_scores()
    assert count == 0