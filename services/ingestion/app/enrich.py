# services/ingestion/app/enrich.py
"""Hero stats enrichment (Task 3.4).

enrich_match() збагачує статистику гравців матчу даними героя і ролі з DB.

Архітектурні рішення:
    - Role маппінг (primary_pos → Role) живе тут, не в db-шарі.
      db/repositories.py повертає primary_pos: int | None — чистий int без domain залежностей.
    - enrich_match() приймає HeroRepository як DI параметр — легко мокається в тестах.
    - Не пише в DB — тільки читає.
    - Graceful degradation: якщо герой не знайдений — логує warning, hero-поля = None.
"""
import logging

from services.ingestion.db.repositories import HeroRepository
from services.ingestion.domains.heroes.dtos import EnrichedPlayerStats
from services.ingestion.domains.matches.dtos import Match
from services.ingestion.domains.roles.dtos import Role

logger = logging.getLogger(__name__)


def _primary_pos_to_role(primary_pos: int | None) -> Role | None:
    """Конвертує primary_pos (int 1–5) → Role enum або None.

    Живе в app-шарі щоб db-шар не мав залежності від domains.
    """
    if primary_pos is None:
        return None
    try:
        return Role(primary_pos)
    except ValueError:
        logger.warning("Unknown primary_pos value: %d", primary_pos)
        return None


def enrich_match(
    match: Match,
    hero_repo: HeroRepository,
) -> list[EnrichedPlayerStats]:
    """Збагачує гравців матчу даними героя і ролі з DB.

    Для кожного гравця з match.players:
      1. Шукає героя через hero_repo.get_with_role(hero_id).
         get_with_role повертає (HeroDB, primary_pos: int | None) | None.
      2. Конвертує primary_pos → Role тут (app-шар).
      3. Якщо герой не знайдений — логує warning, всі hero-поля = None.

    Args:
        match: провалідований Match DTO.
        hero_repo: HeroRepository з активним DB-з'єднанням.

    Returns:
        Список EnrichedPlayerStats — по одному на кожного гравця.
    """
    results: list[EnrichedPlayerStats] = []

    for player in match.players:
        hero_result = hero_repo.get_with_role(player.hero_id)

        if hero_result is None:
            logger.warning(
                "enrich_match: hero_id=%d not found in DB (match_id=%d, slot=%d). "
                "Run sync_heroes() and sync_role_scores() first.",
                player.hero_id, match.match_id, player.player_slot,
            )
            hero_name = None
            primary_attr = None
            attack_type = None
            role = None
        else:
            hero_db, primary_pos = hero_result
            hero_name = hero_db.localized_name
            primary_attr = hero_db.primary_attr
            attack_type = hero_db.attack_type
            role = _primary_pos_to_role(primary_pos)

        results.append(EnrichedPlayerStats(
            match_id=match.match_id,
            player_slot=player.player_slot,
            account_id=player.account_id,
            hero_id=player.hero_id,
            kills=player.kills,
            deaths=player.deaths,
            assists=player.assists,
            gpm=player.gpm,
            xpm=player.xpm,
            is_radiant=player.is_radiant,
            win=player.win,
            hero_name=hero_name,
            primary_attr=primary_attr,
            attack_type=attack_type,
            role=role,
        ))

    return results