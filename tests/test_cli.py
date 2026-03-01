from scraper.cli import _slugify


class TestSlugify:
    def test_basic(self):
        assert _slugify("18s - 15s Power League") == "18s-15s-power-league"

    def test_special_chars(self):
        assert _slugify("Girls' 14 & Under") == "girls-14-under"

    def test_empty(self):
        assert _slugify("") == "unknown"

    def test_already_slug(self):
        assert _slugify("12-open") == "12-open"
