# services/ingestion/tests/app/test_main.py
"""Тести для FastAPI endpoints: /health і /stats."""
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from services.ingestion.app.main import app
from services.ingestion.app.state import app_state


@pytest.fixture()
def client() -> Iterator[TestClient]:
    """TestClient без lifespan (init_db не потрібен для unit тестів)."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state() -> Iterator[None]:
    """Скидає app_state перед кожним тестом."""
    app_state.last_cycle_at = None
    app_state.last_cycle_stats = None
    yield


# ── /health ──────────────────────────────────────────────────────────────────


def test_health_returns_200_when_db_ok(client: TestClient) -> None:
    """Якщо DB доступна — /health повертає 200 і status='ok'."""
    with patch("services.ingestion.app.main._check_db", return_value=True):
        resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "db_ok": True}


def test_health_returns_503_when_db_unavailable(client: TestClient) -> None:
    """Якщо DB недоступна — /health повертає 503 і status='degraded'."""
    with patch("services.ingestion.app.main._check_db", return_value=False):
        resp = client.get("/health")

    assert resp.status_code == 503
    assert resp.json() == {"status": "degraded", "db_ok": False}


# ── /stats ───────────────────────────────────────────────────────────────────


def test_stats_returns_nulls_before_first_cycle(client: TestClient) -> None:
    """/stats повертає null поля якщо runner ще не запускався."""
    resp = client.get("/stats")

    assert resp.status_code == 200
    data = resp.json()
    assert data["last_cycle_at"] is None
    assert data["last_cycle_stats"] is None


def test_stats_returns_last_cycle_data(client: TestClient) -> None:
    """/stats повертає дані після того як runner оновив app_state."""
    app_state.last_cycle_at = 1700000000
    app_state.last_cycle_stats = {
        "discovered": 10,
        "skipped": 3,
        "ingested": 6,
        "failed": 1,
        "errors": [[999, "RuntimeError: timeout"]],
    }

    resp = client.get("/stats")

    assert resp.status_code == 200
    data = resp.json()
    assert data["last_cycle_at"] == 1700000000
    assert data["last_cycle_stats"]["ingested"] == 6
    assert data["last_cycle_stats"]["failed"] == 1