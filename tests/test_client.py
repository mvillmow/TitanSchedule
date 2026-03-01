import httpx
import pytest
import respx

from scraper.client import AESClient, AESClientError
from scraper.config import AES_API_BASE


class TestAESClient:
    @respx.mock
    async def test_get_event_success(self):
        respx.get(f"{AES_API_BASE}/event/TEST_KEY").mock(
            return_value=httpx.Response(200, json={"Key": "TEST_KEY", "Name": "Test Event"})
        )
        async with AESClient() as client:
            result = await client.get_event("TEST_KEY")
        assert result["Name"] == "Test Event"

    @respx.mock
    async def test_get_event_404_raises(self):
        respx.get(f"{AES_API_BASE}/event/BAD_KEY").mock(
            return_value=httpx.Response(404, json={"error": "not found"})
        )
        async with AESClient() as client:
            with pytest.raises(AESClientError):
                await client.get_event("BAD_KEY")

    @respx.mock
    async def test_retry_on_500(self):
        route = respx.get(f"{AES_API_BASE}/event/KEY")
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, json={"Key": "KEY"}),
        ]
        async with AESClient() as client:
            result = await client.get_event("KEY")
        assert result["Key"] == "KEY"
        assert route.call_count == 3

    @respx.mock
    async def test_max_retries_exhausted(self):
        respx.get(f"{AES_API_BASE}/event/KEY").mock(
            return_value=httpx.Response(500)
        )
        async with AESClient() as client:
            with pytest.raises(AESClientError, match="Max retries"):
                await client.get_event("KEY")

    @respx.mock
    async def test_get_poolsheet(self):
        respx.get(f"{AES_API_BASE}/event/KEY/poolsheet/-51151").mock(
            return_value=httpx.Response(
                200,
                json={
                    "Pool": {"PlayId": -51151, "FullName": "Pool 1"},
                    "Matches": [],
                    "FutureRoundMatches": [],
                },
            )
        )
        async with AESClient() as client:
            result = await client.get_poolsheet("KEY", -51151)
        assert result["Pool"]["FullName"] == "Pool 1"

    @respx.mock
    async def test_get_division_plays(self):
        respx.get(f"{AES_API_BASE}/event/KEY/division/12345/plays").mock(
            return_value=httpx.Response(200, json={"Plays": []})
        )
        async with AESClient() as client:
            result = await client.get_division_plays("KEY", 12345)
        assert result == {"Plays": []}

    @respx.mock
    async def test_get_division_brackets(self):
        respx.get(f"{AES_API_BASE}/event/KEY/division/12345/brackets/2026-02-07").mock(
            return_value=httpx.Response(200, json=[])
        )
        async with AESClient() as client:
            result = await client.get_division_brackets("KEY", 12345, "2026-02-07")
        assert result == []

    @respx.mock
    async def test_4xx_not_retried(self):
        route = respx.get(f"{AES_API_BASE}/event/KEY")
        route.mock(return_value=httpx.Response(403, json={"error": "forbidden"}))
        async with AESClient() as client:
            with pytest.raises(AESClientError):
                await client.get_event("KEY")
        # Should only be called once — no retry on 4xx
        assert route.call_count == 1
