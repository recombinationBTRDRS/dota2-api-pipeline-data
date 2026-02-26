# services/ingestion/tests/test_health.py
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.ingestion.app.main import app


def test_health():
    """Health endpoint повертає 200 і коректну схему відповіді."""
    with TestClient(app) as client:
        with patch("services.ingestion.app.main._check_db", return_value=True):
            resp = client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db_ok"] is True