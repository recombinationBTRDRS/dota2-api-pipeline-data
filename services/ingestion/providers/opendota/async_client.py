# providers/opendota/async_client.py (потім)
import asyncio
import httpx

class AsyncOpenDotaClient:
    async def get_match(self, match_id: int) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(f"https://api.opendota.com/api/matches/{match_id}")
            r.raise_for_status()
            await asyncio.sleep(1.0)  # rate limit
            return r.json()