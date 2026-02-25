#services/ingestion/tests/providers/test_opendota_client.py
from unittest.mock import Mock, patch
import pytest

from services.ingestion.providers.opendota.client import OpenDotaClient


def make_response(status: int, payload: dict | None = None):
    resp = Mock()
    resp.status_code = status
    resp.json.return_value = payload or {}
    resp.raise_for_status.return_value = None
    return resp


def test_get_match_success():
    fake_response = make_response(200, {"match_id": 123})

    with patch("requests.get", return_value=fake_response), \
         patch("time.sleep"):
        client = OpenDotaClient()
        data = client.get_match(123)

    assert data["match_id"] == 123


def test_get_match_retry_on_429_then_success():
    resp_429 = make_response(429)
    resp_ok = make_response(200, {"match_id": 123})

    with patch("requests.get", side_effect=[resp_429, resp_ok]), \
         patch("time.sleep"):
        client = OpenDotaClient()
        data = client.get_match(123)

    assert data["match_id"] == 123


def test_get_match_fail_after_retries():
    resp_500 = make_response(500)

    with patch("requests.get", return_value=resp_500), \
         patch("time.sleep"):
        client = OpenDotaClient()

        with pytest.raises(RuntimeError):
            client.get_match(123)
