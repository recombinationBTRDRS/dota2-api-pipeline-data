# services/analysis/tests/test_teamfight_analyzer.py
import pytest

from services.analysis.app.analyzers.teamfight import TeamfightAnalyzer


def _p(is_radiant: bool, kills: int, deaths: int, assists: int) -> dict:
    return {"is_radiant": is_radiant, "kills": kills, "deaths": deaths, "assists": assists}


def test_radiant_dominant():
    players = [
        _p(True,  10, 1, 5), _p(True,  8, 2, 4), _p(True,  6, 1, 3),
        _p(True,   4, 2, 2), _p(True,  3, 1, 1),
        _p(False,  2, 5, 1), _p(False, 1, 6, 0), _p(False, 2, 4, 1),
        _p(False,  1, 5, 0), _p(False, 1, 5, 1),
    ]
    snap = TeamfightAnalyzer().analyze(players)
    assert snap.teamfight_verdict == "radiant_dominant"
    assert snap.radiant_kills == 31
    assert snap.kill_ratio > 0.6


def test_dire_dominant():
    players = [
        _p(True,  2, 8, 1), _p(True,  1, 7, 0), _p(True,  1, 6, 1),
        _p(True,   1, 5, 0), _p(True,  2, 6, 0),
        _p(False, 10, 1, 5), _p(False, 8, 2, 4), _p(False, 7, 1, 3),
        _p(False,  6, 1, 2), _p(False, 5, 2, 2),
    ]
    snap = TeamfightAnalyzer().analyze(players)
    assert snap.teamfight_verdict == "dire_dominant"
    assert snap.kill_ratio < 0.4


def test_contested():
    players = [
        _p(True,  5, 4, 3), _p(True,  4, 3, 2), _p(True,  3, 3, 2),
        _p(True,   3, 4, 1), _p(True,  2, 3, 2),
        _p(False,  4, 3, 3), _p(False, 3, 4, 2), _p(False, 4, 3, 1),
        _p(False,  3, 3, 2), _p(False, 3, 3, 2),
    ]
    snap = TeamfightAnalyzer().analyze(players)
    assert snap.teamfight_verdict == "contested"
    assert 0.4 <= snap.kill_ratio <= 0.6


def test_zero_kills():
    """kills=0 для всіх → kill_ratio=0.5, verdict=contested, не падає."""
    players = [_p(True, 0, 0, 0)] * 5 + [_p(False, 0, 0, 0)] * 5
    snap = TeamfightAnalyzer().analyze(players)
    assert snap.kill_ratio == 0.5
    assert snap.teamfight_verdict == "contested"
    assert snap.radiant_kills == 0
    assert snap.dire_kills == 0


def test_empty_players():
    snap = TeamfightAnalyzer().analyze([])
    assert snap.radiant_kills == 0
    assert snap.teamfight_verdict == "contested"


def test_kda_calculation():
    """KDA = (kills + assists) / max(deaths, 1)."""
    players = [_p(True, 10, 2, 5)]   # kda = (10+5)/2 = 7.5
    snap = TeamfightAnalyzer().analyze(players + [_p(False, 0, 0, 0)])
    assert snap.radiant_avg_kda == pytest.approx(7.5)
