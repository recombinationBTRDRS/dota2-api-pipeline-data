# services/ingestion/app/sync_items.py
"""Item sync orchestration (Task 3.2)."""
import logging

from services.ingestion.db.models import ItemDB
from services.ingestion.db.repositories import ItemRepository
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.items.dtos import Item
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
    """Синхронізує предмети з OpenDota API до локальної БД.

    Ідемпотентний — повторний виклик не дублює дані.

    Args:
        provider: провайдер для завантаження предметів.
                  Default: OpenDotaItemsClient (реальний HTTP).

    Returns:
        Кількість збережених/оновлених предметів.
    """
    client = provider or OpenDotaItemsClient()

    items = client.get_items()
    db_items = [_to_db(i) for i in items]

    with UnitOfWork() as uow:
        ItemRepository(uow.conn).upsert_batch(db_items)

    logger.info("sync_items: saved %d items", len(db_items))
    return len(db_items)