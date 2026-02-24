#services/ingestion/tests/test_health.py

from fastapi.testclient import TestClient
from services.ingestion.app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}