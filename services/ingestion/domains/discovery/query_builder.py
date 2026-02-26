# services/ingestion/domains/discovery/query_builder.py
from services.ingestion.domains.discovery.dtos import DiscoveryFilter


def build_explorer_sql(f: DiscoveryFilter) -> str:
    """Будує SQL-рядок для OpenDota Explorer API (/explorer?sql=...).

    OpenDota Explorer приймає обмежений subset SQL проти таблиці public_matches.
    Колонки: match_id, start_time, avg_mmr, lobby_type, patch, region.

    Args:
        f: фільтри discovery.

    Returns:
        SQL-рядок готовий для підстановки в ?sql= query param.

    Example:
        >>> f = DiscoveryFilter(lobby_type=7, min_mmr=4000, limit=50)
        >>> sql = build_explorer_sql(f)
        >>> assert "avg_mmr >= 4000" in sql
    """
    conditions: list[str] = [
        f"lobby_type = {f.lobby_type}",
        f"avg_mmr >= {f.min_mmr}",
    ]

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