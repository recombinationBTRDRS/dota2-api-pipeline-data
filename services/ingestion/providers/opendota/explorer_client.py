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

    Explorer приймає обмежений SQL проти public_matches і повертає JSON
    з полем `rows` — список dict з match_id та іншими колонками.

    Використовує ту ж retry/backoff стратегію що й OpenDotaClient:
    - rate limiting між запитами
    - exponential backoff при 429 та 5xx
    - fail-fast при non-retryable 4xx
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

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        """Виконує GET /explorer з retry-стратегією.

        Args:
            params: query params для запиту (включно з sql=...).

        Returns:
            Розпарсений JSON як dict.

        Raises:
            RuntimeError: при 4xx або вичерпанні спроб.
        """
        url = f"{settings.OPENDOTA_BASE_URL}/explorer"
        last_exc: Exception | None = None

        for attempt in range(1, settings.OPENDOTA_RETRIES + 1):
            self._rate_limit()
            try:
                resp = requests.get(url, params=params, timeout=settings.OPENDOTA_TIMEOUT)
            except requests.RequestException as e:
                last_exc = e
                if attempt == settings.OPENDOTA_RETRIES:
                    raise RuntimeError(
                        f"Explorer request failed after {settings.OPENDOTA_RETRIES} attempts. "
                        f"Last error: {e}"
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
                logger.warning(
                    "Explorer %s, retry %s/%s, sleep %.2fs",
                    resp.status_code, attempt, settings.OPENDOTA_RETRIES, sleep,
                )
                time.sleep(sleep)
                continue

            if 400 <= resp.status_code < 500:
                raise RuntimeError(
                    f"Explorer client error {resp.status_code}. "
                    f"Body: {resp.text[:200]}"
                )

            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

        raise RuntimeError(
            f"Explorer: all {settings.OPENDOTA_RETRIES} attempts exhausted. "
            f"Last error: {last_exc}"
        )

    def discover(self, f: DiscoveryFilter) -> list[DiscoveredMatch]:
        """Виконує discovery запит і повертає список матчів.

        Args:
            f: фільтри для пошуку матчів.

        Returns:
            Список DiscoveredMatch з match_id.

        Raises:
            RuntimeError: якщо API повернув помилку або retries вичерпані.
            ValueError: якщо відповідь не містить поля 'rows'.
        """
        sql = build_explorer_sql(f)
        logger.info(
            "Discovery query: lobby_type=%s min_mmr=%s limit=%s patch=%s region=%s",
            f.lobby_type, f.min_mmr, f.limit, f.patch, f.region,
        )

        data = self._get({"sql": sql})

        rows = data.get("rows")
        if rows is None:
            raise ValueError(
                f"Explorer response missing 'rows' field. Got keys: {list(data.keys())}"
            )

        matches = [DiscoveredMatch(match_id=row["match_id"]) for row in rows]
        logger.info("Discovery found %d matches", len(matches))
        return matches