# services/ingestion/app/runner.py
import logging
import signal
import time
from dataclasses import asdict, dataclass, field

from services.ingestion.app.config import settings
from services.ingestion.app.ingest_match import ingest_match
from services.ingestion.app.state import app_state
from services.ingestion.db.repositories import IngestionLogRepository
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.discovery.dtos import DiscoveryFilter
from services.ingestion.providers.opendota.client import MatchProvider
from services.ingestion.providers.opendota.explorer_client import (
    DiscoveryProvider,
    OpenDotaExplorerClient,
)

logger = logging.getLogger(__name__)

_MIN_INTERVAL_SEC = 10


@dataclass
class CycleStats:
    """Статистика одного циклу discovery + ingest."""

    discovered: int = 0
    skipped: int = 0
    ingested: int = 0
    failed: int = 0
    errors: list[tuple[int, str]] = field(default_factory=list)

    # Epic 5.6 — rebuild stats (None якщо AUTO_REBUILD_AFTER_INGEST=False)
    rebuild_hero_stats_rows: int | None = None
    rebuild_item_build_rows: int | None = None


class Runner:
    """Discovery + Ingest runner з deduplication і graceful shutdown."""

    def __init__(
        self,
        discovery_provider: DiscoveryProvider | None = None,
        match_provider: MatchProvider | None = None,
        interval_sec: int | None = None,
    ) -> None:
        self._discovery = discovery_provider or OpenDotaExplorerClient()
        self._match_provider = match_provider

        raw_interval = interval_sec if interval_sec is not None else settings.DISCOVERY_INTERVAL_SEC
        if raw_interval <= 0:
            logger.warning(
                "interval_sec=%s is invalid, falling back to minimum %s",
                raw_interval, _MIN_INTERVAL_SEC,
            )
            raw_interval = _MIN_INTERVAL_SEC
        self._interval = raw_interval
        self._running = False

    def _build_filter(self) -> DiscoveryFilter:
        return DiscoveryFilter(
            lobby_type=settings.DISCOVERY_LOBBY_TYPE,
            min_mmr=settings.DISCOVERY_MIN_MMR,
            limit=settings.DISCOVERY_LIMIT,
            patch=settings.DISCOVERY_PATCH,
            region=settings.DISCOVERY_REGION,
        )

    def _is_known(self, match_id: int) -> bool:
        with UnitOfWork() as uow:
            return IngestionLogRepository(uow.conn).is_known(match_id)

    def _mark_ok(self, match_id: int) -> None:
        with UnitOfWork() as uow:
            IngestionLogRepository(uow.conn).mark_ok(
                match_id=match_id, ingested_at=int(time.time()),
            )

    def _mark_failed(self, match_id: int, error: str) -> None:
        with UnitOfWork() as uow:
            IngestionLogRepository(uow.conn).mark_failed(
                match_id=match_id, ingested_at=int(time.time()), error=error,
            )

    def _run_rebuild(self, stats: CycleStats) -> None:
        """Запускає rebuild pre-computed таблиць якщо AUTO_REBUILD_AFTER_INGEST=True.

        Помилка rebuild не зупиняє runner — логується як WARNING.
        Rebuild не запускається якщо в циклі не було нових матчів (ingested == 0).
        """
        if not settings.AUTO_REBUILD_AFTER_INGEST:
            return

        if stats.ingested == 0:
            logger.debug("Skipping rebuild — no new matches ingested this cycle")
            return

        try:
            from services.ingestion.app.rebuild_hero_stats import rebuild_hero_stats
            from services.ingestion.app.rebuild_item_builds import rebuild_item_builds

            hero_rows = rebuild_hero_stats()
            item_rows = rebuild_item_builds()

            stats.rebuild_hero_stats_rows = hero_rows
            stats.rebuild_item_build_rows = item_rows

            logger.info(
                "Rebuild done: hero_stats=%s rows, item_builds=%s rows",
                hero_rows, item_rows,
            )
        except Exception:
            logger.warning("Rebuild failed — pre-computed tables may be stale", exc_info=True)

    def run_cycle(self) -> CycleStats:
        """Виконує один цикл discovery + ingest + (optional) rebuild."""
        stats = CycleStats()

        discovered = self._discovery.discover(self._build_filter())
        stats.discovered = len(discovered)

        for dm in discovered:
            match_id = dm.match_id

            if self._is_known(match_id):
                stats.skipped += 1
                logger.debug("Skipping known match_id=%s", match_id)
                continue

            try:
                ingest_match(match_id=match_id, provider=self._match_provider)
                self._mark_ok(match_id)
                stats.ingested += 1
            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                self._mark_failed(match_id, error_msg)
                stats.failed += 1
                stats.errors.append((match_id, error_msg))
                logger.error("Ingest failed match_id=%s error=%s", match_id, error_msg)

        logger.info(
            "Cycle done: discovered=%s skipped=%s ingested=%s failed=%s",
            stats.discovered, stats.skipped, stats.ingested, stats.failed,
        )

        # Epic 5.6 — rebuild після інжесту якщо є нові матчі
        self._run_rebuild(stats)

        app_state.last_cycle_at = int(time.time())
        app_state.last_cycle_stats = asdict(stats)

        return stats

    def start(self) -> None:
        """Запускає нескінченний цикл з паузою між ітераціями."""
        self._running = True
        self._setup_signal_handlers()
        logger.info("Runner started, interval=%ss", self._interval)

        while self._running:
            try:
                self.run_cycle()
            except Exception:
                logger.exception("Unexpected error in run_cycle, continuing")

            if self._running:
                logger.info("Sleeping %ss until next cycle", self._interval)
                self._interruptible_sleep(self._interval)

        logger.info("Runner stopped")

    def stop(self) -> None:
        logger.info("Stop requested, finishing current cycle...")
        self._running = False

    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame: object) -> None:
        logger.info("Received signal %s, stopping after current cycle", signum)
        self.stop()

    def _interruptible_sleep(self, seconds: int) -> None:
        deadline = time.time() + seconds
        while self._running:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            time.sleep(min(1.0, remaining))