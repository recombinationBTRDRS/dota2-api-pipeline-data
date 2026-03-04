# services/ingestion/tests/providers/test_explorer_client.py
"""Unit-тести для OpenDotaExplorerClient — mock requests.get, без реального HTTP."""
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from services.ingestion.domains.discovery.dtos import DiscoveredMatch, DiscoveryFilter
from services.ingestion.providers.opendota.explorer_client import OpenDotaExplorerClient


def make_response(status: int, json_data: Any) -> MagicMock:
    """Фабрика mock HTTP response."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


VALID_ROWS = {
    "rows": [
        {"match_id": 1001},
        {"match_id": 1002},
        {"match_id": 1003},
    ]
}


@patch("services.ingestion.providers.opendota.explorer_client.requests.get")
def test_discover_returns_match_list(mock_get: MagicMock) -> None:
    """Успішний запит повертає список DiscoveredMatch."""
    mock_get.return_value = make_response(200, VALID_ROWS)

    client = OpenDotaExplorerClient()
    result = client.discover(DiscoveryFilter())

    assert len(result) == 3
    assert all(isinstance(m, DiscoveredMatch) for m in result)
    assert [m.match_id for m in result] == [1001, 1002, 1003]


@patch("services.ingestion.providers.opendota.explorer_client.requests.get")
def test_discover_empty_rows(mock_get: MagicMock) -> None:
    """Порожній rows — повертає пустий список без помилок."""
    mock_get.return_value = make_response(200, {"rows": []})

    result = OpenDotaExplorerClient().discover(DiscoveryFilter())

    assert result == []


@patch("services.ingestion.providers.opendota.explorer_client.requests.get")
def test_discover_raises_on_missing_rows(mock_get: MagicMock) -> None:
    """Відповідь без поля rows — ValueError з описом."""
    mock_get.return_value = make_response(200, {"error": "bad sql"})

    with pytest.raises(ValueError, match="rows"):
        OpenDotaExplorerClient().discover(DiscoveryFilter())


@patch("services.ingestion.providers.opendota.explorer_client.requests.get")
def test_discover_retries_on_429(mock_get: MagicMock) -> None:
    """429 — клієнт робить retry і повертає результат після успіху."""
    mock_get.side_effect = [
        make_response(429, {}),
        make_response(200, VALID_ROWS),
    ]

    client = OpenDotaExplorerClient()
    with patch("services.ingestion.providers.opendota.explorer_client.time.sleep"):
        result = client.discover(DiscoveryFilter())

    assert len(result) == 3
    assert mock_get.call_count == 2


@patch("services.ingestion.providers.opendota.explorer_client.requests.get")
def test_discover_retries_on_500(mock_get: MagicMock) -> None:
    """5xx — клієнт робить retry і повертає результат після успіху."""
    mock_get.side_effect = [
        make_response(500, {}),
        make_response(500, {}),
        make_response(200, VALID_ROWS),
    ]

    client = OpenDotaExplorerClient()
    with patch("services.ingestion.providers.opendota.explorer_client.time.sleep"):
        result = client.discover(DiscoveryFilter())

    assert len(result) == 3
    assert mock_get.call_count == 3


@patch("services.ingestion.providers.opendota.explorer_client.requests.get")
def test_discover_fails_fast_on_4xx(mock_get: MagicMock) -> None:
    """4xx (крім 429) — одразу RuntimeError, без retry."""
    mock_get.return_value = make_response(404, {})

    with pytest.raises(RuntimeError, match="404"):
        OpenDotaExplorerClient().discover(DiscoveryFilter())

    assert mock_get.call_count == 1


@patch("services.ingestion.providers.opendota.explorer_client.requests.get")
def test_discover_raises_after_exhausted_retries(mock_get: MagicMock) -> None:
    """Всі retry вичерпані — RuntimeError з описом."""
    mock_get.return_value = make_response(503, {})

    client = OpenDotaExplorerClient()
    with patch("services.ingestion.providers.opendota.explorer_client.time.sleep"):
        with pytest.raises(RuntimeError, match="attempts exhausted"):
            client.discover(DiscoveryFilter())


@patch("services.ingestion.providers.opendota.explorer_client.requests.get")
def test_sql_passed_as_query_param(mock_get: MagicMock) -> None:
    """SQL генерується і передається як query param ?sql=..."""
    mock_get.return_value = make_response(200, VALID_ROWS)

    client = OpenDotaExplorerClient()
    f = DiscoveryFilter(min_rank_tier=70, patch=138)
    client.discover(f)

    _, kwargs = mock_get.call_args
    sql_param = kwargs["params"]["sql"]
    assert "avg_rank_tier >= 70" in sql_param
    # patch ignored — column removed from public_matches (2026-03)
