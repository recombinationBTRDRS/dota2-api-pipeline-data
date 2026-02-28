# services/ingestion/app/sync_heroes.py
"""Hero sync orchestration (Task 3.1).

Використання:
    from services.ingestion.app.sync_heroes import sync_heroes
    sync_heroes()  # uses real OpenDota API

    # або з fake provider для тестів:
    sync_heroes(provider=FakeHeroesClient())
"""
import logging
from typing import Any

from services.ingestion.db.models import HeroDB
from services.ingestion.db.repositories import HeroRepository
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.heroes.dtos import Hero
from services.ingestion.domains.heroes.parsers import parse_heroes
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
    """
    Synchronize heroes from OpenDota into the local database.

    The provider returns raw API payload (list[dict[str, Any]]).
    Parsing and normalization into Hero DTOs happens in the domain layer.

    The function is idempotent: repeated calls update existing rows
    instead of inserting duplicates.

    Fake providers used in tests may return partial hero payloads
    (without primary_attr / attack_type) — these are normalized in the parser.

    Args:
        provider: Optional HeroesProvider for dependency injection (tests).
                  Defaults to OpenDotaHeroesClient.

    Returns:
        Number of heroes upserted into the database.
    """
    client = provider or OpenDotaHeroesClient()

    raw_heroes: list[dict[str, Any]] = client.get_heroes()
    heroes = parse_heroes(raw_heroes)
    db_heroes = [_to_db(h) for h in heroes]  # ← FIX: map Hero → HeroDB before upsert

    with UnitOfWork() as uow:
        repo = HeroRepository(uow.conn)
        repo.upsert_batch(db_heroes)
        return len(db_heroes)