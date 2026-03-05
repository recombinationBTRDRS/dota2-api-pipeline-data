# services/analysis/app/clients/ingestion.py
from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from services.analysis.app.config import config

logger = logging.getLogger(__name__)

_RETRIES = 3
_BACKOFF = [1.0, 2.0, 4.0]
_TIMEOUT = 10


class IngestionUnavailableError(RuntimeError):
    """Ingestion API недоступний після всіх спроб."""


class IngestionClient:
    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or config.ingestion_api_url).rstrip("/")

    # ── internal ─────────────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> Any:
        url = f"{self._base}{path}"
        last_exc: Exception | None = None

        for attempt, delay in enumerate((_BACKOFF[i] for i in range(_RETRIES)), 1):
            try:
                resp = requests.get(url, params=params, timeout=_TIMEOUT)
                if resp.status_code == 429 or resp.status_code >= 500:
                    logger.warning(
                        "IngestionClient %s → %d, retry %d/%d",
                        path, resp.status_code, attempt, _RETRIES,
                    )
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                return resp.json()
            except (ConnectionError, Timeout) as exc:
                last_exc = exc
                logger.warning(
                    "IngestionClient %s connection error, retry %d/%d: %s",
                    path, attempt, _RETRIES, exc,
                )
                time.sleep(delay)
            except HTTPError as exc:
                raise IngestionUnavailableError(str(exc)) from exc

        raise IngestionUnavailableError(
            f"Ingestion API unavailable after {_RETRIES} attempts: {url}"
        ) from last_exc

    # ── public API ────────────────────────────────────────────────────────────

    def get_hero_matchups(self, hero_id: int, limit: int = 20) -> list[dict]:
        """GET /computed/heroes/{hero_id}/matchups"""
        try:
            data = self._get(
                f"/computed/heroes/{hero_id}/matchups",
                params={"limit": limit},
            )
            return data if isinstance(data, list) else []
        except IngestionUnavailableError:
            logger.warning("get_hero_matchups(%d) unavailable", hero_id)
            return []

    def get_hero_synergies(self, hero_id: int, limit: int = 20) -> list[dict]:
        """GET /computed/heroes/{hero_id}/synergies"""
        try:
            data = self._get(
                f"/computed/heroes/{hero_id}/synergies",
                params={"limit": limit},
            )
            return data if isinstance(data, list) else []
        except IngestionUnavailableError:
            logger.warning("get_hero_synergies(%d) unavailable", hero_id)
            return []

    def get_hero_stats(self, hero_id: int) -> dict | None:
        """GET /computed/heroes/{hero_id}/stats  →  перший запис (all patches)"""
        try:
            data = self._get(f"/computed/heroes/{hero_id}/stats")
            # повертає list[HeroStatRow] — беремо агрегат (patch=None, region=None)
            if not isinstance(data, list) or not data:
                return None
            # шукаємо запис без patch/region (загальний агрегат)
            for row in data:
                if row.get("patch") is None and row.get("region") is None:
                    return row
            return data[0]
        except IngestionUnavailableError:
            logger.warning("get_hero_stats(%d) unavailable", hero_id)
            return None

    def get_match_players(self, match_id: int) -> list[dict]:
        """
        Повертає гравців конкретного матчу.
        Ingestion не має прямого /matches/{id}/players endpoint —
        використовуємо /heroes/{hero_id}/stats як fallback або
        запит до DB напряму (поки що через /analytics/meta для перевірки).

        TODO: додати GET /matches/{match_id}/players в Ingestion API (Task 8.4+)
        Поки повертаємо порожній список — analyzers обробляють gracefully.
        """
        logger.warning(
            "get_match_players(%d): endpoint not yet implemented in Ingestion — "
            "add GET /matches/{id}/players in Epic 8+",
            match_id,
        )
        return []
