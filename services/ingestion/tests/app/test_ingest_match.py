#services/ingestion/tests/app/test_ingest_match.py
from unittest.mock import patch

from services.ingestion.app.ingest_match import ingest_match


def test_ingest_match_pipeline():
    with patch("services.ingestion.providers.opendota.client.OpenDotaClient.get_match") as mock_get:
        mock_get.return_value = {
            "match_id": 123,
            "duration": 1000,
            "radiant_win": True,
            "start_time": 1700000000,
            "radiant_score": 40,
            "dire_score": 35,
            "players": [],
        }

        result = ingest_match(123)

    assert result.id == 123