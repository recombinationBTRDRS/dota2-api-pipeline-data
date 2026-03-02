# services/ingestion/app/rebuild_all.py
"""Epic 5 — Атомарний coordinator для rebuild всіх pre-computed таблиць.

Увага: rebuild_hero_stats і rebuild_item_builds відкривають власний UnitOfWork.
Атомарність тут означає що обидва виклики або обидва виконуються, або
при помилці другого — перший вже committed (це прийнятно для pre-computed layer,
бо наступний rebuild виправить стан). Справжня атомарність потребує
рефактору rebuild функцій щоб приймати conn — відкладено до Epic 5+.
"""
import logging

logger = logging.getLogger(__name__)


def rebuild_all_computed() -> dict[str, int]:
    """Rebuild hero_stats_computed + hero_item_build_computed.

    Returns:
        {"hero_stats_rows": N, "item_build_rows": M}

    Raises:
        Exception — будь-яка помилка пробивається назовні.
    """
    from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats
    from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

    hero_rows = rebuild_hero_stats()
    item_rows = rebuild_item_builds()

    result = {"hero_stats_rows": hero_rows, "item_build_rows": item_rows}
    logger.info("rebuild_all_computed: %s", result)
    return result