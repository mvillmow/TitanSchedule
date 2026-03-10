"""Tests for scraper.parsers.follow_on."""

from scraper.parsers.follow_on import parse_follow_on


class TestParseFollowOn:
    def test_basic_rank_extraction(self) -> None:
        ref = parse_follow_on("1st R1P1")
        assert ref is not None
        assert ref.rank == 1
        assert ref.source_short_name == "R1P1"

    def test_second_place(self) -> None:
        ref = parse_follow_on("2nd R1P1")
        assert ref is not None
        assert ref.rank == 2
        assert ref.source_short_name == "R1P1"

    def test_numeric_only(self) -> None:
        ref = parse_follow_on("3")
        assert ref is not None
        assert ref.rank == 3
        assert ref.source_short_name == ""

    def test_empty_text_returns_none(self) -> None:
        assert parse_follow_on("") is None

    def test_no_leading_digit_returns_none(self) -> None:
        assert parse_follow_on("Winner") is None

    def test_complex_short_name(self) -> None:
        ref = parse_follow_on("1st R2G1P3")
        assert ref is not None
        assert ref.rank == 1
        assert ref.source_short_name == "R2G1P3"

    def test_third_place(self) -> None:
        ref = parse_follow_on("3rd R1P2")
        assert ref is not None
        assert ref.rank == 3
        assert ref.source_short_name == "R1P2"

    def test_fourth_place(self) -> None:
        ref = parse_follow_on("4th R1P1")
        assert ref is not None
        assert ref.rank == 4
