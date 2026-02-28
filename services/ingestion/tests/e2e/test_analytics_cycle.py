# services/ingestion/tests/e2e/test_analytics_cycle.py
"""E2E тести Analytics Engine (Task 4.6).

Flow: sync_heroes → sync_role_scores → seed матчі → analytics queries → assert.
Аналог test_domain_model_cycle.py але для Epic 4.
"""
from typing import Any

import pytest

from services.ingestion.app.sync_heroes import sync_heroes
from services.ingestion.app.sync_role_scores import sync_role_scores
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.models import MatchPlayerItemDB
from services.ingestion.db.repositories import (
    HeroStatsRepository,
    ItemBuildRepository,
    MatchPlayerItemRepository,
    MatchTimelineRepository,
)
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork

# ── fake providers ────────────────────────────────────────────────────────────

class FakeHeroesClient:
    def get_heroes(self) -> list[dict[str, Any]]:
        return [
            {"id": 1, "name": "npc_dota_hero_antimage",
             "localized_name": "Anti-Mage", "primary_attr": "agi", "attack_type": "Melee"},
            {"id": 2, "name": "npc_dota_hero_axe",
             "localized_name": "Axe", "primary_attr": "str", "attack_type": "Melee"},
            {"id": 5, "name": "npc_dota_hero_crystal_maiden",
             "localized_name": "Crystal Maiden", "primary_attr": "int", "attack_type": "Ranged"},
        ]


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test_analytics.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


# ── seed helpers ──────────────────────────────────────────────────────────────

def _seed_match(conn, match_id: int, duration: int = 2400) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win) "
        "VALUES (?, 1700000000, ?, 1)",
        (match_id, duration),
    )


def _seed_mp(
    conn, match_id: int, slot: int, hero_id: int, win: bool,
    kills: int = 5, gpm: int = 500,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_players "
        "(match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win) "
        "VALUES (?, ?, ?, ?, 2, 8, ?, 600, ?)",
        (match_id, slot, hero_id, kills, gpm, int(win)),
    )


def _seed_item(conn, item_id: int, name: str, localized: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO items (id, name, localized_name, cost) VALUES (?, ?, ?, 0)",
        (item_id, name, localized),
    )


# ── E2E: Hero Stats (Task 4.1) ────────────────────────────────────────────────

def test_e2e_hero_stats_after_sync(db) -> None:
    """sync_heroes → seed матчі → get_hero_stats → коректний winrate."""
    sync_heroes(provider=FakeHeroesClient())

    with UnitOfWork() as uow:
        for i in range(1, 11):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=(i <= 6))  # AM: 6/10

    with UnitOfWork() as uow:
        stats = HeroStatsRepository(uow.conn).get_hero_stats(hero_id=1)

    assert stats is not None
    assert stats.hero_name == "Anti-Mage"
    assert stats.matches_played == 10
    assert stats.winrate == 0.6


def test_e2e_top_by_winrate(db) -> None:
    """Два герої → get_top_by_winrate → правильний порядок."""
    sync_heroes(provider=FakeHeroesClient())

    with UnitOfWork() as uow:
        # AM: 6/10 = 0.6
        for i in range(1, 11):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=(i <= 6))
        # Axe: 8/10 = 0.8
        for i in range(11, 21):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 1, hero_id=2, win=(i <= 18))

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_top_by_winrate(limit=2, min_matches=1)

    assert result[0].hero_id == 2   # Axe: 0.8
    assert result[1].hero_id == 1   # AM: 0.6


# ── E2E: Role Stats (Task 4.2) ────────────────────────────────────────────────

def test_e2e_role_leaderboard_after_sync(db) -> None:
    """sync_heroes + sync_role_scores → get_role_leaderboard → AM в carry leaderboard."""
    sync_heroes(provider=FakeHeroesClient())
    sync_role_scores()

    with UnitOfWork() as uow:
        for i in range(1, 6):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=True)  # AM carry

    with UnitOfWork() as uow:
        result = HeroStatsRepository(uow.conn).get_role_leaderboard(
            primary_pos=1, min_matches=1
        )

    hero_ids = [r.hero_id for r in result]
    assert 1 in hero_ids  # Anti-Mage (primary_pos=1) є в carry leaderboard


# ── E2E: Item Build (Task 4.3) ────────────────────────────────────────────────

