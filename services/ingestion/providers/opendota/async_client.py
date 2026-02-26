# services/ingestion/providers/opendota/async_client.py
import asyncio
import logging
import random

import httpx

from services.ingestion.app.config import settings

logger = logging.getLogger(__name__)


class AsyncOpenDotaClient:
    """Асинхронний клієнт OpenDota API з rate-limit retry та exponential backoff."""

    async def get_match(self, match_id: int) -> dict:
        """Отримує дані матчу за match_id.

        Retry тільки при 429 та 5xx (exponential backoff).
        Fail-fast при 4xx (крім 429) — одразу raise, не ретраїмо.

        Args:
            match_id: ідентифікатор матчу OpenDota.

        Returns:
            Raw match dict від OpenDota API.

        Raises:
            httpx.HTTPStatusError: при non-retryable 4xx відповіді.
            RuntimeError: якщо всі retry-спроби вичерпані (429/5xx).
        """
        url = f"{settings.OPENDOTA_BASE_URL}/matches/{match_id}"
        last_exc: Exception | None = None

        async with httpx.AsyncClient(timeout=settings.OPENDOTA_TIMEOUT) as client:
            for attempt in range(1, settings.OPENDOTA_RETRIES + 1):
                try:
                    r = await client.get(url)

                    # Retryable: rate limit або server error
                    if r.status_code == 429 or r.status_code >= 500:
                        sleep = (2 ** attempt) + random.random()
                        logger.warning(
                            "AsyncOpenDota %s on attempt %s/%s, backoff %.2fs",
                            r.status_code,
                            attempt,
                            settings.OPENDOTA_RETRIES,
                            sleep,
                        )
                        await asyncio.sleep(sleep)
                        continue

                    # Non-retryable 4xx — fail-fast, не витрачаємо retry
                    if 400 <= r.status_code < 500:
                        r.raise_for_status()  # кидає HTTPStatusError

                    r.raise_for_status()
                    return r.json()

                except httpx.HTTPStatusError:
                    # Пробрасуємо 4xx одразу — це не мережева помилка
                    raise
                except httpx.HTTPError as e:
                    last_exc = e
                    sleep = (2 ** attempt) + random.random()
                    logger.warning(
                        "AsyncOpenDota network error %s on attempt %s/%s, backoff %.2fs",
                        type(e).__name__,
                        attempt,
                        settings.OPENDOTA_RETRIES,
                        sleep,
                    )
                    await asyncio.sleep(sleep)

        raise RuntimeError(
            f"AsyncOpenDotaClient: failed to fetch match_id={match_id} "
            f"after {settings.OPENDOTA_RETRIES} attempts. Last error: {last_exc}"
        )