"""Tests for scraper.parsers.division."""

from scraper.parsers.division import parse_division_plays


class TestParseDivisionPlays:
    def test_sorts_by_round_id_descending(self) -> None:
        data = [
            {"RoundId": -200, "RoundName": "Round 2", "Type": 0},
            {"RoundId": -100, "RoundName": "Round 1", "Type": 0},
            {"RoundId": -300, "RoundName": "Round 3", "Type": 1},
        ]
        rounds = parse_division_plays(data)
        assert [r.id for r in rounds] == [-100, -200, -300]

    def test_pool_type(self) -> None:
        data = [{"RoundId": -100, "RoundName": "Pool Play", "Type": 0}]
        rounds = parse_division_plays(data)
        assert rounds[0].type == "pool"

    def test_bracket_type(self) -> None:
        data = [{"RoundId": -200, "RoundName": "Gold Bracket", "Type": 1}]
        rounds = parse_division_plays(data)
        assert rounds[0].type == "bracket"

    def test_group_fields(self) -> None:
        data = [
            {
                "RoundId": -100,
                "RoundName": "R1",
                "Type": 0,
                "GroupId": -50,
                "GroupName": "Gold A",
                "CompleteShortName": "R1P1",
            }
        ]
        rounds = parse_division_plays(data)
        assert rounds[0].group_id == -50
        assert rounds[0].group_name == "Gold A"
        assert rounds[0].short_name == "R1P1"

    def test_play_id_and_order(self) -> None:
        data = [
            {
                "RoundId": -100,
                "RoundName": "R1",
                "Type": 0,
                "PlayId": -51151,
                "Order": 3,
                "Date": "2025-03-08",
            }
        ]
        rounds = parse_division_plays(data)
        assert rounds[0].play_id == -51151
        assert rounds[0].order == 3
        assert rounds[0].date == "2025-03-08"

    def test_missing_play_id_defaults_none(self) -> None:
        data = [{"RoundId": -100, "RoundName": "R1", "Type": 0}]
        rounds = parse_division_plays(data)
        assert rounds[0].play_id is None
        assert rounds[0].order == 0

    def test_empty_input(self) -> None:
        assert parse_division_plays([]) == []

    def test_mixed_types_same_round(self) -> None:
        data = [
            {"RoundId": -100, "RoundName": "R1 Pool", "Type": 0},
            {"RoundId": -100, "RoundName": "R1 Bracket", "Type": 1},
        ]
        rounds = parse_division_plays(data)
        assert len(rounds) == 2
        types = {r.type for r in rounds}
        assert types == {"pool", "bracket"}