def test_e2e_item_build_after_sync(db) -> None:
    """sync_heroes → seed матчі + items → get_hero_item_build → pickrate коректний."""
    sync_heroes(provider=FakeHeroesClient())

    with UnitOfWork() as uow:
        _seed_item(uow.conn, 1, "blink", "Blink Dagger")
        _seed_item(uow.conn, 2, "manta", "Manta Style")

        for i in range(1, 6):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=True)

        # blink у всіх 5, manta тільки в 3
        MatchPlayerItemRepository(uow.conn).upsert_batch([
            MatchPlayerItemDB(match_id=i, player_slot=0, slot=0, item_id=1)
            for i in range(1, 6)
        ])
        MatchPlayerItemRepository(uow.conn).upsert_batch([
            MatchPlayerItemDB(match_id=i, player_slot=0, slot=1, item_id=2)
            for i in range(1, 4)
        ])

    with UnitOfWork() as uow:
        result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1)

    assert result[0].item_id == 1           # blink перший
    assert result[0].item_name == "Blink Dagger"
    assert result[0].pickrate == 1.0        # 5/5
    assert result[1].pickrate == round(3 / 5, 4)


# ── E2E: Timeline (Task 4.4) ─────────────────────────────────────────────────

def test_e2e_hero_timeline(db) -> None:
    """Матчі різної тривалості → get_hero_phase_stats → 3 фази."""
    sync_heroes(provider=FakeHeroesClient())

    with UnitOfWork() as uow:
        _seed_match(uow.conn, 1, duration=1200)   # early
        _seed_match(uow.conn, 2, duration=2400)   # mid
        _seed_match(uow.conn, 3, duration=4000)   # late
        for i in range(1, 4):
            _seed_mp(uow.conn, i, 0, hero_id=1, win=(i % 2 == 0))

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_hero_phase_stats(hero_id=1)

    phases = [r.phase for r in result]
    assert phases == ["early", "mid", "late"]


def test_e2e_meta_snapshot(db) -> None:
    """sync_heroes + sync_role_scores → seed матчі → get_meta_snapshot → AM в meta."""
    sync_heroes(provider=FakeHeroesClient())
    sync_role_scores()

    with UnitOfWork() as uow:
        for i in range(1, 6):
            _seed_match(uow.conn, i)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=True)

    with UnitOfWork() as uow:
        result = MatchTimelineRepository(uow.conn).get_meta_snapshot()

    hero_ids = [r.hero_id for r in result]
    assert 1 in hero_ids  # Anti-Mage в snapshot


# ── E2E: Full cycle ───────────────────────────────────────────────────────────

def test_e2e_full_analytics_cycle(db) -> None:
    """Повний цикл: sync → матчі → всі 4 аналітики → всі дані коректні."""
    sync_heroes(provider=FakeHeroesClient())
    sync_role_scores()

    with UnitOfWork() as uow:
        _seed_item(uow.conn, 1, "blink", "Blink Dagger")

        # 10 матчів різної тривалості для AM
        for i in range(1, 11):
            duration = 1500 if i <= 3 else (2400 if i <= 7 else 4000)
            _seed_match(uow.conn, i, duration=duration)
            _seed_mp(uow.conn, i, 0, hero_id=1, win=(i <= 6), gpm=500 + i * 10)

        # blink у 8 з 10 матчів
        MatchPlayerItemRepository(uow.conn).upsert_batch([
            MatchPlayerItemDB(match_id=i, player_slot=0, slot=0, item_id=1)
            for i in range(1, 9)
        ])

    with UnitOfWork() as uow:
        repo = HeroStatsRepository(uow.conn)
        timeline = MatchTimelineRepository(uow.conn)

        stats = repo.get_hero_stats(hero_id=1)
        role_stats = repo.get_hero_stats_by_role(hero_id=1, primary_pos=1)
        items = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1)
        phases = timeline.get_hero_phase_stats(hero_id=1)
        meta = timeline.get_meta_snapshot()

    # 4.1
    assert stats is not None
    assert stats.matches_played == 10
    assert stats.winrate == 0.6

    # 4.2
    assert role_stats is not None
    assert role_stats.primary_pos == 1

    # 4.3
    assert len(items) >= 1
    assert items[0].item_id == 1
    assert items[0].times_bought == 8

    # 4.4
    assert len(phases) == 3
    assert any(r.phase == "early" for r in phases)

    # meta
    am_meta = next((r for r in meta if r.hero_id == 1), None)
    assert am_meta is not None
    assert am_meta.meta_score > 0