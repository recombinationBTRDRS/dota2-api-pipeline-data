# services/ingestion/providers/opendota/client.py
import logging
import random
import time
from typing import Any, Protocol

import requests

from services.ingestion.app.config import settings

logger = logging.getLogger(__name__)


class MatchProvider(Protocol):
    """Протокол для підміни HTTP-клієнта в тестах."""

    def get_match(self, match_id: int) -> dict[str, Any]:
        """Повертає raw match dict для вказаного match_id."""
        ...


class OpenDotaClient(MatchProvider):
    """Синхронний клієнт OpenDota API.

    Підтримує:
    - rate limiting між запитами (settings.OPENDOTA_RATE_LIMIT req/min)
    - exponential backoff при 429 та 5xx
    - негайний fail для 4xx (не ретраїмо клієнтські помилки)
    - contextual RuntimeError при вичерпанні спроб
    """

    def __init__(self) -> None:
        self._last_request_ts = 0.0

    def _rate_limit(self) -> None:
        """Витримує мінімальний інтервал між запитами."""
        sleep_between = 60.0 / settings.OPENDOTA_RATE_LIMIT
        delta = time.time() - self._last_request_ts
        if delta < sleep_between:
            time.sleep(sleep_between - delta)
        self._last_request_ts = time.time()

    def _request(self, path: str) -> dict[str, Any]:
        """Виконує GET запит з retry-стратегією.

        Retry: тільки при 429 або 5xx (exponential backoff).
        Fail-fast: при будь-якому 4xx (крім 429) — одразу RuntimeError.

        Args:
            path: шлях після base URL, наприклад "/matches/123".

        Returns:
            Розпарсений JSON-відповідь як dict.

        Raises:
            RuntimeError: при 4xx помилці або вичерпанні всіх спроб.
        """
        url = f"{settings.OPENDOTA_BASE_URL}{path}"
        last_exc: Exception | None = None

        for attempt in range(1, settings.OPENDOTA_RETRIES + 1):
            self._rate_limit()
            try:
                resp = requests.get(url, timeout=settings.OPENDOTA_TIMEOUT)
            except requests.RequestException as e:
                last_exc = e
                if attempt == settings.OPENDOTA_RETRIES:
                    raise RuntimeError(
                        f"OpenDota request failed after {settings.OPENDOTA_RETRIES} attempts. "
                        f"URL: {url}. Last error: {e}"
                    ) from e
                sleep = (2 ** attempt) + random.random()
                logger.warning(
                    "OpenDota connection error %s, retry %s/%s, sleep %.2fs",
                    type(e).__name__, attempt, settings.OPENDOTA_RETRIES, sleep,
                )
                time.sleep(sleep)
                continue

            # 429 або 5xx — retryable
            if resp.status_code == 429 or resp.status_code >= 500:
                sleep = (2 ** attempt) + random.random()
                logger.warning(
                    "OpenDota %s, retry %s/%s, sleep %.2fs",
                    resp.status_code, attempt, settings.OPENDOTA_RETRIES, sleep,
                )
                time.sleep(sleep)
                continue

            # 4xx (крім 429) — не ретраїмо, одразу fail
            if 400 <= resp.status_code < 500:
                raise RuntimeError(
                    f"OpenDota client error {resp.status_code} for URL {url}. "
                    f"Body: {resp.text[:200]}"
                )

            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(
            f"OpenDota: all {settings.OPENDOTA_RETRIES} attempts exhausted for URL {url}. "
            f"Last error: {last_exc}"
        )

    def get_match(self, match_id: int) -> dict[str, Any]:
        """Завантажує матч з OpenDota API.

        Args:
            match_id: ідентифікатор матчу.

        Returns:
            Raw match JSON як dict.
        """
        logger.info("Fetching match %s from OpenDota", match_id)
        return self._request(f"/matches/{match_id}")