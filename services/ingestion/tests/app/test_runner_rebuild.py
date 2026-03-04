# services/ingestion/tests/app/test_runner_rebuild.py
"""Тести для Epic 5.6 — AUTO_REBUILD_AFTER_INGEST scheduler."""
from unittest.mock import MagicMock, patch

from services.ingestion.app.runner import Runner
from services.ingestion.domains.discovery.dtos import DiscoveredMatch, DiscoveryFilter


class FakeDiscovery:
    def __init__(self, match_ids: list[int]) -> None:
        self._matches = [DiscoveredMatch(match_id=mid) for mid in match_ids]

    def discover(self, f: DiscoveryFilter) -> list[DiscoveredMatch]:
        return self._matches


def _make_runner(match_ids: list[int]) -> Runner:
    # interval_sec передаємо явно — не читаємо з settings (може бути замокований)
    return Runner(discovery_provider=FakeDiscovery(match_ids), interval_sec=300)


def _patch_deps(mock_ingest, mock_uow, mock_repo_cls, *, is_known: bool = False) -> None:
    mock_repo = MagicMock()
    mock_repo.is_known.return_value = is_known
    mock_repo_cls.return_value = mock_repo
    mock_uow.return_value.__enter__ = MagicMock(return_value=MagicMock(conn=MagicMock()))
    mock_uow.return_value.__exit__ = MagicMock(return_value=False)


# ── rebuild викликається ──────────────────────────────────────────────────────

@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
@patch("services.ingestion.app.runner.settings")
def test_rebuild_called_after_ingest(
    mock_settings: MagicMock,
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """AUTO_REBUILD_AFTER_INGEST=True + нові матчі → _run_rebuild викликається."""
    mock_settings.AUTO_REBUILD_AFTER_INGEST = True
    mock_settings.DISCOVERY_LOBBY_TYPE = 7
    mock_settings.DISCOVERY_MIN_RANK_TIER = 60
    mock_settings.DISCOVERY_LIMIT = 100
    mock_settings.DISCOVERY_PATCH = None
    mock_settings.DISCOVERY_REGION = None
    _patch_deps(mock_ingest, mock_uow, mock_repo_cls, is_known=False)

    runner = _make_runner([101, 102])

    with patch.object(runner, "_run_rebuild") as mock_rebuild:
        stats = runner.run_cycle()
        mock_rebuild.assert_called_once_with(stats)


# ── rebuild не викликається якщо немає нових матчів ──────────────────────────

@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
@patch("services.ingestion.app.runner.settings")
def test_rebuild_not_called_when_no_new_matches(
    mock_settings: MagicMock,
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """Всі матчі known (ingested=0) → rebuild не запускається."""
    mock_settings.AUTO_REBUILD_AFTER_INGEST = True
    mock_settings.DISCOVERY_LOBBY_TYPE = 7
    mock_settings.DISCOVERY_MIN_RANK_TIER = 60
    mock_settings.DISCOVERY_LIMIT = 100
    mock_settings.DISCOVERY_PATCH = None
    mock_settings.DISCOVERY_REGION = None
    _patch_deps(mock_ingest, mock_uow, mock_repo_cls, is_known=True)

    runner = _make_runner([101, 102])
    stats = runner.run_cycle()

    assert stats.ingested == 0
    assert stats.rebuild_hero_stats_rows is None
    assert stats.rebuild_item_build_rows is None


# ── rebuild вимкнений через config ───────────────────────────────────────────

@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
@patch("services.ingestion.app.runner.settings")
def test_rebuild_not_called_when_disabled(
    mock_settings: MagicMock,
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """AUTO_REBUILD_AFTER_INGEST=False → rebuild не запускається навіть при нових матчах."""
    mock_settings.AUTO_REBUILD_AFTER_INGEST = False
    mock_settings.DISCOVERY_LOBBY_TYPE = 7
    mock_settings.DISCOVERY_MIN_RANK_TIER = 60
    mock_settings.DISCOVERY_LIMIT = 100
    mock_settings.DISCOVERY_PATCH = None
    mock_settings.DISCOVERY_REGION = None
    _patch_deps(mock_ingest, mock_uow, mock_repo_cls, is_known=False)

    runner = _make_runner([101])
    stats = runner.run_cycle()

    assert stats.ingested == 1
    assert stats.rebuild_hero_stats_rows is None
    assert stats.rebuild_item_build_rows is None


# ── помилка rebuild не зупиняє цикл ──────────────────────────────────────────

@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
@patch("services.ingestion.app.runner.settings")
def test_rebuild_failure_does_not_raise(
    mock_settings: MagicMock,
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """Помилка в _run_rebuild не пробивається назовні — runner не падає."""
    mock_settings.AUTO_REBUILD_AFTER_INGEST = True
    mock_settings.DISCOVERY_LOBBY_TYPE = 7
    mock_settings.DISCOVERY_MIN_RANK_TIER = 60
    mock_settings.DISCOVERY_LIMIT = 100
    mock_settings.DISCOVERY_PATCH = None
    mock_settings.DISCOVERY_REGION = None
    _patch_deps(mock_ingest, mock_uow, mock_repo_cls, is_known=False)

    runner = _make_runner([101])

    # Мокуємо внутрішній lazy import rebuild щоб кинути помилку
    with patch(
        "services.ingestion.app.rebuild_hero_stats.rebuild_hero_stats",
        side_effect=RuntimeError("DB locked"),
    ):
        # run_cycle не повинен кинути — помилка ловиться в _run_rebuild
        stats = runner.run_cycle()

    # ingested відбувся, rebuild провалився але не зупинив цикл
    assert stats.ingested == 1


# ── CycleStats містить rebuild counts ────────────────────────────────────────

@patch("services.ingestion.app.runner.IngestionLogRepository")
@patch("services.ingestion.app.runner.UnitOfWork")
@patch("services.ingestion.app.runner.ingest_match")
@patch("services.ingestion.app.runner.settings")
def test_cycle_stats_include_rebuild_counts(
    mock_settings: MagicMock,
    mock_ingest: MagicMock,
    mock_uow: MagicMock,
    mock_repo_cls: MagicMock,
) -> None:
    """CycleStats.rebuild_hero_stats_rows і rebuild_item_build_rows заповнені після rebuild."""
    mock_settings.AUTO_REBUILD_AFTER_INGEST = True
    mock_settings.DISCOVERY_LOBBY_TYPE = 7
    mock_settings.DISCOVERY_MIN_RANK_TIER = 60
    mock_settings.DISCOVERY_LIMIT = 100
    mock_settings.DISCOVERY_PATCH = None
    mock_settings.DISCOVERY_REGION = None
    _patch_deps(mock_ingest, mock_uow, mock_repo_cls, is_known=False)

    runner = _make_runner([101])

    with patch.object(runner, "_run_rebuild") as mock_rebuild:
        def _fake_rebuild(stats):
            stats.rebuild_hero_stats_rows = 10
            stats.rebuild_item_build_rows = 7

        mock_rebuild.side_effect = _fake_rebuild
        stats = runner.run_cycle()

    assert stats.rebuild_hero_stats_rows == 10
    assert stats.rebuild_item_build_rows == 7
    assert stats.ingested == 1
