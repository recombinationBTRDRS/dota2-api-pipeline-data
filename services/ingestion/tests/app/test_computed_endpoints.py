# services/ingestion/tests/app/test_computed_endpoints.py
"""E2E тести для /computed endpoints (Epic 5.8).

Сценарій кожного тесту:
  1. Seed raw data (heroes, matches, match_players, items)
  2. rebuild_hero_stats() / rebuild_item_builds()
  3. GET /computed/... → assert HTTP status + response body

Використовує monkeypatch DB_PATH (той самий підхід що і в test_analytics_endpoints.py).
computed.py router відкриває conn через get_connection() — monkeypatch DB_PATH достатньо.
"""
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from services.ingestion.app.main import app
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import init_db

# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_conn(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    yield db_path


@pytest.fixture()
def client(db_conn) -> TestClient:
    return TestClient(app)


# ── seed helpers ──────────────────────────────────────────────────────────────

@contextmanager
def _conn(db_path) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _seed_hero(conn, hero_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO heroes (id, name, localized_name, primary_attr, attack_type) "
        "VALUES (?, ?, ?, 'agi', 'Melee')",
        (hero_id, f"npc_dota_hero_{name}", name),
    )


def _seed_role_score(conn, hero_id: int, primary_pos: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO hero_role_scores "
        "(hero_id, pos1, pos2, pos3, pos4, pos5, flex_score, primary_pos) "
        "VALUES (?, 3, 3, 3, 3, 3, 5, ?)",
        (hero_id, primary_pos),
    )


def _seed_item(conn, item_id: int, name: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO items (id, name, localized_name, cost) VALUES (?, ?, ?, 0)",
        (item_id, f"item_{name}", name),
    )


def _seed_match(conn, match_id: int, patch: int | None = None) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO matches (id, start_time, duration, radiant_win, patch) "
        "VALUES (?, 1700000000, 2400, 1, ?)",
        (match_id, patch),
    )


def _seed_mp(conn, match_id: int, slot: int, hero_id: int, win: bool, gpm: int = 500) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_players "
        "(match_id, player_slot, hero_id, kills, deaths, assists, gpm, xpm, win) "
        "VALUES (?, ?, ?, 5, 2, 8, ?, 600, ?)",
        (match_id, slot, hero_id, gpm, int(win)),
    )


def _seed_item_slot(conn, match_id: int, slot: int, item_id: int, item_slot: int = 0) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO match_player_items (match_id, player_slot, slot, item_id) "
        "VALUES (?, ?, ?, ?)",
        (match_id, slot, item_slot, item_id),
    )


# ── POST /computed/rebuild ────────────────────────────────────────────────────

def test_rebuild_endpoint_returns_202_empty_db(client) -> None:
    resp = client.post("/computed/rebuild")
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "ok"
    assert data["hero_stats_rows"] == 0
    assert data["item_build_rows"] == 0


