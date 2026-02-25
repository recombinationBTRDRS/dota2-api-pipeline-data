#services/ingestion/providers/opendota/client.py
import random
import time
from typing import Any, Protocol

import requests

from services.ingestion.app.config import settings

BASE_URL = settings.OPENDOTA_BASE_URL
REQUESTS_PER_MIN = settings.OPENDOTA_RATE_LIMIT
SLEEP_BETWEEN = 60 / REQUESTS_PER_MIN

MAX_RETRIES = settings.OPENDOTA_RETRIES
TIMEOUT = settings.OPENDOTA_TIMEOUT


class MatchProvider(Protocol):
    def get_match(self, match_id: int) -> dict[str, Any]:
        ...


class OpenDotaClient(MatchProvider):
    def __init__(self):
        self._last_request_ts = 0.0

    def _rate_limit(self):
        now = time.time()
        delta = now - self._last_request_ts
        if delta < SLEEP_BETWEEN:
            time.sleep(SLEEP_BETWEEN - delta)
        self._last_request_ts = time.time()

    def _request(self, path: str) -> dict[str, Any]:
        self._rate_limit()
        url = f"{BASE_URL}{path}"

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.get(url, timeout=TIMEOUT)
                if r.status_code == 429:
                    sleep = 2 ** attempt + random.random()
                    time.sleep(sleep)
                    continue

                r.raise_for_status()
                return r.json()

            except requests.RequestException:
                if attempt == MAX_RETRIES:
                    raise
                sleep = 2 ** attempt + random.random()
                time.sleep(sleep)

        raise RuntimeError("Unreachable")

    def get_match(self, match_id: int) -> dict[str, Any]:
        """Повертає дані матчу з OpenDota API"""
        return self._request(f"/matches/{match_id}")