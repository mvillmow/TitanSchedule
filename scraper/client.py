"""Async HTTP client for the AES REST API."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from scraper.config import API_BASE, DEFAULT_HEADERS, MAX_RETRIES, RATE_LIMIT_DELAY, REQUEST_TIMEOUT

_RETRY_STATUSES = {429, 500, 502, 503, 504}


class AESRequestError(Exception):
    """Raised when an AES API request fails after all retries."""

    def __init__(self, path: str, attempts: int, cause: Exception) -> None:
        self.path = path
        self.attempts = attempts
        self.cause = cause
        super().__init__(f"Request to {path} failed after {attempts} attempts: {cause}")


class AESClient:
    """Async HTTP client wrapping httpx for AES API requests."""

    def __init__(
        self,
        base_url: str = API_BASE,
        delay: float = RATE_LIMIT_DELAY,
        max_retries: int = MAX_RETRIES,
        timeout: float = REQUEST_TIMEOUT,
    ) -> None:
        self.base_url = base_url
        self.delay = delay
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
        )

    async def __aenter__(self) -> AESClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, path: str) -> Any:
        """Make a GET request with retry and rate limiting."""
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            if attempt > 0:
                backoff = 2**attempt * 0.5
                await asyncio.sleep(backoff)
            try:
                resp = await self._client.get(path)
                if resp.status_code in _RETRY_STATUSES:
                    last_exc = httpx.HTTPStatusError(
                        f"HTTP {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                    continue
                resp.raise_for_status()
                await asyncio.sleep(self.delay)
                return resp.json()
            except httpx.TimeoutException as exc:
                last_exc = exc
                continue
        raise AESRequestError(path, self.max_retries, last_exc) from last_exc  # type: ignore[arg-type]

    async def get_event(self, event_key: str) -> Any:
        return await self._request(f"/event/{event_key}")

    async def get_division_plays(self, event_key: str, division_id: int) -> Any:
        return await self._request(f"/event/{event_key}/division/{division_id}/plays")

    async def get_pool_sheet(self, event_key: str, play_id: int) -> Any:
        return await self._request(f"/event/{event_key}/poolsheet/{play_id}")

    async def get_brackets(self, event_key: str, division_id: int, date: str) -> Any:
        return await self._request(
            f"/event/{event_key}/division/{division_id}/brackets/{date}"
        )

    async def get_pools(self, event_key: str, division_id: int) -> Any:
        return await self._request(f"/event/{event_key}/division/{division_id}/pools")
