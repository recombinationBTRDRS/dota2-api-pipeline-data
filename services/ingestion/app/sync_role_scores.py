# services/ingestion/app/sync_role_scores.py
"""Role scores sync orchestration (Task 3.3).

Join: HERO_META (universal, name→scores) + OPENDOTA_HERO_IDS (name→id)
→ upsert hero_role_scores в DB.

Пропускає героїв яких немає в таблиці heroes (FK constraint).
flex_score і primary_pos обчислюються тут — не беруться з вхідних даних.
"""
import logging

from services.ingestion.db.models import HeroRoleScoreDB
from services.ingestion.db.repositories import HeroRepository, HeroRoleScoreRepository
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.heroes.meta import HERO_META
from services.ingestion.providers.opendota.hero_id_map import OPENDOTA_HERO_IDS

logger = logging.getLogger(__name__)


def sync_role_scores() -> int:
    """Синхронізує бальні оцінки героїв з HERO_META до DB.

    Алгоритм:
    1. Зчитує існуючі hero_id з таблиці heroes (FK-safe).
    2. Для кожного імені з HERO_META шукає hero_id в OPENDOTA_HERO_IDS.
    3. Якщо hero_id є в heroes таблиці — зберігає HeroRoleScoreDB.
    4. Обчислює flex_score і primary_pos з pos1-5.

    Returns:
        Кількість збережених записів.
    """
    with UnitOfWork() as uow:
        existing_ids = {h.id for h in HeroRepository(uow.conn).get_all()}

        records: list[HeroRoleScoreDB] = []
        skipped_no_id: list[str] = []
        skipped_no_hero: list[str] = []

        for name, meta in HERO_META.items():
            hero_id = OPENDOTA_HERO_IDS.get(name)
            if hero_id is None:
                skipped_no_id.append(name)
                continue
            if hero_id not in existing_ids:
                skipped_no_hero.append(name)
                continue

            flex = meta.flex_score
            primary = meta.primary_pos

            records.append(HeroRoleScoreDB(
                hero_id=hero_id,
                pos1=meta.pos1, pos2=meta.pos2, pos3=meta.pos3,
                pos4=meta.pos4, pos5=meta.pos5,
                flex_score=flex,
                primary_pos=primary,
            ))

        if records:
            HeroRoleScoreRepository(uow.conn).upsert_batch(records)

    if skipped_no_id:
        logger.warning("sync_role_scores: no OpenDota ID for %d heroes: %s",
                       len(skipped_no_id), skipped_no_id)
    if skipped_no_hero:
        logger.warning("sync_role_scores: %d heroes not in heroes table (run sync_heroes first)",
                       len(skipped_no_hero))

    logger.info("sync_role_scores: saved %d records", len(records))
    return len(records)
