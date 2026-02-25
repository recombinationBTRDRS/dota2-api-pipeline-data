# providers/opendota/async_client.py
import asyncio

import httpx


class AsyncOpenDotaClient:
    async def get_match(self, match_id: int) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                r = await client.get(f"https://api.opendota.com/api/matches/{match_id}")
                r.raise_for_status()
                return r.json()
            finally:
                await asyncio.sleep(1.0)
