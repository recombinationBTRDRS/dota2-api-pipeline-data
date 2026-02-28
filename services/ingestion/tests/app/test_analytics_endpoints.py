# services/ingestion/tests/app/test_analytics_endpoints.py
"""FastAPI TestClient тести для analytics endpoints (Task 4.5).

Використовує реальний tmp SQLite через dependency override.
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from services.ingestion.app.main import app
from services.ingestion.app.routers.analytics import get_db
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import init_db

# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_conn(monkeypatch, tmp_path):
    """Ізольована tmp SQLite + override FastAPI get_db dependency."""
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()

    def override_get_db():
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    yield db_path
    app.dependency_overrides.clear()


@pytest.fixture()
def client(db_conn) -> TestClient:
    return TestClient(app)


# ── seed helpers ──────────────────────────────────────────────────────────────

def _seed_hero(conn, hero_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO heroes (id, name, localized_name, primary_attr, attack_type) "
        "VALUES (?, ?, ?, 'agi', 'Melee')",
        (hero_id, f"npc_dota_hero_{name}", name),
    )
    conn.commit()


def _seed_role_score(conn, hero_id: int, primary_pos: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO hero_role_scores "
        "(hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos) "
        "VALUES (?, 3, 3, 3, 3, 3, 5, ?)",
        (hero_id, primary_pos),
    )
    conn.commit()


def _seed_item(conn, item_id: int, name: str, localized: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO items (id, name, localized_name, cost) VALUES (?, ?, ?, 0)",
        (item_id, name, localized),
    )
    conn.commit()


def _seed_match(conn, match_id: int, duration: int = 2400) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win) "
        "VALUES (?, 1700000000, ?, 1)",
        (match_id, duration),
    )
    conn.commit()


def _seed_mp(conn, match_id: int, slot: int, hero_id: int, win: bool) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_players "
        "(match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win) "
        "VALUES (?, ?, ?, 5, 2, 8, 500, 600, ?)",
        (match_id, slot, hero_id, int(win)),
    )
    conn.commit()


def _seed_item_for_player(conn, match_id: int, slot: int, item_id: int, item_slot: int = 0) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_player_items (match_id, player_slot, slot, item_id) "
        "VALUES (?, ?, ?, ?)",
        (match_id, slot, item_slot, item_id),
    )
    conn.commit()


def _get_conn(db_path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# ── /health ───────────────────────────────────────────────────────────────────

def test_health_still_works(client) -> None:
    """/health не зламався після додавання analytics router."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── GET /heroes/{hero_id}/stats ───────────────────────────────────────────────

