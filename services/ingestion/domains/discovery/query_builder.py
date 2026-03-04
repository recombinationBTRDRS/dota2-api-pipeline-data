# services/ingestion/domains/discovery/query_builder.py
"""Будує SQL для OpenDota Explorer API (/explorer?sql=...).

Таблиця public_matches містить колонки:
  match_id, start_time, lobby_type, patch, region,
  avg_rank_tier, num_rank_tier, radiant_win, duration, game_mode

ВАЖЛИВО: колонки avg_mmr більше не існує в public_matches (видалена OpenDota).
Замість неї використовується avg_rank_tier:
  Tier 10-19 = Herald, 20-29 = Guardian, 30-39 = Crusader,
  40-49 = Archon,  50-59 = Legend,   60-69 = Ancient,
  70-79 = Divine,  80+   = Immortal
"""
from services.ingestion.domains.discovery.dtos import DiscoveryFilter


def build_explorer_sql(f: DiscoveryFilter) -> str:
    """Будує SQL-рядок для OpenDota Explorer API.

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

    if f.patch is not None:
        conditions.append(f"patch = {f.patch}")

    if f.region is not None:
        conditions.append(f"region = {f.region}")

    where_clause = " AND ".join(conditions)

    return (
        f"SELECT match_id FROM public_matches "
        f"WHERE {where_clause} "
        f"ORDER BY start_time DESC "
        f"LIMIT {f.limit}"
    )