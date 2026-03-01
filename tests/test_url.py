import pytest

from scraper.url import AESUrlParts, parse_aes_url


class TestParseAESUrl:
    def test_division_overview(self):
        result = parse_aes_url(
            "https://results.advancedeventsystems.com/event/PTAwMDAwNDE4MzE90/divisions/199194/overview"
        )
        assert result == AESUrlParts(
            event_key="PTAwMDAwNDE4MzE90", division_id=199194, pool_id=None
        )

    def test_division_standings(self):
        result = parse_aes_url(
            "https://results.advancedeventsystems.com/event/PTAwMDAwNDEwNjg90/divisions/193839/standings"
        )
        assert result == AESUrlParts(
            event_key="PTAwMDAwNDEwNjg90", division_id=193839, pool_id=None
        )

    def test_pool_subpage(self):
        result = parse_aes_url(
            "https://results.advancedeventsystems.com/event/PTAwMDAwNDE0NzU90/divisions/197173/overview/pool/-50218"
        )
        assert result == AESUrlParts(
            event_key="PTAwMDAwNDE0NzU90", division_id=197173, pool_id=-50218
        )

    def test_teams_page(self):
        result = parse_aes_url(
            "https://results.advancedeventsystems.com/event/PTAwMDAwNDEwNjg90/divisions/193843/teams"
        )
        assert result == AESUrlParts(
            event_key="PTAwMDAwNDEwNjg90", division_id=193843, pool_id=None
        )

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            parse_aes_url("https://google.com/search?q=volleyball")

    def test_missing_division_raises(self):
        with pytest.raises(ValueError):
            parse_aes_url(
                "https://results.advancedeventsystems.com/event/PTAwMDAwNDE4MzE90/home"
            )
