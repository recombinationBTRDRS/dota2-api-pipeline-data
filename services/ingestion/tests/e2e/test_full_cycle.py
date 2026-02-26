# services/ingestion/tests/e2e/test_full_cycle.py
"""E2E тести повного циклу: discovery → dedup → ingest → DB.

Без реального HTTP — використовує FakeExplorer і FakeMatchProvider.
Кожен тест має власну tmp SQLite БД через fixture.
"""
import sqlite3
from contextlib import contextmanager
from typing import Any, Generator

import pytest

from services.ingestion.app.runner import Runner
from services.ingestion.db import sqlite as sqlite_module
from services.ingestion.db.sqlite import get_connection, init_db
from services.ingestion.domains.discovery.dtos import DiscoveredMatch, DiscoveryFilter

# ── Fake провайдери ──────────────────────────────────────────────────────────


class FakeExplorer:
    """Повертає фіксований список match_id без HTTP."""

    def __init__(self, match_ids: list[int]) -> None:
        self._matches = [DiscoveredMatch(match_id=mid) for mid in match_ids]

    def discover(self, f: DiscoveryFilter) -> list[DiscoveredMatch]:
        return self._matches


class FakeMatchProvider:
    """Повертає синтетичний raw match dict без HTTP."""

    def __init__(self, fail_ids: set[int] | None = None) -> None:
        # fail_ids — match_id для яких симулюємо помилку
        self._fail_ids = fail_ids or set()

    def get_match(self, match_id: int) -> dict[str, Any]:
        if match_id in self._fail_ids:
            raise RuntimeError(f"Simulated failure for match_id={match_id}")
        return {
            "match_id": match_id,
            "duration": 1800,
            "radiant_win": True,
            "start_time": 1700000000,
            "radiant_score": 20,
            "dire_score": 15,
            "players": [
                {
                    "account_id": match_id * 10,  # унікальний per match
                    "hero_id": 1,
                    "kills": 5,
                    "deaths": 2,
                    "assists": 8,
                    "gpm": 500,
                    "xpm": 600,
                    "isRadiant": True,
                    "win": 1,
                }
            ],
        }


# ── Fixtures ─────────────────────────────────────────────────────────────────


@contextmanager
def db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Контекстний менеджер що гарантує закриття з'єднання."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def db(monkeypatch, tmp_path):
    """Тимчасова SQLite БД для одного тесту."""
    db_path = tmp_path / "e2e.sqlite"
    monkeypatch.setattr(sqlite_module, "DB_PATH", db_path)
    init_db()
    return db_path


def make_runner(match_ids: list[int], fail_ids: set[int] | None = None) -> Runner:
    """Фабрика Runner з fake провайдерами."""
    return Runner(
        discovery_provider=FakeExplorer(match_ids),
        match_provider=FakeMatchProvider(fail_ids=fail_ids),
    )


# ── Smoke тест ───────────────────────────────────────────────────────────────


def test_full_cycle_two_matches_saved(db) -> None:
    """FakeExplorer → 2 match_id → обидва інжестуються і зберігаються в DB."""
    runner = make_runner([1001, 1002])
    stats = runner.run_cycle()

    assert stats.discovered == 2
    assert stats.ingested == 2
    assert stats.skipped == 0
    assert stats.failed == 0

    with db_conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM ingestion_log WHERE status='ok'").fetchone()[0] == 2


# ── Dedup тест ───────────────────────────────────────────────────────────────


def test_second_cycle_skips_known_matches(db) -> None:
    """Другий запуск runner — 0 нових інжестів, всі матчі skipped."""
    runner = make_runner([2001, 2002])

    first = runner.run_cycle()
    assert first.ingested == 2

    second = runner.run_cycle()
    assert second.discovered == 2
    assert second.skipped == 2
    assert second.ingested == 0

    with db_conn() as conn:
        assert conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 2


# ── Failure тест ─────────────────────────────────────────────────────────────


def test_failed_match_logged_others_saved(db) -> None:
    """match_id=3002 падає → 3001 збережено, 3002 має status='failed'."""
    runner = make_runner([3001, 3002], fail_ids={3002})
    stats = runner.run_cycle()

    assert stats.ingested == 1
    assert stats.failed == 1
    assert stats.errors[0][0] == 3002
    assert "Simulated failure" in stats.errors[0][1]

    with db_conn() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM matches WHERE id=3001"
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM matches WHERE id=3002"
        ).fetchone()[0] == 0
        assert conn.execute(
            "SELECT status FROM ingestion_log WHERE match_id=3002"
        ).fetchone()[0] == "failed"


def test_failed_match_retried_on_next_cycle(db) -> None:
    """Failed матч ретрається при наступному циклі якщо провайдер відновився."""
    # Перший цикл — 4001 падає
    runner = make_runner([4001], fail_ids={4001})
    first = runner.run_cycle()
    assert first.failed == 1

    # Другий цикл — 4001 вже без помилки (новий runner без fail_ids)
    runner2 = make_runner([4001])
    second = runner2.run_cycle()
    assert second.ingested == 1
    assert second.skipped == 0

    with db_conn() as conn:
        assert conn.execute(
            "SELECT status FROM ingestion_log WHERE match_id=4001"
        ).fetchone()[0] == "ok"


# ── ingestion_log integrity ───────────────────────────────────────────────────


def test_ingestion_log_records_all_outcomes(db) -> None:
    """ingestion_log має записи для всіх матчів з коректними статусами."""
    runner = make_runner([5001, 5002, 5003], fail_ids={5003})
    runner.run_cycle()

    with db_conn() as conn:
        ok_count = conn.execute(
            "SELECT COUNT(*) FROM ingestion_log WHERE status='ok'"
        ).fetchone()[0]
        fail_count = conn.execute(
            "SELECT COUNT(*) FROM ingestion_log WHERE status='failed'"
        ).fetchone()[0]

    assert ok_count == 2
    assert fail_count == 1