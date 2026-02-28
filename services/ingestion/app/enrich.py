# services/ingestion/app/enrich.py
"""Hero stats enrichment (Task 3.4).

enrich_match() збагачує статистику гравців матчу даними героя і ролі з DB.

Передумова:
    sync_heroes() і sync_role_scores() мають бути запущені перед викликом,
    інакше герої не будуть знайдені і поля hero_name/role будуть None.

Архітектурні рішення:
    - enrich_match() приймає HeroRepository як DI параметр — легко мокається в тестах.
    - Не пише в DB — тільки читає.
    - Graceful degradation: якщо герой не знайдений — логує warning і повертає None-поля,
      не падає і не пропускає гравця.
"""
import logging

from services.ingestion.db.repositories import HeroRepository
from services.ingestion.domains.heroes.dtos import EnrichedPlayerStats
from services.ingestion.domains.matches.dtos import Match

logger = logging.getLogger(__name__)


def enrich_match(
    match: Match,
    hero_repo: HeroRepository,
) -> list[EnrichedPlayerStats]:
    """Збагачує гравців матчу даними героя і ролі з DB.

    Для кожного гравця з match.players:
      1. Шукає героя через hero_repo.get_with_role(hero_id).
      2. Якщо знайдений — заповнює hero_name, primary_attr, attack_type, role.
      3. Якщо не знайдений — логує warning, всі hero-поля = None.

    Args:
        match: провалідований Match DTO з domain layer.
        hero_repo: HeroRepository з активним DB-з'єднанням.
                   Caller відповідає за lifecycle з'єднання (UnitOfWork або conn).

    Returns:
        Список EnrichedPlayerStats — по одному на кожного гравця в матчі.
        Порядок відповідає match.players.
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
            hero_db, role = hero_result
            hero_name = hero_db.localized_name
            primary_attr = hero_db.primary_attr
            attack_type = hero_db.attack_type

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