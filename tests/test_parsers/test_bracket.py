"""Tests for scraper.parsers.bracket."""

from scraper.parsers.bracket import parse_brackets


class TestParseBrackets:
    def test_basic_bracket_match(self) -> None:
        data = [
            {
                "MatchId": -300,
                "HomeTeamId": 1,
                "AwayTeamId": 2,
                "HomeTeamName": "Team A",
                "AwayTeamName": "Team B",
                "CourtName": "Court 1",
                "MatchDate": "2025-03-09",
                "MatchTime": "10:00",
                "HomeSeed": 1,
                "AwaySeed": 4,
                "GroupId": -50,
                "GroupName": "Gold",
                "Order": 1,
                "IsFinished": True,
                "SetScores": [{"HomeScore": 25, "AwayScore": 20}],
                "Courts": [
                    {"CourtId": -10, "CourtName": "Court 1", "VideoLink": None}
                ],
            }
        ]
        matches = parse_brackets(data)
        assert len(matches) == 1
        m = matches[0]
        assert m.id == -300
        assert m.home_seed == 1
        assert m.away_seed == 4
        assert m.group_name == "Gold"
        assert m.order == 1
        assert len(m.scores) == 1
        assert len(m.courts) == 1
        assert m.courts[0].name == "Court 1"

    def test_empty_brackets(self) -> None:
        assert parse_brackets([]) == []

    def test_match_with_video_link(self) -> None:
        data = [
            {
                "MatchId": -400,
                "Courts": [
                    {"CourtId": -20, "CourtName": "C2", "VideoLink": "https://vid.example.com"}
                ],
            }
        ]
        matches = parse_brackets(data)
        assert matches[0].courts[0].video_link == "https://vid.example.com"

    def test_multiple_matches(self) -> None:
        data = [
            {"MatchId": -300, "GroupName": "Gold", "Order": 1},
            {"MatchId": -301, "GroupName": "Silver", "Order": 2},
        ]
        matches = parse_brackets(data)
        assert len(matches) == 2
        assert matches[0].group_name == "Gold"
        assert matches[1].group_name == "Silver"
