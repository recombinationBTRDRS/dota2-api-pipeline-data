# services/analysis/tests/test_economy_analyzer.py
from unittest.mock import MagicMock

import pytest

from services.analysis.app.analyzers.economy import EconomyAnalyzer
from services.analysis.app.clients.ingestion import IngestionClient


def _client(stats_map: dict[int, dict | None]) -> IngestionClient:
    c = MagicMock(spec=IngestionClient)
    c.get_hero_stats.side_effect = lambda hero_id, **kw: stats_map.get(hero_id)
    return c


def _player(hero_id: int, is_radiant: bool, gpm: int, net_worth: int | None = None) -> dict:
    return {
        "hero_id": hero_id,
        "is_radiant": is_radiant,
        "gold_per_min": gpm,
        "net_worth": net_worth,
    }


PLAYERS_5V5 = [
    _player(1, True,  500, 12000),
    _player(2, True,  450, 10000),
    _player(3, True,  400,  9000),
    _player(4, True,  380,  8500),
    _player(5, True,  360,  8000),
    _player(6, False, 420, 11000),
    _player(7, False, 390, 10500),
    _player(8, False, 350,  9500),
    _player(9, False, 330,  8800),
    _player(10,False, 310,  8200),
]


# ── basic ─────────────────────────────────────────────────────────────────────

def test_returns_10_players():
    stats = {i: {"avg_gpm": 420.0} for i in range(1, 11)}
    snap = EconomyAnalyzer(_client(stats)).analyze(PLAYERS_5V5)
    assert len(snap.players) == 10


def test_radiant_dire_split():
    stats = {i: {"avg_gpm": 420.0} for i in range(1, 11)}
    snap = EconomyAnalyzer(_client(stats)).analyze(PLAYERS_5V5)
    radiant = [p for p in snap.players if p.is_radiant]
    dire    = [p for p in snap.players if not p.is_radiant]
    assert len(radiant) == 5
    assert len(dire) == 5


# ── gpm rating ────────────────────────────────────────────────────────────────

def test_above_average_rating():
    """GPM 600 vs avg 400 → +50% → above_average."""
    stats = {1: {"avg_gpm": 400.0}}
    snap = EconomyAnalyzer(_client(stats)).analyze([_player(1, True, 600)])
    assert snap.players[0].gpm_rating == "above_average"
    assert snap.players[0].gpm_delta == pytest.approx(200.0)


def test_below_average_rating():
    """GPM 250 vs avg 400 → -37.5% → below_average."""
    stats = {1: {"avg_gpm": 400.0}}
    snap = EconomyAnalyzer(_client(stats)).analyze([_player(1, True, 250)])
    assert snap.players[0].gpm_rating == "below_average"


def test_average_rating():
    """GPM 410 vs avg 400 → +2.5% → average."""
    stats = {1: {"avg_gpm": 400.0}}
    snap = EconomyAnalyzer(_client(stats)).analyze([_player(1, True, 410)])
    assert snap.players[0].gpm_rating == "average"


def test_unknown_rating_if_no_stats():
    """Герой не знайдений в stats → gpm_rating='unknown', gpm_delta=None."""
    snap = EconomyAnalyzer(_client({})).analyze([_player(999, True, 500)])
    assert snap.players[0].gpm_rating == "unknown"
    assert snap.players[0].gpm_delta is None


# ── networth advantage ────────────────────────────────────────────────────────

def test_radiant_advantage():
    """Radiant сумарний net_worth значно більший → 'radiant'."""
    players = [
        _player(1, True,  500, 30000),
        _player(2, False, 400, 10000),
    ]
    snap = EconomyAnalyzer(_client({})).analyze(players)
    assert snap.networth_advantage == "radiant"


def test_dire_advantage():
    players = [
        _player(1, True,  400, 10000),
        _player(2, False, 500, 30000),
    ]
    snap = EconomyAnalyzer(_client({})).analyze(players)
    assert snap.networth_advantage == "dire"


def test_even_advantage():
    players = [
        _player(1, True,  500, 20000),
        _player(2, False, 500, 20000),
    ]
    snap = EconomyAnalyzer(_client({})).analyze(players)
    assert snap.networth_advantage == "even"


# ── fallback to GPM if no net_worth ──────────────────────────────────────────

def test_gpm_advantage_fallback():
    """net_worth=None → fallback на GPM для advantage."""
    players = [
        _player(1, True,  600, None),
        _player(2, False, 300, None),
    ]
    snap = EconomyAnalyzer(_client({})).analyze(players)
    assert snap.networth_advantage == "radiant"


# ── empty ─────────────────────────────────────────────────────────────────────

def test_empty_players():
    snap = EconomyAnalyzer(_client({})).analyze([])
    assert snap.players == []
    assert snap.networth_advantage == "even"
