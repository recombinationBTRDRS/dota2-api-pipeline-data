# services/ingestion/tests/domains/test_discovery_query_builder.py
"""Unit-тести для build_explorer_sql — без HTTP, без DB."""

from services.ingestion.domains.discovery.dtos import DiscoveryFilter
from services.ingestion.domains.discovery.query_builder import build_explorer_sql


def test_default_filter_generates_valid_sql() -> None:
    """Дефолтний фільтр генерує коректний SQL з усіма обов'язковими умовами."""
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


def test_patch_filter_included_when_set() -> None:
    """Фільтр по patch додається якщо вказано."""
    f = DiscoveryFilter(patch=138)
    sql = build_explorer_sql(f)

    assert "patch = 138" in sql


def test_patch_filter_absent_when_none() -> None:
    """Фільтр по patch відсутній якщо patch=None."""
    f = DiscoveryFilter(patch=None)
    sql = build_explorer_sql(f)

    assert "patch" not in sql


def test_region_filter_included_when_set() -> None:
    """Фільтр по region додається якщо вказано."""
    f = DiscoveryFilter(region=3)
    sql = build_explorer_sql(f)

    assert "region = 3" in sql


def test_region_filter_absent_when_none() -> None:
    """Фільтр по region відсутній якщо region=None."""
    f = DiscoveryFilter(region=None)
    sql = build_explorer_sql(f)

    assert "region" not in sql


def test_all_filters_combined() -> None:
    """Всі фільтри разом генерують правильний SQL."""
    f = DiscoveryFilter(lobby_type=7, min_rank_tier=80, limit=25, patch=138, region=1)
    sql = build_explorer_sql(f)

    assert "lobby_type = 7" in sql
    assert "avg_rank_tier >= 80" in sql
    assert "patch = 138" in sql
    assert "region = 1" in sql
    assert "LIMIT 25" in sql