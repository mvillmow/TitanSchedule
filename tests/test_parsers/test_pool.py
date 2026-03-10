"""Tests for scraper.parsers.pool."""

from scraper.parsers.pool import parse_pool_sheet


class TestParsePoolSheet:
    def test_full_pool(self) -> None:
        """Parse a poolsheet with teams, matches, and standings."""
        data = {
            "Pool": {
                "PlayId": -52135,
                "FullName": "Pool 1",
                "Teams": [
                    {
                        "TeamId": 1,
                        "TeamName": "Team A",
                        "Club": {"ClubId": 100, "Name": "Club A"},
                        "Seed": 1,
                        "FinishRank": 1,
                        "MatchesWon": 2,
                        "MatchesLost": 0,
                    },
                    {
                        "TeamId": 2,
                        "TeamName": "Team B",
                        "Club": {"ClubId": 200, "Name": "Club B"},
                        "Seed": 2,
                        "FinishRank": 2,
                        "MatchesWon": 0,
                        "MatchesLost": 2,
                    },
                ],
            },
            "Matches": [
                {
                    "MatchId": -51190,
                    "FirstTeamId": 1,
                    "SecondTeamId": 2,
                    "FirstTeamName": "Team A",
                    "SecondTeamName": "Team B",
                    "FirstTeamWon": True,
                    "SecondTeamWon": False,
                    "HasScores": True,
                    "TypeOfOutcome": 2,
                    "Sets": [
                        {"FirstTeamScore": 25, "SecondTeamScore": 18},
                        {"FirstTeamScore": 25, "SecondTeamScore": 21},
                    ],
                    "WorkTeamId": None,
                    "WorkTeamText": "",
                    "Court": {"CourtId": -100, "Name": "Court 3"},
                    "ScheduledStartDateTime": "2025-03-08T08:00:00",
                    "ScheduledEndDateTime": "2025-03-08T08:59:59",
                }
            ],
            "FutureRoundMatches": [],
        }
        pool = parse_pool_sheet(data)
        assert pool.play_id == -52135
        assert pool.name == "Pool 1"
        assert len(pool.teams) == 2
        assert pool.teams[0].club == "Club A"
        assert len(pool.matches) == 1
        assert pool.matches[0].id == -51190
        assert len(pool.matches[0].scores) == 2
        assert pool.matches[0].scores[0].home == 25
        assert pool.matches[0].scores[0].away == 18
        assert pool.matches[0].is_finished is True
        assert pool.matches[0].home_sets_won == 2
        assert pool.matches[0].away_sets_won == 0
        assert pool.matches[0].court == "Court 3"
        assert pool.matches[0].date == "2025-03-08"
        assert pool.matches[0].time == "08:00"
        # Standings from team FinishRank
        assert len(pool.standings) == 2
        assert pool.standings[0].rank == 1

    def test_empty_pool(self) -> None:
        """Pool with no matches and no teams."""
        data = {"Pool": {"PlayId": -100, "FullName": "Empty Pool"}, "Matches": []}
        pool = parse_pool_sheet(data)
        assert pool.matches == []
        assert pool.standings == []
        assert pool.teams == []

    def test_missing_club_field(self) -> None:
        """Teams without Club object get empty club name."""
        data = {
            "Pool": {
                "PlayId": -100,
                "FullName": "Pool",
                "Teams": [{"TeamId": 1, "TeamName": "Solo"}],
            },
            "Matches": [],
        }
        pool = parse_pool_sheet(data)
        assert pool.teams[0].name == "Solo"
        assert pool.teams[0].club == ""

    def test_match_without_scores(self) -> None:
        """Scheduled match with no scores."""
        data = {
            "Pool": {"PlayId": -100, "FullName": "Pool"},
            "Matches": [
                {
                    "MatchId": -200,
                    "FirstTeamId": 1,
                    "SecondTeamId": 2,
                    "FirstTeamName": "A",
                    "SecondTeamName": "B",
                    "FirstTeamWon": False,
                    "SecondTeamWon": False,
                    "HasScores": False,
                    "TypeOfOutcome": 0,
                    "Sets": [],
                    "Court": {"Name": "Court 1"},
                    "ScheduledStartDateTime": "2025-03-08T10:00:00",
                }
            ],
        }
        pool = parse_pool_sheet(data)
        assert pool.matches[0].scores == []
        assert pool.matches[0].is_finished is False
        assert pool.matches[0].is_in_progress is False

    def test_in_progress_match(self) -> None:
        """Match currently in progress."""
        data = {
            "Pool": {"PlayId": -100, "FullName": "Pool"},
            "Matches": [
                {
                    "MatchId": -200,
                    "FirstTeamId": 1,
                    "SecondTeamId": 2,
                    "TypeOfOutcome": 1,
                    "HasScores": True,
                    "Sets": [{"FirstTeamScore": 15, "SecondTeamScore": 12}],
                    "Court": {"Name": "Court 1"},
                    "ScheduledStartDateTime": "2025-03-08T10:00:00",
                }
            ],
        }
        pool = parse_pool_sheet(data)
        assert pool.matches[0].is_in_progress is True
        assert pool.matches[0].is_finished is False

    def test_work_team(self) -> None:
        """Match with a work team."""
        data = {
            "Pool": {"PlayId": -100, "FullName": "Pool"},
            "Matches": [
                {
                    "MatchId": -200,
                    "FirstTeamId": 1,
                    "SecondTeamId": 2,
                    "WorkTeamId": 3,
                    "WorkTeamText": "Team C (NC)",
                    "TypeOfOutcome": 0,
                    "HasScores": False,
                    "Sets": [],
                    "Court": {"Name": "Court 1"},
                    "ScheduledStartDateTime": "2025-03-08T10:00:00",
                }
            ],
        }
        pool = parse_pool_sheet(data)
        assert pool.matches[0].work_team_id == 3
        assert pool.matches[0].work_team_name == "Team C (NC)"

    def test_legacy_flat_format(self) -> None:
        """Backward compat: if data has no Pool wrapper, treat as pool directly."""
        data = {
            "PlayId": -100,
            "FullName": "Pool A",
            "Teams": [{"TeamId": 1, "TeamName": "Team A"}],
        }
        pool = parse_pool_sheet(data)
        assert pool.play_id == -100
        assert pool.name == "Pool A"
        assert len(pool.teams) == 1
