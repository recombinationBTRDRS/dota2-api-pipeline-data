# services/ingestion/domains/discovery/query_builder.py
"""Будує SQL для OpenDota Explorer API (/explorer?sql=...).

Актуальні колонки public_matches (перевірено 2026-03):
    match_id, start_time, lobby_type, avg_rank_tier,
    num_rank_tier, radiant_win, duration, game_mode

ВИДАЛЕНІ колонки (більше не існують):
    avg_mmr  — замінено на avg_rank_tier
    patch    — відсутня
    region   — відсутня

Rank Tier шкала:
    10=Herald, 20=Guardian, 30=Crusader, 40=Archon,
    50=Legend, 60=Ancient, 70=Divine, 80+=Immortal
"""
from services.ingestion.domains.discovery.dtos import DiscoveryFilter


def build_explorer_sql(f: DiscoveryFilter) -> str:
    """Будує SQL-рядок для OpenDota Explorer API.

    Фільтрує по lobby_type і avg_rank_tier.
    patch і region не підтримуються Explorer API (колонки відсутні).

    Args:
        f: фільтри discovery.

    Returns:
        SQL-рядок готовий для підстановки в ?sql= query param.

    Example:
        >>> f = DiscoveryFilter(lobby_type=7, min_rank_tier=70, limit=50)
        >>> sql = build_explorer_sql(f)
        >>> assert "avg_rank_tier >= 70" in sql
    """
    conditions: list[str] = [
        f"lobby_type = {f.lobby_type}",
    ]

    if f.min_rank_tier is not None and f.min_rank_tier > 0:
        conditions.append(f"avg_rank_tier >= {f.min_rank_tier}")

    where_clause = " AND ".join(conditions)

    return (
        f"SELECT match_id FROM public_matches "
        f"WHERE {where_clause} "
        f"ORDER BY start_time DESC "
        f"LIMIT {f.limit}"
    )