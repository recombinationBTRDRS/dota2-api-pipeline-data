# services/ingestion/tests/integration/test_item_sync.py
"""Інтеграційні тести ItemRepository і sync_items з реальним SQLite."""
import pytest

from services.ingestion.app.sync_items import sync_items
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.models import ItemDB
from services.ingestion.db.repositories import ItemRepository
from services.ingestion.db.sqlite import init_db
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.items.dtos import Item


@pytest.fixture()
def db(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


class FakeItemsClient:
    """Stub — повертає фіксований список предметів без HTTP."""

    def get_items(self) -> list[Item]:
        return [
            Item(id=1, name="blink", localized_name="Blink Dagger", cost=2250),
            Item(id=2, name="branches", localized_name="Iron Branch", cost=50),
            Item(id=36, name="eaglesong", localized_name="Eaglesong",
                 cost=3200, secret_shop=True),
        ]


# ── ItemRepository ────────────────────────────────────────────────────────────


def test_upsert_batch_and_get(db) -> None:
    """upsert_batch + get повертає збережений ItemDB."""
    items = [
        ItemDB(id=1, name="blink", localized_name="Blink Dagger",
               cost=2250, secret_shop=False, side_shop=False, recipe=False),
    ]
    with UnitOfWork() as uow:
        ItemRepository(uow.conn).upsert_batch(items)

    with UnitOfWork() as uow:
        result = ItemRepository(uow.conn).get(1)

    assert result is not None
    assert result.name == "blink"
    assert result.cost == 2250
    assert result.secret_shop is False


def test_get_returns_none_for_unknown(db) -> None:
    with UnitOfWork() as uow:
        assert ItemRepository(uow.conn).get(9999) is None


def test_upsert_batch_idempotent(db) -> None:
    """Повторний upsert_batch не дублює записи."""
    items = [ItemDB(id=1, name="blink", localized_name="Blink Dagger",
                    cost=2250, secret_shop=False, side_shop=False, recipe=False)]
    with UnitOfWork() as uow:
        repo = ItemRepository(uow.conn)
        repo.upsert_batch(items)
        repo.upsert_batch(items)

    with UnitOfWork() as uow:
        all_items = ItemRepository(uow.conn).get_all()
    assert len(all_items) == 1


def test_upsert_batch_updates_existing(db) -> None:
    """Повторний upsert з новою ціною — оновлює запис."""
    with UnitOfWork() as uow:
        ItemRepository(uow.conn).upsert_batch([
            ItemDB(id=1, name="blink", localized_name="Blink Dagger",
                   cost=2250, secret_shop=False, side_shop=False, recipe=False)
        ])

    with UnitOfWork() as uow:
        ItemRepository(uow.conn).upsert_batch([
            ItemDB(id=1, name="blink", localized_name="Blink Dagger",
                   cost=2000, secret_shop=False, side_shop=False, recipe=False)
        ])

    with UnitOfWork() as uow:
        result = ItemRepository(uow.conn).get(1)
    assert result is not None
    assert result.cost == 2000


def test_bool_flags_persisted_correctly(db) -> None:
    """secret_shop=True і recipe=True коректно зберігаються і читаються."""
    with UnitOfWork() as uow:
        ItemRepository(uow.conn).upsert_batch([
            ItemDB(id=99, name="eaglesong", localized_name="Eaglesong",
                   cost=3200, secret_shop=True, side_shop=False, recipe=False)
        ])

    with UnitOfWork() as uow:
        result = ItemRepository(uow.conn).get(99)
    assert result is not None
    assert result.secret_shop is True
    assert result.side_shop is False


# ── sync_items ────────────────────────────────────────────────────────────────


def test_sync_items_saves_all(db) -> None:
    count = sync_items(provider=FakeItemsClient())
    assert count == 3

    with UnitOfWork() as uow:
        all_items = ItemRepository(uow.conn).get_all()
    assert len(all_items) == 3


def test_sync_items_idempotent(db) -> None:
    sync_items(provider=FakeItemsClient())
    sync_items(provider=FakeItemsClient())

    with UnitOfWork() as uow:
        all_items = ItemRepository(uow.conn).get_all()
    assert len(all_items) == 3