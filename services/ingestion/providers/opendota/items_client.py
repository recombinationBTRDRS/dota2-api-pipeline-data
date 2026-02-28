# services/ingestion/providers/opendota/items_client.py
import logging
import random
import time
from typing import Any, Protocol

import requests

from services.ingestion.app.config import settings

logger = logging.getLogger(__name__)


class ItemsProvider(Protocol):
    """Протокол для підміни HTTP-клієнта в тестах."""

    def get_items(self) -> dict[str, Any]:
        """Повертає raw payload /constants/items."""
        ...


class OpenDotaItemsClient:
    """Клієнт для GET /constants/items OpenDota API."""

    def __init__(self) -> None:
        self._last_request_ts = 0.0

    def _rate_limit(self) -> None:
        rate = settings.OPENDOTA_RATE_LIMIT
        if rate <= 0:
            logger.warning("OPENDOTA_RATE_LIMIT=%s invalid, skipping rate limit", rate)
            self._last_request_ts = time.time()
            return
        sleep_between = 60.0 / rate
        delta = time.time() - self._last_request_ts
        if delta < sleep_between:
            time.sleep(sleep_between - delta)
        self._last_request_ts = time.time()

    def _get_raw(self) -> dict[str, Any]:
        url = f"{settings.OPENDOTA_BASE_URL}/constants/items"
        last_exc: Exception | None = None

        for attempt in range(1, settings.OPENDOTA_RETRIES + 1):
            self._rate_limit()
            try:
                resp = requests.get(url, timeout=settings.OPENDOTA_TIMEOUT)
            except requests.RequestException as e:
                last_exc = e
                if attempt == settings.OPENDOTA_RETRIES:
                    raise RuntimeError(
                        f"Items request failed after {settings.OPENDOTA_RETRIES} attempts. "
                        f"Last error: {last_exc}"
                    ) from e
                sleep = (2 ** attempt) + random.random()
                logger.warning("Items connection error %s, retry %s/%s, sleep %.2fs",
                               type(e).__name__, attempt, settings.OPENDOTA_RETRIES, sleep)
                time.sleep(sleep)
                continue

            if resp.status_code == 429 or resp.status_code >= 500:
                sleep = (2 ** attempt) + random.random()
                last_exc = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                logger.warning("Items %s, retry %s/%s, sleep %.2fs",
                               resp.status_code, attempt, settings.OPENDOTA_RETRIES, sleep)
                time.sleep(sleep)
                continue

            if 400 <= resp.status_code < 500:
                raise RuntimeError(
                    f"Items client error {resp.status_code}. Body: {resp.text[:200]}"
                )

            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise RuntimeError(
                    f"Items response has unexpected type: {type(data).__name__}"
                )
            return data

        raise RuntimeError(
            f"Items: all {settings.OPENDOTA_RETRIES} attempts exhausted. "
            f"Last error: {last_exc}"
        )

    def get_items(self) -> dict[str, Any]:
        logger.info("Fetching items from OpenDota")
        raw = self._get_raw()
        logger.info("Fetched %d raw items", len(raw))
        return raw