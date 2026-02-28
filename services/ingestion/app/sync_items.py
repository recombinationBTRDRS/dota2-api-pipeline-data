# services/ingestion/app/sync_items.py
"""Item sync orchestration (Task 3.2)."""
import logging
from typing import Any

from services.ingestion.db.models import ItemDB
from services.ingestion.db.repositories import ItemRepository
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.items.dtos import Item
from services.ingestion.domains.items.parsers import parse_items
from services.ingestion.providers.opendota.items_client import (
    ItemsProvider,
    OpenDotaItemsClient,
)

logger = logging.getLogger(__name__)


def _to_db(item: Item) -> ItemDB:
    """Конвертує domain Item DTO → ItemDB для збереження."""
    return ItemDB(
        id=item.id,
        name=item.name,
        localized_name=item.localized_name,
        cost=item.cost,
        secret_shop=item.secret_shop,
        side_shop=item.side_shop,
        recipe=item.recipe,
    )


def sync_items(provider: ItemsProvider | None = None) -> int:
    """
    Synchronize items from OpenDota into the local database.

    The provider returns raw API payload (dict[str, Any]).
    Parsing and normalization into Item DTOs happens in the domain layer.

    The function is idempotent: repeated calls update existing rows
    instead of inserting duplicates.

    Fake providers used in tests may return a reduced schema —
    parsing is handled in the domain layer.

    Args:
        provider: Optional ItemsProvider for dependency injection (tests).
                  Defaults to OpenDotaItemsClient.

    Returns:
        Number of items upserted into the database.
    """
    client = provider or OpenDotaItemsClient()

    raw_items: dict[str, Any] = client.get_items()
    items = parse_items(raw_items)
    db_items = [_to_db(i) for i in items]  # ← FIX: map Item → ItemDB before upsert

    with UnitOfWork() as uow:
        repo = ItemRepository(uow.conn)
        repo.upsert_batch(db_items)
        return len(db_items)
