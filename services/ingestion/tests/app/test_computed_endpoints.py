# services/ingestion/tests/app/test_computed_endpoints.py
"""E2E тести для /computed endpoints (Epic 5.8)."""
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from services.ingestion.app.main import app
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import init_db
from services.ingestion.tests.seed_helpers import (
    seed_hero,
    seed_item,
    seed_item_slot,
    seed_match,
    seed_mp,
    seed_role_score,
)


@pytest.fixture()
def db_conn(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    yield db_path


@pytest.fixture()
def client(db_conn) -> TestClient:
    return TestClient(app)


@contextmanager
def _conn(db_path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ── POST /computed/rebuild ────────────────────────────────────────────────────

def test_rebuild_endpoint_returns_200_empty_db(client) -> None:
    resp = client.post("/computed/rebuild")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["hero_stats_rows"] == 0
    assert data["item_build_rows"] == 0


def test_rebuild_endpoint_returns_row_counts(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        seed_item(conn, 10, "Blink Dagger")
        for i in range(1, 4):
            seed_match(conn, i)
            seed_mp(conn, i, 0, 1, win=(i <= 2))
            seed_item_slot(conn, i, 0, 10)

    resp = client.post("/computed/rebuild")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hero_stats_rows"] >= 1  # мінімум 1 rollup рядок
    assert data["item_build_rows"] == 1


# ── GET /computed/staleness ───────────────────────────────────────────────────

def test_staleness_none_before_rebuild(client) -> None:
    resp = client.get("/computed/staleness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hero_stats_computed"] is None
    assert data["hero_item_build_computed"] is None


def test_staleness_set_after_rebuild(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        seed_match(conn, 1)
        seed_mp(conn, 1, 0, 1, win=True)

    client.post("/computed/rebuild")

    resp = client.get("/computed/staleness")
    assert resp.status_code == 200
    assert resp.json()["hero_stats_computed"] is not None
    assert resp.json()["hero_stats_computed"] > 0


# ── GET /computed/heroes/{hero_id}/stats ─────────────────────────────────────

def test_get_hero_stats_404_before_rebuild(client) -> None:
    resp = client.get("/computed/heroes/1/stats")
    assert resp.status_code == 404


def test_get_hero_stats_200_after_rebuild(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        for i in range(1, 6):
            seed_match(conn, i)
            seed_mp(conn, i, 0, 1, win=(i <= 3))

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/stats")
    assert resp.status_code == 200
    data = resp.json()
    # global rollup
    global_rows = [r for r in data if r["patch"] is None and r["region"] is None]
    assert len(global_rows) == 1
    row = global_rows[0]
    assert row["hero_id"] == 1
    assert row["hero_name"] == "Anti-Mage"
    assert row["matches_played"] == 5
    assert row["wins"] == 3
    assert row["winrate"] == 0.6
    assert row["primary_pos"] == 1


def test_get_hero_stats_filter_by_patch(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        seed_match(conn, 1, patch=38)
        seed_match(conn, 2, patch=39)
        seed_mp(conn, 1, 0, 1, win=True)
        seed_mp(conn, 2, 0, 1, win=False)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/stats?patch=38")
    assert resp.status_code == 200
    data = resp.json()
    assert all(r["patch"] == 38 for r in data)
    assert data[0]["wins"] == 1


def test_get_hero_stats_avg_gpm_correct(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        seed_match(conn, 1)
        seed_match(conn, 2)
        seed_mp(conn, 1, 0, 1, win=True,  gpm=400)
        seed_mp(conn, 2, 0, 1, win=False, gpm=600)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/stats")
    global_rows = [r for r in resp.json() if r["patch"] is None and r["region"] is None]
    assert global_rows[0]["avg_gpm"] == 500.0


# ── GET /computed/heroes/top ──────────────────────────────────────────────────

def test_get_top_heroes_empty_before_rebuild(client) -> None:
    resp = client.get("/computed/heroes/top?min_matches=1")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_top_heroes_sorted_by_winrate(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        for i in range(1, 6):
            seed_match(conn, i)
            seed_mp(conn, i, 0, 1, win=(i <= 3))
        seed_hero(conn, 2, "Axe")
        seed_role_score(conn, 2, 3)
        for i in range(10, 15):
            seed_match(conn, i)
            seed_mp(conn, i, 1, 2, win=(i <= 13))

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/top?min_matches=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert data[0]["winrate"] >= data[1]["winrate"]


def test_get_top_heroes_min_matches_excludes(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        seed_match(conn, 1)
        seed_mp(conn, 1, 0, 1, win=True)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/top?min_matches=5")
    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /computed/heroes/{hero_id}/items/{primary_pos} ───────────────────────

def test_get_hero_items_404_no_data(client) -> None:
    resp = client.get("/computed/heroes/1/items/1")
    assert resp.status_code == 404


def test_get_hero_items_200_after_rebuild(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        seed_item(conn, 10, "Blink Dagger")
        for i in range(1, 4):
            seed_match(conn, i)
            seed_mp(conn, i, 0, 1, win=(i <= 2))
            seed_item_slot(conn, i, 0, 10)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/items/1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["item_id"] == 10
    assert data[0]["times_bought"] == 3
    assert data[0]["times_won"] == 2


def test_get_hero_items_422_invalid_pos(client) -> None:
    resp = client.get("/computed/heroes/1/items/6")
    assert resp.status_code == 422


# ── Full E2E ──────────────────────────────────────────────────────────────────

def test_full_e2e_ingest_rebuild_api(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        seed_hero(conn, 1, "Anti-Mage")
        seed_role_score(conn, 1, 1)
        seed_hero(conn, 2, "Crystal-Maiden")
        seed_role_score(conn, 2, 5)
        seed_item(conn, 10, "Blink Dagger")
        seed_item(conn, 11, "Force Staff")
        for i in range(1, 6):
            seed_match(conn, i)
            seed_mp(conn, i, 0, 1, win=(i <= 3))
            seed_mp(conn, i, 1, 2, win=(i <= 2))
            seed_item_slot(conn, i, 0, 10)
            seed_item_slot(conn, i, 1, 11)

    rebuild_resp = client.post("/computed/rebuild")
    assert rebuild_resp.status_code == 200
    assert rebuild_resp.json()["hero_stats_rows"] >= 2
    assert rebuild_resp.json()["item_build_rows"] == 2

    staleness = client.get("/computed/staleness").json()
    assert staleness["hero_stats_computed"] is not None

    am_data = client.get("/computed/heroes/1/stats").json()
    am_global = next(r for r in am_data if r["patch"] is None and r["region"] is None)
    assert am_global["wins"] == 3
    assert am_global["winrate"] == 0.6

    cm_data = client.get("/computed/heroes/2/stats").json()
    cm_global = next(r for r in cm_data if r["patch"] is None and r["region"] is None)
    assert cm_global["wins"] == 2
    assert cm_global["winrate"] == 0.4

    am_items = client.get("/computed/heroes/1/items/1").json()
    assert am_items[0]["item_id"] == 10
    assert am_items[0]["times_bought"] == 5
    assert am_items[0]["times_won"] == 3