def test_rebuild_endpoint_returns_row_counts(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_item(conn, 10, "Blink Dagger")
        for i in range(1, 4):
            _seed_match(conn, i)
            _seed_mp(conn, i, 0, 1, win=(i <= 2))
            _seed_item_slot(conn, i, 0, 10)

    resp = client.post("/computed/rebuild")
    assert resp.status_code == 202
    data = resp.json()
    assert data["hero_stats_rows"] == 1
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
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_match(conn, 1)
        _seed_mp(conn, 1, 0, 1, win=True)

    client.post("/computed/rebuild")

    resp = client.get("/computed/staleness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["hero_stats_computed"] is not None
    assert data["hero_stats_computed"] > 0


# ── GET /computed/heroes/{hero_id}/stats ─────────────────────────────────────

def test_get_hero_stats_404_before_rebuild(client) -> None:
    resp = client.get("/computed/heroes/1/stats")
    assert resp.status_code == 404


def test_get_hero_stats_200_after_rebuild(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        for i in range(1, 6):
            _seed_match(conn, i)
            _seed_mp(conn, i, 0, 1, win=(i <= 3))

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    row = data[0]
    assert row["hero_id"] == 1
    assert row["hero_name"] == "Anti-Mage"
    assert row["matches_played"] == 5
    assert row["wins"] == 3
    assert row["losses"] == 2
    assert row["winrate"] == 0.6
    assert row["primary_pos"] == 1


def test_get_hero_stats_filter_by_patch(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_match(conn, 1, patch=38)
        _seed_match(conn, 2, patch=39)
        _seed_mp(conn, 1, 0, 1, win=True)
        _seed_mp(conn, 2, 0, 1, win=False)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/stats?patch=38")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["patch"] == 38
    assert data[0]["wins"] == 1


def test_get_hero_stats_avg_gpm_correct(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_match(conn, 1)
        _seed_match(conn, 2)
        _seed_mp(conn, 1, 0, 1, win=True,  gpm=400)
        _seed_mp(conn, 2, 0, 1, win=False, gpm=600)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/stats")
    assert resp.status_code == 200
    assert resp.json()[0]["avg_gpm"] == 500.0


# ── GET /computed/heroes/top ──────────────────────────────────────────────────

def test_get_top_heroes_empty_before_rebuild(client) -> None:
    resp = client.get("/computed/heroes/top?min_matches=1")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_top_heroes_sorted_by_winrate(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        # Anti-Mage carry: 3/5 = 0.6
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        for i in range(1, 6):
            _seed_match(conn, i)
            _seed_mp(conn, i, 0, 1, win=(i <= 3))
        # Axe offlane: 4/5 = 0.8
        _seed_hero(conn, 2, "Axe")
        _seed_role_score(conn, 2, 3)
        for i in range(10, 15):
            _seed_match(conn, i)
            _seed_mp(conn, i, 1, 2, win=(i <= 13))

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/top?min_matches=1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["hero_id"] == 2   # Axe: 0.8
    assert data[1]["hero_id"] == 1   # AM: 0.6


def test_get_top_heroes_filter_by_pos(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_hero(conn, 2, "Axe")
        _seed_role_score(conn, 2, 3)
        for hero_id, slot in [(1, 0), (2, 1)]:
            for i in range(1, 4):
                _seed_match(conn, i * 10 + hero_id)
                _seed_mp(conn, i * 10 + hero_id, slot, hero_id, win=True)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/top?primary_pos=1&min_matches=1")
    assert resp.status_code == 200
    data = resp.json()
    assert all(r["primary_pos"] == 1 for r in data)
    assert len(data) == 1
    assert data[0]["hero_id"] == 1


def test_get_top_heroes_min_matches_excludes(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_match(conn, 1)
        _seed_mp(conn, 1, 0, 1, win=True)

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
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_item(conn, 10, "Blink Dagger")
        for i in range(1, 4):
            _seed_match(conn, i)
            _seed_mp(conn, i, 0, 1, win=(i <= 2))
            _seed_item_slot(conn, i, 0, 10)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/items/1")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["item_id"] == 10
    assert data[0]["item_name"] == "Blink Dagger"
    assert data[0]["times_bought"] == 3
    assert data[0]["times_won"] == 2
    assert data[0]["win_rate"] == round(2 / 3, 4)


def test_get_hero_items_422_invalid_pos(client) -> None:
    resp = client.get("/computed/heroes/1/items/6")
    assert resp.status_code == 422


def test_get_hero_items_limit(client, db_conn) -> None:
    with _conn(db_conn) as conn:
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_match(conn, 1)
        _seed_mp(conn, 1, 0, 1, win=True)
        for item_id in range(1, 5):  # 4 items
            _seed_item(conn, item_id, f"item_{item_id}")
            _seed_item_slot(conn, 1, 0, item_id, item_slot=item_id - 1)

    client.post("/computed/rebuild")

    resp = client.get("/computed/heroes/1/items/1?limit=2")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── Full E2E flow ─────────────────────────────────────────────────────────────

def test_full_e2e_ingest_rebuild_api(client, db_conn) -> None:
    """Повний E2E: seed raw data → rebuild → GET endpoints → assert все правильно."""
    with _conn(db_conn) as conn:
        # Два герої
        _seed_hero(conn, 1, "Anti-Mage")
        _seed_role_score(conn, 1, 1)
        _seed_hero(conn, 2, "Crystal-Maiden")
        _seed_role_score(conn, 2, 5)

        # Items
        _seed_item(conn, 10, "Blink Dagger")
        _seed_item(conn, 11, "Force Staff")

        # 5 матчів: AM виграє 3, CM виграє 2
        for i in range(1, 6):
            am_win = i <= 3
            cm_win = i <= 2
            _seed_match(conn, i)
            _seed_mp(conn, i, 0, 1, win=am_win, gpm=500 + i * 10)
            _seed_mp(conn, i, 1, 2, win=cm_win, gpm=300 + i * 5)
            _seed_item_slot(conn, i, 0, 10)  # AM: Blink
            _seed_item_slot(conn, i, 1, 11)  # CM: Force Staff

    # Rebuild
    rebuild_resp = client.post("/computed/rebuild")
    assert rebuild_resp.status_code == 202
    assert rebuild_resp.json()["hero_stats_rows"] == 2
    assert rebuild_resp.json()["item_build_rows"] == 2

    # Staleness — обидві таблиці заповнені
    staleness = client.get("/computed/staleness").json()
    assert staleness["hero_stats_computed"] is not None

    # AM stats
    am_resp = client.get("/computed/heroes/1/stats")
    assert am_resp.status_code == 200
    am = am_resp.json()[0]
    assert am["matches_played"] == 5
    assert am["wins"] == 3
    assert am["winrate"] == 0.6

    # CM stats
    cm_resp = client.get("/computed/heroes/2/stats")
    assert cm_resp.status_code == 200
    cm = cm_resp.json()[0]
    assert cm["wins"] == 2
    assert cm["winrate"] == 0.4

    # Top heroes sorted by winrate
    top_resp = client.get("/computed/heroes/top?min_matches=1")
    assert top_resp.status_code == 200
    top = top_resp.json()
    assert top[0]["hero_id"] == 1  # AM: 0.6 > CM: 0.4

    # AM item build
    am_items = client.get("/computed/heroes/1/items/1").json()
    assert am_items[0]["item_id"] == 10
    assert am_items[0]["times_bought"] == 5
    assert am_items[0]["times_won"] == 3