# services/ingestion/tests/db/test_item_build_repository.py
"""Unit тести ItemBuildRepository і MatchPlayerItemRepository (Task 4.3).

Seed-дані вставляються напряму через SQL.
"""
import pytest

from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.models import MatchPlayerItemDB
from services.ingestion.db.repositories import ItemBuildRepository, MatchPlayerItemRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork

# ── fixture + seed helpers ────────────────────────────────────────────────────

@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def _seed_hero(conn, hero_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO heroes (id, name, localized_name, primary_attr, attack_type) "
        "VALUES (?, ?, ?, 'agi', 'Melee')",
        (hero_id, f"npc_dota_hero_{name}", name),
    )


def _seed_item(conn, item_id: int, name: str, localized: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO items (id, name, localized_name, cost) VALUES (?, ?, ?, 0)",
        (item_id, name, localized),
    )


def _seed_match(conn, match_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win) "
        "VALUES (?, 1700000000, 2400, 1)",
        (match_id,),
    )


def _seed_match_player(
    conn,
    match_id: int,
    slot: int,
    hero_id: int,
    win: bool,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_players "
        "(match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win) "
        "VALUES (?, ?, ?, 5, 2, 8, 500, 600, ?)",
        (match_id, slot, hero_id, int(win)),
    )


def _seed_items_for_player(
    conn,
    match_id: int,
    slot: int,
    item_ids: list[int],
) -> None:
    """Вставляє items для гравця напряму в match_player_items."""
    conn.executemany(
        "INSERT OR IGNORE INTO match_player_items (match_id, player_slot, slot, item_id) "
        "VALUES (?, ?, ?, ?)",
        [
            (match_id, slot, i, item_id)
            for i, item_id in enumerate(item_ids)
            if item_id > 0
        ],
    )


# ── MatchPlayerItemRepository ─────────────────────────────────────────────────

def test_upsert_batch_saves_items(db) -> None:
    """upsert_batch зберігає items в match_player_items."""
    with UnitOfWork() as uow:
        _seed_match(uow.conn, 1)
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True)

        items = [
            MatchPlayerItemDB(match_id=1, player_slot=0, slot=0, item_id=1),
            MatchPlayerItemDB(match_id=1, player_slot=0, slot=1, item_id=2),
        ]
        MatchPlayerItemRepository(uow.conn).upsert_batch(items)

    with UnitOfWork() as uow:
        count = uow.conn.execute(
            "SELECT COUNT(*) FROM match_player_items WHERE match_id=1 AND player_slot=0"
        ).fetchone()[0]
    assert count == 2


def test_upsert_batch_idempotent(db) -> None:
    """Повторний upsert_batch не дублює записи."""
    with UnitOfWork() as uow:
        _seed_match(uow.conn, 1)
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True)

        items = [MatchPlayerItemDB(match_id=1, player_slot=0, slot=0, item_id=5)]
        repo = MatchPlayerItemRepository(uow.conn)
        repo.upsert_batch(items)
        repo.upsert_batch(items)  # повторно

    with UnitOfWork() as uow:
        count = uow.conn.execute(
            "SELECT COUNT(*) FROM match_player_items"
        ).fetchone()[0]
    assert count == 1


# ── ItemBuildRepository ───────────────────────────────────────────────────────

def test_get_hero_item_build_empty_for_no_matches(db) -> None:
    """Герой без матчів → порожній список."""
    with UnitOfWork() as uow:
        result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=999)
    assert result == []


def test_get_hero_item_build_sorted_by_pickrate_desc(db) -> None:
    """Предмети відсортовані за pickrate DESC."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_item(uow.conn, 1, "blink", "Blink Dagger")
        _seed_item(uow.conn, 2, "manta", "Manta Style")

        # 4 матчі: blink у всіх 4, manta тільки в 2
        for match_id in range(1, 5):
            _seed_match(uow.conn, match_id)
            _seed_match_player(uow.conn, match_id, 0, hero_id=1, win=True)
            _seed_items_for_player(uow.conn, match_id, 0, [1])  # blink завжди

        for match_id in range(1, 3):
            _seed_items_for_player(uow.conn, match_id, 0, [0, 2])  # manta в 1,2

    with UnitOfWork() as uow:
        result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1)

    assert len(result) == 2
    assert result[0].item_id == 1   # blink: 4/4 = 1.0
    assert result[1].item_id == 2   # manta: 2/4 = 0.5
    assert result[0].pickrate > result[1].pickrate


def test_get_hero_item_build_pickrate_calculation(db) -> None:
    """pickrate = times_bought / total_matches, округлено 4 знаки."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_item(uow.conn, 1, "blink", "Blink Dagger")

        # 3 матчі, blink у 2 з них → 2/3
        for match_id in range(1, 4):
            _seed_match(uow.conn, match_id)
            _seed_match_player(uow.conn, match_id, 0, hero_id=1, win=True)

        _seed_items_for_player(uow.conn, 1, 0, [1])
        _seed_items_for_player(uow.conn, 2, 0, [1])

    with UnitOfWork() as uow:
        result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1)

    assert len(result) == 1
    assert result[0].times_bought == 2
    assert result[0].pickrate == round(2 / 3, 4)


