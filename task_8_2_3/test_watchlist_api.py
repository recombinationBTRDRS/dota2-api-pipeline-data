# services/analysis/tests/test_watchlist_api.py
import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path):
    db_path = str(tmp_path / "test.sqlite")
    os.environ["ANALYSIS_DB_PATH"] = db_path

    import importlib
    import services.analysis.app.config as cfg_mod
    import services.analysis.db.sqlite as db_mod
    import services.analysis.app.main as main_mod

    cfg_mod.config = cfg_mod.AnalysisConfig()
    importlib.reload(db_mod)
    importlib.reload(main_mod)

    from services.analysis.db.sqlite import init_db
    init_db(db_path)

    from services.analysis.app.main import app
    with TestClient(app) as c:
        yield c


def test_post_match(client):
    resp = client.post("/watchlist/matches", json={"match_id": 12345})
    assert resp.status_code == 201
    data = resp.json()
    assert data["match_id"] == 12345
    assert data["status"] == "pending"


def test_post_duplicate_409(client):
    client.post("/watchlist/matches", json={"match_id": 99})
    resp = client.post("/watchlist/matches", json={"match_id": 99})
    assert resp.status_code == 409


def test_get_list(client):
    client.post("/watchlist/matches", json={"match_id": 1})
    client.post("/watchlist/matches", json={"match_id": 2})
    resp = client.get("/watchlist/matches")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_single(client):
    client.post("/watchlist/matches", json={"match_id": 555, "label": "test"})
    resp = client.get("/watchlist/matches/555")
    assert resp.status_code == 200
    assert resp.json()["label"] == "test"


def test_get_not_found(client):
    resp = client.get("/watchlist/matches/999999")
    assert resp.status_code == 404


def test_delete(client):
    client.post("/watchlist/matches", json={"match_id": 777})
    resp = client.delete("/watchlist/matches/777")
    assert resp.status_code == 204
    assert client.get("/watchlist/matches/777").status_code == 404


def test_delete_not_found(client):
    resp = client.delete("/watchlist/matches/999999")
    assert resp.status_code == 404


def test_e2e_flow(client):
    """POST → GET → DELETE → GET(404)"""
    client.post("/watchlist/matches", json={"match_id": 8716150035, "label": "ranked"})
    assert client.get("/watchlist/matches/8716150035").status_code == 200
    assert client.delete("/watchlist/matches/8716150035").status_code == 204
    assert client.get("/watchlist/matches/8716150035").status_code == 404
