"""Tests for scraper.parsers.bracket."""

from scraper.parsers.bracket import parse_brackets


class TestParseBrackets:
    def test_basic_bracket_match(self) -> None:
        data = [
            {
                "MatchId": -300,
                "FirstTeamId": 1,
                "SecondTeamId": 2,
                "FirstTeamName": "Team A",
                "SecondTeamName": "Team B",
                "Court": {"CourtId": -10, "Name": "Court 1"},
                "ScheduledStartDateTime": "2025-03-09T10:00:00",
                "FirstTeamSeed": 1,
                "SecondTeamSeed": 4,
                "GroupId": -50,
                "GroupName": "Gold",
                "Order": 1,
                "HasScores": True,
                "FirstTeamWon": True,
                "SecondTeamWon": False,
                "TypeOfOutcome": 2,
                "Sets": [{"FirstTeamScore": 25, "SecondTeamScore": 20}],
                "Courts": [
                    {"CourtId": -10, "Name": "Court 1", "VideoLink": None}
                ],
            }
        ]
        matches = parse_brackets(data)
        assert len(matches) == 1
        m = matches[0]
        assert m.id == -300
        assert m.home_team_id == 1
        assert m.away_team_id == 2
        assert m.home_seed == 1
        assert m.away_seed == 4
        assert m.group_name == "Gold"
        assert m.order == 1
        assert m.court == "Court 1"
        assert m.date == "2025-03-09"
        assert m.time == "10:00"
        assert m.is_finished is True
        assert m.home_sets_won == 1
        assert m.away_sets_won == 0
        assert len(m.scores) == 1
        assert m.scores[0].home == 25
        assert m.scores[0].away == 20
        assert len(m.courts) == 1
        assert m.courts[0].name == "Court 1"

    def test_empty_brackets(self) -> None:
        assert parse_brackets([]) == []

    def test_match_with_video_link(self) -> None:
        data = [
            {
                "MatchId": -400,
                "Courts": [
                    {"CourtId": -20, "Name": "C2", "VideoLink": "https://vid.example.com"}
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

    def test_in_progress_match(self) -> None:
        data = [
            {
                "MatchId": -500,
                "FirstTeamId": 1,
                "SecondTeamId": 2,
                "TypeOfOutcome": 1,
                "HasScores": True,
                "Sets": [{"FirstTeamScore": 15, "SecondTeamScore": 12}],
            }
        ]
        matches = parse_brackets(data)
        assert matches[0].is_in_progress is True
        assert matches[0].is_finished is False

    def test_scheduled_match(self) -> None:
        data = [
            {
                "MatchId": -600,
                "FirstTeamId": 1,
                "SecondTeamId": 2,
                "TypeOfOutcome": 0,
                "HasScores": False,
                "Sets": [],
                "ScheduledStartDateTime": "2025-03-09T14:00:00",
            }
        ]
        matches = parse_brackets(data)
        assert matches[0].is_finished is False
        assert matches[0].is_in_progress is False
        assert matches[0].date == "2025-03-09"
        assert matches[0].time == "14:00"

    def test_work_team(self) -> None:
        data = [
            {
                "MatchId": -700,
                "WorkTeamId": 3,
                "WorkTeamText": "Team C (NC)",
            }
        ]
        matches = parse_brackets(data)
        assert matches[0].work_team_id == 3
        assert matches[0].work_team_name == "Team C (NC)"
