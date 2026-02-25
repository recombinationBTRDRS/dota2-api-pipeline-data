#services/ingestion/tests/providers/test_opendota_client.py
from unittest.mock import Mock, patch

from services.ingestion.providers.opendota.client import OpenDotaClient


def test_get_match_success():
    fake_response = Mock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"match_id": 123}
    fake_response.raise_for_status.return_value = None

    with patch("requests.get", return_value=fake_response):
        client = OpenDotaClient()
        data = client.get_match(123)

    assert data["match_id"] == 123