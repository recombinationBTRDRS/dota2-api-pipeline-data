#services/ingestion/providers/opendota/client.py
import logging
import random
import time
from typing import Any, Protocol

import requests

from services.ingestion.app.config import settings

logger = logging.getLogger(__name__)


BASE_URL = settings.OPENDOTA_BASE_URL
REQUESTS_PER_MIN = settings.OPENDOTA_RATE_LIMIT
SLEEP_BETWEEN = 60 / REQUESTS_PER_MIN

MAX_RETRIES = settings.OPENDOTA_RETRIES
TIMEOUT = settings.OPENDOTA_TIMEOUT


class MatchProvider(Protocol):
    def get_match(self, match_id: int) -> dict[str, Any]:
        ...


class OpenDotaClient(MatchProvider):
    def __init__(self) -> None:
        self._last_request_ts = 0.0

    def _rate_limit(self) -> None:
        sleep_between = 60 / settings.OPENDOTA_RATE_LIMIT
        now = time.time()
        delta = now - self._last_request_ts
        if delta < sleep_between:
            time.sleep(sleep_between - delta)
        self._last_request_ts = time.time()

    def _request(self, path: str) -> dict[str, Any]:
        url = f"{settings.OPENDOTA_BASE_URL}{path}"

        for attempt in range(1, settings.OPENDOTA_RETRIES + 1):
            self._rate_limit()

            try:
                resp = requests.get(url, timeout=settings.OPENDOTA_TIMEOUT)

                if resp.status_code == 429 or resp.status_code >= 500:
                    sleep = (2 ** attempt) + random.random()
                    logger.warning(
                        "OpenDota error %s, retry %s/%s, sleep %.2fs",
                        resp.status_code,
                        attempt,
                        settings.OPENDOTA_RETRIES,
                        sleep,
                    )
                    time.sleep(sleep)
                    continue

                resp.raise_for_status()
                return resp.json()

            except requests.RequestException as e:
                if attempt == settings.OPENDOTA_RETRIES:
                    logger.exception("OpenDota request failed after retries")
                    raise RuntimeError("OpenDota request failed") from e

                sleep = (2 ** attempt) + random.random()
                logger.warning(
                    "OpenDota exception %s, retry %s/%s, sleep %.2fs",
                    e.__class__.__name__,
                    attempt,
                    settings.OPENDOTA_RETRIES,
                    sleep,
                )
                time.sleep(sleep)

        raise RuntimeError("Unreachable")

    def get_match(self, match_id: int) -> dict[str, Any]:
        logger.info("Fetching match %s from OpenDota", match_id)
        return self._request(f"/matches/{match_id}")