def test_get_hero_item_build_win_only(db) -> None:
    """win_only=True рахує тільки виграні матчі."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_item(uow.conn, 1, "blink", "Blink Dagger")

        # 4 матчі: 2 win, 2 loss; blink у всіх 4
        for match_id in range(1, 5):
            _seed_match(uow.conn, match_id)
            win = match_id <= 2
            _seed_match_player(uow.conn, match_id, 0, hero_id=1, win=win)
            _seed_items_for_player(uow.conn, match_id, 0, [1])

    with UnitOfWork() as uow:
        all_result = ItemBuildRepository(uow.conn).get_hero_item_build(
            hero_id=1, win_only=False
        )
        win_result = ItemBuildRepository(uow.conn).get_hero_item_build(
            hero_id=1, win_only=True
        )

    # без фільтру: 4/4
    assert all_result[0].times_bought == 4
    assert all_result[0].pickrate == 1.0

    # з фільтром: 2 wins, blink у обох → 2/2
    assert win_result[0].times_bought == 2
    assert win_result[0].pickrate == 1.0


def test_get_hero_item_build_win_pickrate(db) -> None:
    """win_pickrate = win times_bought / total_wins."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_item(uow.conn, 1, "blink", "Blink Dagger")

        # 4 матчі: 2 wins, 2 losses; blink тільки в losses (match 3, 4)
        for match_id in range(1, 5):
            _seed_match(uow.conn, match_id)
            win = match_id <= 2
            _seed_match_player(uow.conn, match_id, 0, hero_id=1, win=win)

        _seed_items_for_player(uow.conn, 3, 0, [1])
        _seed_items_for_player(uow.conn, 4, 0, [1])

    with UnitOfWork() as uow:
        result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1)

    assert len(result) == 1
    assert result[0].times_bought == 2        # blink у 2 матчах (обидва loss)
    assert result[0].pickrate == round(2 / 4, 4)
    assert result[0].win_pickrate == 0.0      # 0 wins з blink / 2 total wins


def test_get_hero_item_build_item_name_from_join(db) -> None:
    """item_name береться з LEFT JOIN items.localized_name."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_item(uow.conn, 1, "blink", "Blink Dagger")
        _seed_match(uow.conn, 1)
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True)
        _seed_items_for_player(uow.conn, 1, 0, [1])

    with UnitOfWork() as uow:
        result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1)

    assert result[0].item_name == "Blink Dagger"


def test_get_hero_item_build_item_name_none_without_sync(db) -> None:
    """item_name = None якщо items таблиця порожня (sync_items не запускався)."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match(uow.conn, 1)
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True)
        _seed_items_for_player(uow.conn, 1, 0, [999])  # item без запису в items

    with UnitOfWork() as uow:
        result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1)

    assert len(result) == 1
    assert result[0].item_name is None  # LEFT JOIN → NULL


def test_get_hero_item_build_limit(db) -> None:
    """limit обрізає результат."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_match(uow.conn, 1)
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True)
        # 6 різних items
        _seed_items_for_player(uow.conn, 1, 0, [1, 2, 3, 4, 5, 6])

    with UnitOfWork() as uow:
        result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1, limit=3)

    assert len(result) == 3


def test_get_hero_item_build_multiple_heroes_isolated(db) -> None:
    """Items одного героя не потрапляють в результати іншого."""
    with UnitOfWork() as uow:
        _seed_hero(uow.conn, 1, "Anti-Mage")
        _seed_hero(uow.conn, 2, "Axe")
        _seed_item(uow.conn, 1, "blink", "Blink Dagger")
        _seed_item(uow.conn, 10, "blade_mail", "Blade Mail")

        _seed_match(uow.conn, 1)
        _seed_match_player(uow.conn, 1, 0, hero_id=1, win=True)   # AM slot 0
        _seed_match_player(uow.conn, 1, 1, hero_id=2, win=True)   # Axe slot 1

        _seed_items_for_player(uow.conn, 1, 0, [1])         # AM: blink
        _seed_items_for_player(uow.conn, 1, 1, [10])        # Axe: blade_mail

    with UnitOfWork() as uow:
        am_result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=1)
        axe_result = ItemBuildRepository(uow.conn).get_hero_item_build(hero_id=2)

    assert len(am_result) == 1
    assert am_result[0].item_id == 1    # тільки blink

    assert len(axe_result) == 1
    assert axe_result[0].item_id == 10  # тільки blade_mail