"""Tests for scraper.url."""

import pytest

from scraper.url import parse_aes_url


class TestParseAesUrl:
    def test_division_schedule(self) -> None:
        url = "https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/division/199189/schedule"
        key, div_id = parse_aes_url(url)
        assert key == "PTAwMDAwNDE4Mjk90"
        assert div_id == 199189

    def test_divisions_overview(self) -> None:
        url = "https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199189/overview"
        key, div_id = parse_aes_url(url)
        assert key == "PTAwMDAwNDE4Mjk90"
        assert div_id == 199189

    def test_division_no_trailing(self) -> None:
        url = "https://results.advancedeventsystems.com/event/ABC123/division/42/something"
        key, div_id = parse_aes_url(url)
        assert key == "ABC123"
        assert div_id == 42

    def test_invalid_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse AES URL"):
            parse_aes_url("https://example.com/not-aes")

    def test_with_query_params(self) -> None:
        url = "https://results.advancedeventsystems.com/event/KEY/divisions/100/overview?tab=schedule"
        key, div_id = parse_aes_url(url)
        assert key == "KEY"
        assert div_id == 100
