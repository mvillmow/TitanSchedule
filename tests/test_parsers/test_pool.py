"""Tests for scraper.parsers.pool."""

from scraper.parsers.pool import parse_pool_sheet


class TestParsePoolSheet:
    def test_full_pool(self) -> None:
        data = {
            "PlayId": -51151,
            "Name": "Pool A",
            "Teams": [
                {"TeamId": 1, "TeamName": "Team A", "ClubName": "Club A", "Seed": 1},
                {"TeamId": 2, "TeamName": "Team B", "ClubName": "Club B", "Seed": 2},
            ],
            "Matches": [
                {
                    "MatchId": -51190,
                    "HomeTeamId": 1,
                    "AwayTeamId": 2,
                    "HomeTeamName": "Team A",
                    "AwayTeamName": "Team B",
                    "WorkTeamId": None,
                    "WorkTeamName": "",
                    "CourtName": "Court 3",
                    "MatchDate": "2025-03-08",
                    "MatchTime": "08:00",
                    "SetScores": [
                        {"HomeScore": 25, "AwayScore": 18},
                        {"HomeScore": 25, "AwayScore": 21},
                    ],
                    "HomeSetsWon": 2,
                    "AwaySetsWon": 0,
                    "IsFinished": True,
                    "IsInProgress": False,
                }
            ],
            "Standings": [
                {"TeamId": 1, "TeamName": "Team A", "Rank": 1, "Wins": 1, "Losses": 0},
                {"TeamId": 2, "TeamName": "Team B", "Rank": 2, "Wins": 0, "Losses": 1},
            ],
        }
        pool = parse_pool_sheet(data)
        assert pool.play_id == -51151
        assert pool.name == "Pool A"
        assert len(pool.teams) == 2
        assert len(pool.matches) == 1
        assert pool.matches[0].id == -51190
        assert len(pool.matches[0].scores) == 2
        assert pool.matches[0].scores[0].home == 25
        assert pool.matches[0].is_finished is True
        assert len(pool.standings) == 2
        assert pool.standings[0].rank == 1

    def test_empty_pool(self) -> None:
        data = {"PlayId": -100, "Name": "Empty Pool"}
        pool = parse_pool_sheet(data)
        assert pool.matches == []
        assert pool.standings == []
        assert pool.teams == []

    def test_missing_team_fields(self) -> None:
        data = {
            "PlayId": -100,
            "Name": "Pool",
            "Teams": [{"TeamId": 1}],
        }
        pool = parse_pool_sheet(data)
        assert pool.teams[0].name == "Unknown"
        assert pool.teams[0].club == ""

    def test_match_without_scores(self) -> None:
        data = {
            "PlayId": -100,
            "Name": "Pool",
            "Matches": [
                {
                    "MatchId": -200,
                    "HomeTeamId": 1,
                    "AwayTeamId": 2,
                    "IsFinished": False,
                    "IsInProgress": False,
                }
            ],
        }
        pool = parse_pool_sheet(data)
        assert pool.matches[0].scores == []
        assert pool.matches[0].is_finished is False
