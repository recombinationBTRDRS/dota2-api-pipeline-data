# services/analysis/tests/test_reports_api.py
"""
Integration тести для /reports endpoints.
IngestionClient замокований — не робить реальних HTTP запитів.
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from services.analysis.app.clients.ingestion import IngestionClient

# ── 10 mock гравців ───────────────────────────────────────────────────────────

MOCK_PLAYERS = [
    {"hero_id": i, "is_radiant": i <= 5,
     "kills": 5, "deaths": 3, "assists": 4,
     "gold_per_min": 450, "net_worth": 12000}
    for i in range(1, 11)
]

MOCK_SYNERGIES = {
    h: [{"ally_id": a, "winrate": 0.54, "matches": 20} for a in range(1, 6) if a != h]
    for h in range(1, 6)
}
MOCK_MATCHUPS = {
    h: [{"opponent_id": e, "winrate": 0.51, "matches": 15} for e in range(6, 11)]
    for h in range(1, 6)
}
MOCK_STATS = {i: {"avg_gpm": 420.0} for i in range(1, 11)}


def _mock_client() -> IngestionClient:
    c = MagicMock(spec=IngestionClient)
    c.get_match_players.return_value   = MOCK_PLAYERS
    c.get_hero_synergies.side_effect   = lambda hid, **kw: MOCK_SYNERGIES.get(hid, [])
    c.get_hero_matchups.side_effect    = lambda hid, **kw: MOCK_MATCHUPS.get(hid, [])
    c.get_hero_stats.side_effect       = lambda hid, **kw: MOCK_STATS.get(hid)
    return c


# ── fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def client(tmp_path):
    db_path = str(tmp_path / "test.sqlite")
    os.environ["ANALYSIS_DB_PATH"] = db_path

    import importlib

    import services.analysis.app.config as cfg_mod
    import services.analysis.app.main as main_mod
    import services.analysis.db.sqlite as db_mod

    cfg_mod.config = cfg_mod.AnalysisConfig()
    importlib.reload(db_mod)
    importlib.reload(main_mod)

    from services.analysis.db.sqlite import init_db
    init_db(db_path)

    from services.analysis.app.main import app
    with TestClient(app) as c:
        yield c


# ── tests ─────────────────────────────────────────────────────────────────────

def test_generate_report_not_in_watchlist(client):
    """POST /reports без watchlist entry → 404."""
    resp = client.post("/reports/matches/99999")
    assert resp.status_code == 404


def test_generate_report_ok(client):
    """Додаємо у watchlist → генеруємо звіт → перевіряємо поля."""
    match_id = 8716150035
    client.post("/watchlist/matches", json={"match_id": match_id})

    with patch(
        "services.analysis.app.routers.reports.IngestionClient",
        return_value=_mock_client(),
    ):
        resp = client.post(f"/reports/matches/{match_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["match_id"] == match_id
    assert data["data_quality"] in ("complete", "partial", "minimal")
    assert "generated_at" in data


def test_generate_report_has_teamfight(client):
    match_id = 111
    client.post("/watchlist/matches", json={"match_id": match_id})

    with patch(
        "services.analysis.app.routers.reports.IngestionClient",
        return_value=_mock_client(),
    ):
        resp = client.post(f"/reports/matches/{match_id}")

    data = resp.json()
    assert data["teamfight"] is not None
    assert "kill_ratio" in data["teamfight"]
    assert "teamfight_verdict" in data["teamfight"]


def test_generate_report_has_economy(client):
    match_id = 222
    client.post("/watchlist/matches", json={"match_id": match_id})

    with patch(
        "services.analysis.app.routers.reports.IngestionClient",
        return_value=_mock_client(),
    ):
        resp = client.post(f"/reports/matches/{match_id}")

    data = resp.json()
    assert data["economy"] is not None
    assert len(data["economy"]["players"]) == 10
    assert "networth_advantage" in data["economy"]


def test_get_report_after_generate(client):
    """POST генерує → GET повертає збережений звіт."""
    match_id = 333
    client.post("/watchlist/matches", json={"match_id": match_id})

    with patch(
        "services.analysis.app.routers.reports.IngestionClient",
        return_value=_mock_client(),
    ):
        client.post(f"/reports/matches/{match_id}")

    resp = client.get(f"/reports/matches/{match_id}")
    assert resp.status_code == 200
    assert resp.json()["match_id"] == match_id


def test_get_report_not_found(client):
    """GET без попереднього POST → 404."""
    resp = client.get("/reports/matches/999999")
    assert resp.status_code == 404


def test_watchlist_status_updated_to_analyzed(client):
    """Після генерації звіту watchlist status = 'analyzed'."""
    match_id = 444
    client.post("/watchlist/matches", json={"match_id": match_id})

    with patch(
        "services.analysis.app.routers.reports.IngestionClient",
        return_value=_mock_client(),
    ):
        client.post(f"/reports/matches/{match_id}")

    wl = client.get(f"/watchlist/matches/{match_id}").json()
    assert wl["status"] == "analyzed"


def test_regenerate_report_idempotent(client):
    """Повторний POST перегенеровує звіт без помилок."""
    match_id = 555
    client.post("/watchlist/matches", json={"match_id": match_id})

    with patch(
        "services.analysis.app.routers.reports.IngestionClient",
        return_value=_mock_client(),
    ):
        r1 = client.post(f"/reports/matches/{match_id}")
        r2 = client.post(f"/reports/matches/{match_id}")

    assert r1.status_code == 200
    assert r2.status_code == 200
