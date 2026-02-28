# services/ingestion/tests/providers/test_heroes_client.py
"""Unit-тести для OpenDotaHeroesClient — mock requests.get."""
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from services.ingestion.providers.opendota.heroes_client import OpenDotaHeroesClient

VALID_HEROES_RESPONSE = [
    {"id": 1, "name": "npc_dota_hero_antimage", "localized_name": "Anti-Mage",
     "primary_attr": "agi", "attack_type": "Melee"},
    {"id": 2, "name": "npc_dota_hero_axe", "localized_name": "Axe",
     "primary_attr": "str", "attack_type": "Melee"},
]


def make_response(status: int, json_data: Any) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    resp.text = str(json_data)
    return resp


@patch("services.ingestion.providers.opendota.heroes_client.requests.get")
def test_get_heroes_returns_list(mock_get: MagicMock) -> None:
    mock_get.return_value = make_response(200, VALID_HEROES_RESPONSE)
    with patch("services.ingestion.providers.opendota.heroes_client.time.sleep"):
        heroes = OpenDotaHeroesClient().get_heroes()

    assert isinstance(heroes, list)
    assert len(heroes) == 2
    assert heroes[0]["name"] == "npc_dota_hero_antimage"


@patch("services.ingestion.providers.opendota.heroes_client.requests.get")
def test_get_heroes_retries_on_429(mock_get: MagicMock) -> None:
    mock_get.side_effect = [
        make_response(429, {}),
        make_response(200, VALID_HEROES_RESPONSE),
    ]
    with patch("services.ingestion.providers.opendota.heroes_client.time.sleep"):
        heroes = OpenDotaHeroesClient().get_heroes()
    assert len(heroes) == 2
    assert mock_get.call_count == 2


@patch("services.ingestion.providers.opendota.heroes_client.requests.get")
def test_get_heroes_fails_fast_on_4xx(mock_get: MagicMock) -> None:
    mock_get.return_value = make_response(404, {})

    with patch("services.ingestion.providers.opendota.heroes_client.time.sleep"):
        with pytest.raises(RuntimeError, match="Heroes client error 404"):
            OpenDotaHeroesClient().get_heroes()


@patch("services.ingestion.providers.opendota.heroes_client.requests.get")
def test_get_heroes_raises_after_exhausted_retries(mock_get: MagicMock) -> None:
    mock_get.return_value = make_response(503, {})
    with patch("services.ingestion.providers.opendota.heroes_client.time.sleep"):
        with pytest.raises(RuntimeError, match="attempts exhausted"):
            OpenDotaHeroesClient().get_heroes()