def test_get_hero_stats_200(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    for i in range(1, 6):
        _seed_match(conn, i)
        _seed_mp(conn, i, 0, hero_id=1, win=(i <= 3))
    conn.close()

    resp = client.get("/heroes/1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hero_id"] == 1
    assert data["hero_name"] == "Anti-Mage"
    assert data["matches_played"] == 5
    assert data["winrate"] == 0.6


def test_get_hero_stats_404_unknown(client) -> None:
    resp = client.get("/heroes/9999/stats")
    assert resp.status_code == 404


def test_get_hero_stats_min_matches_filter(client, db_conn) -> None:
    """min_matches=10 → 404 якщо героя тільки 3 матчі."""
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    for i in range(1, 4):
        _seed_match(conn, i)
        _seed_mp(conn, i, 0, hero_id=1, win=True)
    conn.close()

    resp = client.get("/heroes/1/stats?min_matches=10")
    assert resp.status_code == 404


# ── GET /heroes/{hero_id}/stats/role/{primary_pos} ────────────────────────────

def test_get_hero_stats_by_role_200(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    _seed_role_score(conn, hero_id=1, primary_pos=1)
    for i in range(1, 6):
        _seed_match(conn, i)
        _seed_mp(conn, i, 0, hero_id=1, win=(i <= 4))
    conn.close()

    resp = client.get("/heroes/1/stats/role/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["primary_pos"] == 1
    assert data["matches_played"] == 5
    assert data["winrate"] == 0.8


def test_get_hero_stats_by_role_404(client) -> None:
    resp = client.get("/heroes/9999/stats/role/1")
    assert resp.status_code == 404


def test_get_hero_stats_by_role_422_invalid_pos(client) -> None:
    """primary_pos=6 → 422 (FastAPI validation)."""
    resp = client.get("/heroes/1/stats/role/6")
    assert resp.status_code == 422


# ── GET /heroes/{hero_id}/items ───────────────────────────────────────────────

def test_get_hero_items_200(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    _seed_item(conn, 1, "blink", "Blink Dagger")
    _seed_match(conn, 1)
    _seed_mp(conn, 1, 0, hero_id=1, win=True)
    _seed_item_for_player(conn, 1, 0, item_id=1)
    conn.close()

    resp = client.get("/heroes/1/items")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["item_id"] == 1
    assert data[0]["item_name"] == "Blink Dagger"


def test_get_hero_items_empty_list_not_404(client) -> None:
    """Герой без items → 200 з порожнім списком."""
    resp = client.get("/heroes/9999/items")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_hero_items_win_only(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    _seed_item(conn, 1, "blink", "Blink Dagger")
    # 2 матчі: 1 win, 1 loss, blink у обох
    for i in range(1, 3):
        _seed_match(conn, i)
        _seed_mp(conn, i, 0, hero_id=1, win=(i == 1))
        _seed_item_for_player(conn, i, 0, item_id=1)
    conn.close()

    resp = client.get("/heroes/1/items?win_only=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["times_bought"] == 1   # тільки win матч


def test_get_hero_items_limit(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    _seed_match(conn, 1)
    _seed_mp(conn, 1, 0, hero_id=1, win=True)
    for item_id in range(1, 7):  # 6 items
        _seed_item_for_player(conn, 1, 0, item_id=item_id, item_slot=item_id - 1)
    conn.close()

    resp = client.get("/heroes/1/items?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


# ── GET /analytics/meta ───────────────────────────────────────────────────────

def test_get_meta_snapshot_200(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    _seed_role_score(conn, hero_id=1, primary_pos=1)
    for i in range(1, 6):
        _seed_match(conn, i)
        _seed_mp(conn, i, 0, hero_id=1, win=True)
    conn.close()

    resp = client.get("/analytics/meta")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["hero_id"] == 1
    assert "meta_score" in data[0]


def test_get_meta_snapshot_filter_by_pos(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    _seed_role_score(conn, hero_id=1, primary_pos=1)
    _seed_hero(conn, 2, "Axe")
    _seed_role_score(conn, hero_id=2, primary_pos=3)
    for i in range(1, 4):
        _seed_match(conn, i)
        _seed_mp(conn, i, 0, hero_id=1, win=True)
        _seed_mp(conn, i, 1, hero_id=2, win=True)
    conn.close()

    resp = client.get("/analytics/meta?primary_pos=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["hero_id"] == 1


def test_get_meta_snapshot_422_invalid_pos(client) -> None:
    resp = client.get("/analytics/meta?primary_pos=6")
    assert resp.status_code == 422


# ── GET /analytics/leaderboard/{primary_pos} ─────────────────────────────────

def test_get_leaderboard_200(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    _seed_role_score(conn, hero_id=1, primary_pos=1)
    for i in range(1, 6):
        _seed_match(conn, i)
        _seed_mp(conn, i, 0, hero_id=1, win=True)
    conn.close()

    resp = client.get("/analytics/leaderboard/1?min_matches=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["hero_id"] == 1
    assert data[0]["primary_pos"] == 1


def test_get_leaderboard_empty(client) -> None:
    resp = client.get("/analytics/leaderboard/1?min_matches=1")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_leaderboard_422_invalid_pos(client) -> None:
    resp = client.get("/analytics/leaderboard/6")
    assert resp.status_code == 422


# ── GET /analytics/hero/{hero_id}/timeline ────────────────────────────────────

def test_get_hero_timeline_200(client, db_conn) -> None:
    conn = _get_conn(db_conn)
    _seed_hero(conn, 1, "Anti-Mage")
    _seed_match(conn, 1, duration=1500)   # early
    _seed_match(conn, 2, duration=4000)   # late
    _seed_mp(conn, 1, 0, hero_id=1, win=True)
    _seed_mp(conn, 2, 0, hero_id=1, win=False)
    conn.close()

    resp = client.get("/analytics/hero/1/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    phases = [d["phase"] for d in data]
    assert "early" in phases
    assert "late" in phases


def test_get_hero_timeline_empty_not_404(client) -> None:
    resp = client.get("/analytics/hero/9999/timeline")
    assert resp.status_code == 200
    assert resp.json() == []