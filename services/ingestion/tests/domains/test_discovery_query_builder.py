# services/ingestion/tests/domains/test_discovery_query_builder.py
"""Unit-тести для build_explorer_sql — без HTTP, без DB.

Обмеження OpenDota Explorer (перевірено 2026-03):
patch і region колонок немає в public_matches — ігноруються в SQL.
"""

from services.ingestion.domains.discovery.dtos import DiscoveryFilter
from services.ingestion.domains.discovery.query_builder import build_explorer_sql


def test_default_filter_generates_valid_sql() -> None:
    """Дефолтний фільтр генерує коректний SQL."""
    f = DiscoveryFilter()
    sql = build_explorer_sql(f)

    assert "SELECT match_id FROM public_matches" in sql
    assert "lobby_type = 7" in sql
    assert "avg_rank_tier >= 60" in sql
    assert "ORDER BY start_time DESC" in sql
    assert "LIMIT 100" in sql


def test_custom_rank_tier_and_limit() -> None:
    """Кастомні min_rank_tier і limit коректно підставляються."""
    f = DiscoveryFilter(min_rank_tier=70, limit=50)
    sql = build_explorer_sql(f)

    assert "avg_rank_tier >= 70" in sql
    assert "LIMIT 50" in sql


def test_zero_rank_tier_omits_condition() -> None:
    """min_rank_tier=0 — умова фільтрації не додається."""
    f = DiscoveryFilter(min_rank_tier=0)
    sql = build_explorer_sql(f)

    assert "avg_rank_tier" not in sql


def test_patch_ignored_in_sql() -> None:
    """patch ігнорується — колонка відсутня в public_matches."""
    f = DiscoveryFilter(patch=138)
    sql = build_explorer_sql(f)

    assert "patch" not in sql


def test_region_ignored_in_sql() -> None:
    """region ігнорується — колонка відсутня в public_matches."""
    f = DiscoveryFilter(region=3)
    sql = build_explorer_sql(f)

    assert "region" not in sql


def test_all_supported_filters_combined() -> None:
    """Всі підтримувані фільтри разом генерують правильний SQL."""
    f = DiscoveryFilter(lobby_type=7, min_rank_tier=80, limit=25, patch=138, region=1)
    sql = build_explorer_sql(f)

    assert "lobby_type = 7" in sql
    assert "avg_rank_tier >= 80" in sql
    assert "LIMIT 25" in sql
    # patch і region не потрапляють в SQL
    assert "patch" not in sql
    assert "region" not in sql


def test_patch_absent_when_none() -> None:
    """patch=None — patch не в SQL (як і раніше)."""
    f = DiscoveryFilter(patch=None)
    sql = build_explorer_sql(f)

    assert "patch" not in sql


def test_region_absent_when_none() -> None:
    """region=None — region не в SQL (як і раніше)."""
    f = DiscoveryFilter(region=None)
    sql = build_explorer_sql(f)

    assert "region" not in sql