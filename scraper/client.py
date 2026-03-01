import asyncio

import httpx

from scraper.config import (
    AES_API_BASE,
    BACKOFF_BASE_SECONDS,
    DEFAULT_HEADERS,
    MAX_RETRIES,
    RATE_LIMIT_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
)


class AESClientError(Exception):
    """Raised when the AES API returns an error or retries are exhausted."""


class AESClient:
    """
    HTTP client for the AES Results JSON API.

    Usage:
        async with AESClient() as client:
            event = await client.get_event("PTAwMDAwNDE4MzE90")
            plays = await client.get_division_plays("PTAwMDAwNDE4MzE90", 199194)
    """

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AESClient":
        self._client = httpx.AsyncClient(
            base_url=AES_API_BASE,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def _get(self, path: str) -> dict | list:
        """
        GET request with retry + exponential backoff + rate limiting.

        Retries on: httpx.TimeoutException, httpx.HTTPStatusError (5xx, 429).
        Raises AESClientError on other 4xx or after max retries exhausted.
        """
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                await asyncio.sleep(RATE_LIMIT_DELAY_SECONDS)
                response = await self._client.get(path)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status >= 500 or status == 429:
                    last_exc = e
                else:
                    raise AESClientError(
                        f"API error {status}: {path}"
                    ) from e
            except httpx.TimeoutException as e:
                last_exc = e
            await asyncio.sleep(BACKOFF_BASE_SECONDS * (2 ** attempt))
        raise AESClientError(f"Max retries exceeded for {path}") from last_exc

    # --- Event-level ---
    async def get_event(self, event_key: str) -> dict:
        """GET /event/{eventKey} → event metadata + divisions list"""
        return await self._get(f"/event/{event_key}")

    async def get_event_timestamp(self, event_key: str) -> dict:
        """GET /event/{eventKey}/timestamp → {LastUpdatedTimestamp}"""
        return await self._get(f"/event/{event_key}/timestamp")

    # --- Division-level ---
    async def get_division_plays(self, event_key: str, division_id: int) -> dict:
        """GET /event/{eventKey}/division/{divId}/plays → rounds/pools/brackets structure"""
        return await self._get(f"/event/{event_key}/division/{division_id}/plays")

    async def get_division_playdays(self, event_key: str, division_id: int) -> list:
        """GET /event/{eventKey}/division/{divId}/playdays → [{HasPools, HasBrackets, DateTime}]"""
        return await self._get(f"/event/{event_key}/division/{division_id}/playdays")

    async def get_division_pools(self, event_key: str, division_id: int, date: str) -> list:
        """GET /event/{eventKey}/division/{divId}/pools/{date} → pool standings"""
        return await self._get(f"/event/{event_key}/division/{division_id}/pools/{date}")

    async def get_division_brackets(self, event_key: str, division_id: int, date: str) -> list:
        """GET /event/{eventKey}/division/{divId}/brackets/{date} → bracket tree"""
        return await self._get(f"/event/{event_key}/division/{division_id}/brackets/{date}")

    # --- Play-level ---
    async def get_poolsheet(self, event_key: str, play_id: int) -> dict:
        """GET /event/{eventKey}/poolsheet/{playId} → {Pool, Matches, FutureRoundMatches}"""
        return await self._get(f"/event/{event_key}/poolsheet/{play_id}")
