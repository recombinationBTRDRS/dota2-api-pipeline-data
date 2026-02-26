# services/ingestion/tests/providers/test_items_client.py
"""Unit-тести для OpenDotaItemsClient — mock requests.get."""
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from services.ingestion.providers.opendota.items_client import OpenDotaItemsClient

VALID_ITEMS_RESPONSE = {
    "blink": {"id": 1, "dname": "Blink Dagger", "cost": 2250,
              "secret_shop": 0, "side_shop": 0, "recipe": 0},
    "branches": {"id": 2, "dname": "Iron Branch", "cost": 50,
                 "secret_shop": 0, "side_shop": 0, "recipe": 0},
}


def make_response(status: int, json_data: Any) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


@patch("services.ingestion.providers.opendota.items_client.requests.get")
def test_get_items_returns_list(mock_get: MagicMock) -> None:
    mock_get.return_value = make_response(200, VALID_ITEMS_RESPONSE)
    items = OpenDotaItemsClient().get_items()
    assert len(items) == 2
    names = {i.name for i in items}
    assert names == {"blink", "branches"}


@patch("services.ingestion.providers.opendota.items_client.requests.get")
def test_get_items_retries_on_429(mock_get: MagicMock) -> None:
    mock_get.side_effect = [
        make_response(429, {}),
        make_response(200, VALID_ITEMS_RESPONSE),
    ]
    with patch("services.ingestion.providers.opendota.items_client.time.sleep"):
        items = OpenDotaItemsClient().get_items()
    assert len(items) == 2
    assert mock_get.call_count == 2


@patch("services.ingestion.providers.opendota.items_client.requests.get")
def test_get_items_fails_fast_on_4xx(mock_get: MagicMock) -> None:
    mock_get.return_value = make_response(403, {})
    with pytest.raises(RuntimeError, match="403"):
        OpenDotaItemsClient().get_items()
    assert mock_get.call_count == 1


@patch("services.ingestion.providers.opendota.items_client.requests.get")
def test_get_items_raises_after_exhausted_retries(mock_get: MagicMock) -> None:
    mock_get.return_value = make_response(503, {})
    with patch("services.ingestion.providers.opendota.items_client.time.sleep"):
        with pytest.raises(RuntimeError, match="attempts exhausted"):
            OpenDotaItemsClient().get_items()