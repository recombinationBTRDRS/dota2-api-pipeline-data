# services/ingestion/app/rebuild_all.py
"""Epic 5 — Coordinator для rebuild всіх pre-computed таблиць.

Порядок: hero_stats → item_builds → matchups → synergies.
Кожен rebuild має власний UnitOfWork — не справжня атомарність,
але прийнятно для pre-computed layer (наступний rebuild виправить стан).
"""
import logging

logger = logging.getLogger(__name__)


def rebuild_all_computed() -> dict[str, int]:
    """Rebuild всіх pre-computed таблиць.

    Returns:
        {
            "hero_stats_rows": N,
            "item_build_rows": M,
            "matchup_rows": K,
            "synergy_rows": L,
        }
    """
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds
    from services.ingestion.app.rebuild_matchups import rebuild_matchups
    from services.ingestion.app.rebuild_synergies import rebuild_synergies

    hero_rows = rebuild_hero_stats()
    item_rows = rebuild_item_builds()
    matchup_rows = rebuild_matchups()
    synergy_rows = rebuild_synergies()

    result = {
        "hero_stats_rows": hero_rows,
        "item_build_rows": item_rows,
        "matchup_rows": matchup_rows,
        "synergy_rows": synergy_rows,
    }
    logger.info("rebuild_all_computed: %s", result)
    return result