"""Tests for scraper.parsers.follow_on."""

from scraper.parsers.follow_on import parse_follow_on


class TestParseFollowOn:
    def test_basic_rank_extraction(self) -> None:
        edge = parse_follow_on("1st R1P1", source_round_id=-100, target_round_id=-200)
        assert edge is not None
        assert edge.source_rank == 1
        assert edge.target_slot == "R1P1"
        assert edge.source_round_id == -100
        assert edge.target_round_id == -200

    def test_second_place(self) -> None:
        edge = parse_follow_on("2nd R1P1", source_round_id=-100, target_round_id=-200)
        assert edge is not None
        assert edge.source_rank == 2

    def test_numeric_only(self) -> None:
        edge = parse_follow_on("3", source_round_id=-100, target_round_id=-200)
        assert edge is not None
        assert edge.source_rank == 3
        assert edge.target_slot == ""

    def test_empty_text_returns_none(self) -> None:
        assert parse_follow_on("", source_round_id=-100, target_round_id=-200) is None

    def test_no_leading_digit_returns_none(self) -> None:
        assert parse_follow_on("Winner", source_round_id=-100, target_round_id=-200) is None

    def test_complex_short_name(self) -> None:
        edge = parse_follow_on("1st R2G1P3", source_round_id=-100, target_round_id=-300)
        assert edge is not None
        assert edge.source_rank == 1
        assert edge.target_slot == "R2G1P3"
