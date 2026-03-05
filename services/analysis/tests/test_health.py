# services/analysis/tests/test_health.py
import tempfile
import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path):
    """TestClient з тимчасовою БД."""
    db_path = str(tmp_path / "test_analysis.sqlite")
    os.environ["ANALYSIS_DB_PATH"] = db_path

    # Re-import після зміни env
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


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db_ok"] is True
