# services/analysis/tests/test_draft_analyzer.py
from unittest.mock import MagicMock

from services.analysis.app.analyzers.draft import DraftAnalyzer
from services.analysis.app.clients.ingestion import IngestionClient

RADIANT = [1, 2, 3, 4, 5]
DIRE    = [6, 7, 8, 9, 10]


def _make_client(synergies: dict[int, list], matchups: dict[int, list]) -> IngestionClient:
    """Фабрика мок-клієнта з заданими даними."""
    client = MagicMock(spec=IngestionClient)
    client.get_hero_synergies.side_effect = lambda hero_id, limit=20: synergies.get(hero_id, [])
    client.get_hero_matchups.side_effect  = lambda hero_id, limit=20: matchups.get(hero_id, [])
    return client


# ── full data ─────────────────────────────────────────────────────────────────

def test_full_data_gives_good_quality():
    """Усі пари знайдені → data_quality='good', overall не None."""
    synergies = {
        h: [{"ally_id": a, "winrate": 0.55, "matches": 20} for a in RADIANT if a != h]
        for h in RADIANT
    }
    matchups = {
        h: [{"opponent_id": e, "winrate": 0.52, "matches": 15} for e in DIRE]
        for h in RADIANT
    }
    client = _make_client(synergies, matchups)
    score = DraftAnalyzer(client).analyze(RADIANT, DIRE)

    assert score.data_quality == "good"
    assert score.overall is not None
    assert score.synergy_score is not None
    assert score.counter_score is not None
    assert len(score.top_synergies) <= 3
    assert len(score.top_counters) <= 3


def test_overall_formula():
    """overall = 0.4 * synergy + 0.6 * counter."""
    synergies = {
        h: [{"ally_id": a, "winrate": 0.60, "matches": 10} for a in RADIANT if a != h]
        for h in RADIANT
    }
    matchups = {
        h: [{"opponent_id": e, "winrate": 0.50, "matches": 10} for e in DIRE]
        for h in RADIANT
    }
    client = _make_client(synergies, matchups)
    score = DraftAnalyzer(client).analyze(RADIANT, DIRE)

    expected = round(0.4 * score.synergy_score + 0.6 * score.counter_score, 4)
    assert score.overall == expected


# ── partial data ──────────────────────────────────────────────────────────────

def test_partial_data_limited_quality():
    """Частина пар знайдена (25–45%) → 'limited'."""
    # Тільки 2 з 5 героїв мають synergy, решта порожньо
    synergies = {
        1: [{"ally_id": 2, "winrate": 0.54, "matches": 8}],
        2: [{"ally_id": 1, "winrate": 0.54, "matches": 8}],
    }
    matchups = {
        1: [{"opponent_id": 6, "winrate": 0.50, "matches": 10},
            {"opponent_id": 7, "winrate": 0.48, "matches": 10}],
        2: [{"opponent_id": 8, "winrate": 0.51, "matches": 10}],
    }
    client = _make_client(synergies, matchups)
    score = DraftAnalyzer(client).analyze(RADIANT, DIRE)

    assert score.data_quality in ("limited", "insufficient")


# ── no data ───────────────────────────────────────────────────────────────────

def test_no_data_insufficient():
    """Клієнт повертає порожні списки → insufficient, all None."""
    client = _make_client({}, {})
    score = DraftAnalyzer(client).analyze(RADIANT, DIRE)

    assert score.data_quality == "insufficient"
    assert score.synergy_score is None
    assert score.counter_score is None
    assert score.overall is None


def test_empty_heroes_insufficient():
    """Порожні списки героїв → insufficient."""
    client = _make_client({}, {})
    score = DraftAnalyzer(client).analyze([], [])
    assert score.data_quality == "insufficient"


# ── edge cases ────────────────────────────────────────────────────────────────

def test_hero_missing_in_synergy_skipped():
    """Якщо пара не знайдена — не падає, просто пропускаємо."""
    synergies = {1: [{"ally_id": 99, "winrate": 0.6, "matches": 5}]}  # 99 не в RADIANT
    matchups  = {}
    client = _make_client(synergies, matchups)
    score = DraftAnalyzer(client).analyze(RADIANT, DIRE)
    assert score is not None  # не впало

def test_only_counter_score_if_no_synergy():
    """Якщо synergy порожня але matchup є → overall = counter_score."""
    matchups = {
        h: [{"opponent_id": e, "winrate": 0.55, "matches": 10} for e in DIRE]
        for h in RADIANT
    }
    client = _make_client({}, matchups)
    score = DraftAnalyzer(client).analyze(RADIANT, DIRE)

    assert score.synergy_score is None
    assert score.counter_score is not None
    assert score.overall == score.counter_score
