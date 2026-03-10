"""Tests for scraper.client using respx to mock httpx."""

import httpx
import pytest
import respx

from scraper.client import AESClient, AESRequestError


@pytest.fixture
def mock_client() -> AESClient:
    return AESClient(base_url="https://test.example.com", delay=0, max_retries=3)


class TestAESClient:
    @respx.mock
    async def test_get_event(self, mock_client: AESClient) -> None:
        respx.get("https://test.example.com/event/KEY").mock(
            return_value=httpx.Response(200, json={"Name": "Tournament"})
        )
        result = await mock_client.get_event("KEY")
        assert result == {"Name": "Tournament"}
        await mock_client.close()

    @respx.mock
    async def test_get_division_plays(self, mock_client: AESClient) -> None:
        respx.get("https://test.example.com/event/KEY/division/100/plays").mock(
            return_value=httpx.Response(200, json=[{"RoundId": -100}])
        )
        result = await mock_client.get_division_plays("KEY", 100)
        assert result == [{"RoundId": -100}]
        await mock_client.close()

    @respx.mock
    async def test_get_pool_sheet(self, mock_client: AESClient) -> None:
        respx.get("https://test.example.com/event/KEY/poolsheet/-51151").mock(
            return_value=httpx.Response(200, json={"PlayId": -51151})
        )
        result = await mock_client.get_pool_sheet("KEY", -51151)
        assert result == {"PlayId": -51151}
        await mock_client.close()

    @respx.mock
    async def test_get_brackets(self, mock_client: AESClient) -> None:
        respx.get(
            "https://test.example.com/event/KEY/division/100/brackets/2025-03-08"
        ).mock(return_value=httpx.Response(200, json=[]))
        result = await mock_client.get_brackets("KEY", 100, "2025-03-08")
        assert result == []
        await mock_client.close()

    @respx.mock
    async def test_retry_on_429(self, mock_client: AESClient) -> None:
        route = respx.get("https://test.example.com/event/KEY")
        route.side_effect = [
            httpx.Response(429),
            httpx.Response(200, json={"ok": True}),
        ]
        result = await mock_client.get_event("KEY")
        assert result == {"ok": True}
        await mock_client.close()

    @respx.mock
    async def test_retry_on_500(self, mock_client: AESClient) -> None:
        route = respx.get("https://test.example.com/event/KEY")
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, json={"ok": True}),
        ]
        result = await mock_client.get_event("KEY")
        assert result == {"ok": True}
        await mock_client.close()

    @respx.mock
    async def test_exhausted_retries_raises(self, mock_client: AESClient) -> None:
        respx.get("https://test.example.com/event/KEY").mock(
            return_value=httpx.Response(500)
        )
        with pytest.raises(AESRequestError, match="/event/KEY"):
            await mock_client.get_event("KEY")
        await mock_client.close()

    @respx.mock
    async def test_404_raises_immediately(self, mock_client: AESClient) -> None:
        respx.get("https://test.example.com/event/KEY").mock(
            return_value=httpx.Response(404)
        )
        with pytest.raises(httpx.HTTPStatusError):
            await mock_client.get_event("KEY")
        await mock_client.close()

    @respx.mock
    async def test_context_manager(self) -> None:
        respx.get("https://test.example.com/event/KEY").mock(
            return_value=httpx.Response(200, json={})
        )
        async with AESClient(
            base_url="https://test.example.com", delay=0
        ) as client:
            result = await client.get_event("KEY")
            assert result == {}
