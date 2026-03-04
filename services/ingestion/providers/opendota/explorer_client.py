# services/ingestion/providers/opendota/explorer_client.py
import logging
import random
import time
from typing import Any, Protocol

import requests

from services.ingestion.app.config import settings
from services.ingestion.domains.discovery.dtos import DiscoveredMatch, DiscoveryFilter
from services.ingestion.domains.discovery.query_builder import build_explorer_sql

logger = logging.getLogger(__name__)


class DiscoveryProvider(Protocol):
    """Протокол для підміни Explorer-клієнта в тестах."""

    def discover(self, f: DiscoveryFilter) -> list[DiscoveredMatch]:
        """Повертає список знайдених матчів за фільтром."""
        ...


class OpenDotaExplorerClient:
    """Клієнт до OpenDota Explorer API (/explorer?sql=...).

    Приймає DiscoveryFilter, будує SQL через build_explorer_sql(f)
    і виконує запит до /explorer. Повертає list[DiscoveredMatch].

    Retry стратегія:
    - rate limiting між запитами (OPENDOTA_RATE_LIMIT req/min)
    - exponential backoff при 429 та 5xx
    - fail-fast при non-retryable 4xx
    """

    def __init__(self) -> None:
        self._last_request_ts = 0.0

    def _rate_limit(self) -> None:
        """Витримує мінімальний інтервал між запитами.

        Якщо OPENDOTA_RATE_LIMIT <= 0 — пропускає sleep (необмежено).
        """
        rate = settings.OPENDOTA_RATE_LIMIT
        if rate <= 0:
            logger.warning("OPENDOTA_RATE_LIMIT=%s is invalid, skipping rate limit", rate)
            self._last_request_ts = time.time()
            return

        sleep_between = 60.0 / rate
        delta = time.time() - self._last_request_ts
        if delta < sleep_between:
            time.sleep(sleep_between - delta)
        self._last_request_ts = time.time()

    def _get(self, sql: str) -> list[dict[str, Any]]:
        """Виконує GET /explorer?sql=... з retry-стратегією.

        Args:
            sql: готовий SQL рядок для OpenDota Explorer.

        Returns:
            Список рядків з поля 'rows' відповіді.

        Raises:
            RuntimeError: при 4xx або вичерпанні спроб (з HTTP контекстом).
        """
        url = f"{settings.OPENDOTA_BASE_URL}/explorer"
        last_exc: Exception | None = None

        for attempt in range(1, settings.OPENDOTA_RETRIES + 1):
            self._rate_limit()
            try:
                resp = requests.get(url, params={"sql": sql}, timeout=settings.OPENDOTA_TIMEOUT)
            except requests.RequestException as e:
                last_exc = e
                if attempt == settings.OPENDOTA_RETRIES:
                    raise RuntimeError(
                        f"Explorer request failed after {settings.OPENDOTA_RETRIES} attempts. "
                        f"Last error: {last_exc}"
                    ) from e
                sleep = (2 ** attempt) + random.random()
                logger.warning(
                    "Explorer connection error %s, retry %s/%s, sleep %.2fs",
                    type(e).__name__, attempt, settings.OPENDOTA_RETRIES, sleep,
                )
                time.sleep(sleep)
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                sleep = (2 ** attempt) + random.random()
                last_exc = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                logger.warning(
                    "Explorer %s, retry %s/%s, sleep %.2fs",
                    resp.status_code, attempt, settings.OPENDOTA_RETRIES, sleep,
                )
                time.sleep(sleep)
                continue

            if 400 <= resp.status_code < 500:
                raise RuntimeError(
                    f"Explorer client error {resp.status_code}. Body: {resp.text[:200]}"
                )

            resp.raise_for_status()
            data = resp.json()
            rows = data.get("rows")
            if rows is None:
                raise ValueError(
                    f"Explorer response missing 'rows'. Got keys: {list(data.keys())}"
                )
            return rows  # type: ignore[no-any-return]

        raise RuntimeError(
            f"Explorer: all {settings.OPENDOTA_RETRIES} attempts exhausted. "
            f"Last error: {last_exc}"
        )

    def discover(self, f: DiscoveryFilter) -> list[DiscoveredMatch]:
        """Виконує discovery запит за фільтром і повертає список матчів.

        Будує SQL через build_explorer_sql(f), виконує GET /explorer,
        повертає list[DiscoveredMatch] з match_id.

        Args:
            f: DiscoveryFilter з параметрами пошуку.

        Returns:
            Список DiscoveredMatch з match_id.

        Raises:
            RuntimeError: якщо API повернув помилку або retries вичерпані.
            ValueError: якщо відповідь не містить поля 'rows'.
        """
        sql = build_explorer_sql(f)
        logger.info(
            "Discovery query: lobby_type=%s min_rank_tier=%s limit=%s patch=%s region=%s",
            f.lobby_type, f.min_rank_tier, f.limit, f.patch, f.region,
        )
        rows = self._get(sql)
        matches = [DiscoveredMatch(match_id=row["match_id"]) for row in rows]
        logger.info("Discovery found %d matches", len(matches))
        return matches
