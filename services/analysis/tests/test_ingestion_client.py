# services/analysis/tests/test_ingestion_client.py
"""
Тести для IngestionClient — всі HTTP запити замоковані через responses/monkeypatch.
Не робить реальних HTTP запитів.
"""
import pytest
import responses as resp_mock

from services.analysis.app.clients.ingestion import IngestionClient

BASE = "http://localhost:8000"


@pytest.fixture()
def client():
    return IngestionClient(base_url=BASE)


# ── get_hero_matchups ─────────────────────────────────────────────────────────

@resp_mock.activate
def test_get_hero_matchups_ok(client):
    resp_mock.add(
        resp_mock.GET,
        f"{BASE}/computed/heroes/1/matchups",
        json=[{"opponent_id": 2, "matches": 10, "winrate": 0.6}],
        status=200,
    )
    result = client.get_hero_matchups(1, limit=5)
    assert len(result) == 1
    assert result[0]["opponent_id"] == 2


@resp_mock.activate
def test_get_hero_matchups_empty(client):
    resp_mock.add(
        resp_mock.GET,
        f"{BASE}/computed/heroes/1/matchups",
        json=[],
        status=200,
    )
    assert client.get_hero_matchups(1) == []


@resp_mock.activate
def test_get_hero_matchups_unavailable_returns_empty(client):
    """503 після всіх retry → повертає [] (не падає)."""
    for _ in range(3):
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/computed/heroes/1/matchups",
            status=503,
        )
    result = client.get_hero_matchups(1)
    assert result == []


# ── get_hero_synergies ────────────────────────────────────────────────────────

@resp_mock.activate
def test_get_hero_synergies_ok(client):
    resp_mock.add(
        resp_mock.GET,
        f"{BASE}/computed/heroes/5/synergies",
        json=[{"ally_id": 10, "matches": 5, "winrate": 0.7}],
        status=200,
    )
    result = client.get_hero_synergies(5)
    assert result[0]["ally_id"] == 10


# ── get_hero_stats ────────────────────────────────────────────────────────────

@resp_mock.activate
def test_get_hero_stats_aggregate(client):
    """Повертає запис де patch=None і region=None."""
    resp_mock.add(
        resp_mock.GET,
        f"{BASE}/computed/heroes/1/stats",
        json=[
            {"patch": 59, "region": 3, "matches_played": 5, "avg_gpm": 400.0},
            {"patch": None, "region": None, "matches_played": 20, "avg_gpm": 450.0},
        ],
        status=200,
    )
    result = client.get_hero_stats(1)
    assert result is not None
    assert result["matches_played"] == 20


@resp_mock.activate
def test_get_hero_stats_none_if_empty(client):
    resp_mock.add(
        resp_mock.GET,
        f"{BASE}/computed/heroes/999/stats",
        json=[],
        status=200,
    )
    assert client.get_hero_stats(999) is None


@resp_mock.activate
def test_get_hero_stats_unavailable_returns_none(client):
    for _ in range(3):
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/computed/heroes/1/stats",
            status=500,
        )
    assert client.get_hero_stats(1) is None


# ── get_match_players ─────────────────────────────────────────────────────────

def test_get_match_players_returns_empty(client):
    """Поки endpoint не реалізований в Ingestion — повертає []."""
    result = client.get_match_players(8716150035)
    assert result == []
