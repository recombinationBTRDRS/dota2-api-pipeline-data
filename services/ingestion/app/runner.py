# services/ingestion/app/runner.py
"""Match Discovery Runner (Task 2.2).

Основний цикл: discover → filter known → ingest each → log result.

Запуск:
    python -m services.ingestion.app.runner
    python -m services.ingestion.app.runner --interval 60
"""
import logging
import signal
import time
from dataclasses import dataclass, field

from services.ingestion.app.config import settings
from services.ingestion.app.ingest_match import ingest_match
from services.ingestion.db.repositories import IngestionLogRepository
from services.ingestion.db.unit_of_work import UnitOfWork
from services.ingestion.domains.discovery.dtos import DiscoveryFilter
from services.ingestion.providers.opendota.client import MatchProvider
from services.ingestion.providers.opendota.explorer_client import (
    DiscoveryProvider,
    OpenDotaExplorerClient,
)

logger = logging.getLogger(__name__)


@dataclass
class CycleStats:
    """Статистика одного циклу discovery + ingest."""

    discovered: int = 0
    skipped: int = 0
    ingested: int = 0
    failed: int = 0
    errors: list[tuple[int, str]] = field(default_factory=list)


class Runner:
    """Discovery + Ingest runner з deduplication і graceful shutdown.

    Підтримує підміну провайдерів через конструктор — для тестів
    передай FakeDiscoveryProvider і FakeMatchProvider.

    Args:
        discovery_provider: провайдер для пошуку match_id.
        match_provider: провайдер для завантаження матчів.
        interval_sec: пауза між циклами в секундах.
    """

    def __init__(
        self,
        discovery_provider: DiscoveryProvider | None = None,
        match_provider: MatchProvider | None = None,
        interval_sec: int | None = None,
    ) -> None:
        self._discovery = discovery_provider or OpenDotaExplorerClient()
        self._match_provider = match_provider
        self._interval = interval_sec if interval_sec is not None else settings.DISCOVERY_INTERVAL_SEC
        self._running = False

    def _build_filter(self) -> DiscoveryFilter:
        """Будує DiscoveryFilter з поточних settings."""
        return DiscoveryFilter(
            lobby_type=settings.DISCOVERY_LOBBY_TYPE,
            min_mmr=settings.DISCOVERY_MIN_MMR,
            limit=settings.DISCOVERY_LIMIT,
            patch=settings.DISCOVERY_PATCH,
            region=settings.DISCOVERY_REGION,
        )

    def _is_known(self, match_id: int) -> bool:
        """Перевіряє чи матч вже успішно збережено."""
        with UnitOfWork() as uow:
            return IngestionLogRepository(uow.conn).is_known(match_id)

    def _mark_ok(self, match_id: int) -> None:
        """Записує успішний інжест в журнал."""
        with UnitOfWork() as uow:
            IngestionLogRepository(uow.conn).mark_ok(
                match_id=match_id,
                ingested_at=int(time.time()),
            )

    def _mark_failed(self, match_id: int, error: str) -> None:
        """Записує невдалий інжест в журнал."""
        with UnitOfWork() as uow:
            IngestionLogRepository(uow.conn).mark_failed(
                match_id=match_id,
                ingested_at=int(time.time()),
                error=error,
            )

    def run_cycle(self) -> CycleStats:
        """Виконує один цикл discovery + ingest.

        Помилка на одному match_id не зупиняє цикл — логується і записується
        в ingestion_log зі статусом 'failed'.

        Returns:
            CycleStats зі статистикою циклу.
        """
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
                logger.error(
                    "Ingest failed match_id=%s error=%s",
                    match_id,
                    error_msg,
                )

        logger.info(
            "Cycle done: discovered=%s skipped=%s ingested=%s failed=%s",
            stats.discovered,
            stats.skipped,
            stats.ingested,
            stats.failed,
        )
        return stats

    def start(self) -> None:
        """Запускає нескінченний цикл з паузою між ітераціями.

        Graceful shutdown на SIGINT/SIGTERM — поточний цикл завершується,
        наступний не починається.
        """
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
        """Сигналізує runner-у зупинитись після поточного циклу."""
        logger.info("Stop requested, finishing current cycle...")
        self._running = False

    def _setup_signal_handlers(self) -> None:
        """Реєструє SIGINT/SIGTERM для graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame: object) -> None:
        logger.info("Received signal %s, stopping after current cycle", signum)
        self.stop()

    def _interruptible_sleep(self, seconds: int) -> None:
        """Sleep що переривається при stop() через короткі інтервали."""
        deadline = time.time() + seconds
        while self._running and time.time() < deadline:
            time.sleep(min(1.0, deadline - time.time()))