# services/ingestion/tests/app/test_runner.py
"""Unit-тести для Runner.

Всі провайдери і ingest_match замінені на fake/mock — без HTTP і без реальної БД.
"""
from unittest.mock import MagicMock, patch

from services.ingestion.app.runner import Runner
from services.ingestion.domains.discovery.dtos import DiscoveredMatch, DiscoveryFilter

# ── Fake провайдери ──────────────────────────────────────────────────────────


class FakeDiscovery:
    """Повертає фіксований список match_id без HTTP."""

    def __init__(self, match_ids: list[int]) -> None:
        self._matches = [DiscoveredMatch(match_id=mid) for mid in match_ids]

    def discover(self, f: DiscoveryFilter) -> list[DiscoveredMatch]:
        return self._matches


class FakeDiscoveryError:
    """Кидає виняток при discovery."""

    def discover(self, f: DiscoveryFilter) -> list[DiscoveredMatch]:
        raise RuntimeError("Explorer API is down")


# ── run_cycle тести ──────────────────────────────────────────────────────────


@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
def test_cycle_ingests_new_matches(
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """Нові матчі (is_known=False) — інжестяться і позначаються 'ok'."""
    mock_repo = MagicMock()
    mock_repo.is_known.return_value = False
    mock_repo_cls.return_value = mock_repo
    mock_uow.return_value.__enter__ = MagicMock(return_value=MagicMock(conn=MagicMock()))
    mock_uow.return_value.__exit__ = MagicMock(return_value=False)

    runner = Runner(discovery_provider=FakeDiscovery([101, 102]))
    stats = runner.run_cycle()

    assert stats.discovered == 2
    assert stats.ingested == 2
    assert stats.skipped == 0
    assert stats.failed == 0
    assert mock_ingest.call_count == 2


@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
def test_cycle_skips_known_matches(
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """Відомі матчі (is_known=True) — пропускаються без інжесту."""
    mock_repo = MagicMock()
    mock_repo.is_known.return_value = True
    mock_repo_cls.return_value = mock_repo
    mock_uow.return_value.__enter__ = MagicMock(return_value=MagicMock(conn=MagicMock()))
    mock_uow.return_value.__exit__ = MagicMock(return_value=False)

    runner = Runner(discovery_provider=FakeDiscovery([101, 102]))
    stats = runner.run_cycle()

    assert stats.skipped == 2
    assert stats.ingested == 0
    mock_ingest.assert_not_called()


@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
def test_cycle_continues_after_single_failure(
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """Помилка на одному матчі не зупиняє цикл — інші обробляються."""
    mock_repo = MagicMock()
    mock_repo.is_known.return_value = False
    mock_repo_cls.return_value = mock_repo
    mock_uow.return_value.__enter__ = MagicMock(return_value=MagicMock(conn=MagicMock()))
    mock_uow.return_value.__exit__ = MagicMock(return_value=False)

    mock_ingest.side_effect = [RuntimeError("timeout"), None]

    runner = Runner(discovery_provider=FakeDiscovery([201, 202]))
    stats = runner.run_cycle()

    assert stats.ingested == 1
    assert stats.failed == 1
    assert stats.errors[0][0] == 201
    assert "timeout" in stats.errors[0][1]


@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
def test_cycle_marks_failed_on_error(
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """При помилці інжесту — mark_failed викликається з match_id і текстом."""
    mock_repo = MagicMock()
    mock_repo.is_known.return_value = False
    mock_repo_cls.return_value = mock_repo
    mock_uow.return_value.__enter__ = MagicMock(return_value=MagicMock(conn=MagicMock()))
    mock_uow.return_value.__exit__ = MagicMock(return_value=False)

    mock_ingest.side_effect = RuntimeError("api error")

    runner = Runner(discovery_provider=FakeDiscovery([301]))
    runner.run_cycle()

    mock_repo.mark_failed.assert_called_once()
    call_kwargs = mock_repo.mark_failed.call_args
    assert call_kwargs.kwargs["match_id"] == 301
    assert "api error" in call_kwargs.kwargs["error"]


@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
def test_cycle_empty_discovery(
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """Порожній результат discovery — нічого не інжестується."""
    mock_uow.return_value.__enter__ = MagicMock(return_value=MagicMock(conn=MagicMock()))
    mock_uow.return_value.__exit__ = MagicMock(return_value=False)

    runner = Runner(discovery_provider=FakeDiscovery([]))
    stats = runner.run_cycle()

    assert stats.discovered == 0
    assert stats.ingested == 0
    mock_ingest.assert_not_called()


# ── stop / graceful shutdown ─────────────────────────────────────────────────


def test_stop_sets_running_false() -> None:
    """stop() виставляє _running=False."""
    runner = Runner(discovery_provider=FakeDiscovery([]))
    runner._running = True
    runner.stop()
    assert runner._running is False