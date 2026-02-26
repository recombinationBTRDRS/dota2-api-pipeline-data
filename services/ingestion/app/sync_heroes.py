# services/ingestion/app/sync_heroes.py
"""Hero sync orchestration (Task 3.1).

Використання:
    from services.ingestion.app.sync_heroes import sync_heroes
    sync_heroes()  # uses real OpenDota API

    # або з fake provider для тестів:
    sync_heroes(provider=FakeHeroesClient())
"""
import logging

from services.ingestion.db.models import HeroDB
from services.ingestion.db.repositories import HeroRepository
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.heroes.dtos import Hero
from services.ingestion.providers.opendota.heroes_client import (
    HeroesProvider,
    OpenDotaHeroesClient,
)

logger = logging.getLogger(__name__)


def _to_db(hero: Hero) -> HeroDB:
    """Конвертує domain Hero DTO → HeroDB для збереження."""
    return HeroDB(
        id=hero.id,
        name=hero.name,
        localized_name=hero.localized_name,
        primary_attr=hero.primary_attr,
        attack_type=hero.attack_type,
    )


def sync_heroes(provider: HeroesProvider | None = None) -> int:
    """Синхронізує героїв з OpenDota API до локальної БД.

    Ідемпотентний — повторний виклик не дублює дані.
    Використовує batch upsert для ефективності.

    Args:
        provider: провайдер для завантаження героїв.
                  Default: OpenDotaHeroesClient (реальний HTTP).

    Returns:
        Кількість збережених/оновлених героїв.

    Raises:
        RuntimeError: якщо API недоступний.
        ValidationError: якщо відповідь не відповідає схемі.
    """
    client = provider or OpenDotaHeroesClient()

    heroes = client.get_heroes()
    db_heroes = [_to_db(h) for h in heroes]

    with UnitOfWork() as uow:
        HeroRepository(uow.conn).upsert_batch(db_heroes)

    logger.info("sync_heroes: saved %d heroes", len(db_heroes))
    return len(db_heroes)