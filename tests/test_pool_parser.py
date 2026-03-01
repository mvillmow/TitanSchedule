import pytest

from scraper.models import MatchStatus
from scraper.parsers.pool import PoolParser

POOLSHEET_DATA = {
    "Pool": {
        "PlayId": -51151,
        "FullName": "Pool 1",
        "ShortName": "P1",
        "CompleteFullName": "Round 1 Pool 1",
        "CompleteShortName": "R1P1",
        "MatchDescription": "2 of 3 to 25(15)",
        "Courts": [{"CourtId": -52201, "Name": "Court 3", "VideoLink": "https://video.example.com"}],
        "Teams": [
            {
                "TeamId": 197665,
                "TeamName": "GRV 12 Black",
                "TeamText": "GRV 12 Black (HO) (1)",
                "TeamCode": "g12grbvc1ho",
                "MatchesWon": 2,
                "MatchesLost": 1,
                "MatchPercent": 0.6667,
                "SetsWon": 4,
                "SetsLost": 2,
                "SetPercent": 0.6667,
                "PointRatio": 1.0703,
                "FinishRank": 2,
                "FinishRankText": "2nd",
                "Club": {"ClubId": 31156, "Name": "Gym Rats Volleyball"},
            },
            {
                "TeamId": 216147,
                "TeamName": "513VB 12-4",
                "TeamText": "513VB 12-4 (OV) (11)",
                "TeamCode": "513vb124ov",
                "MatchesWon": 0,
                "MatchesLost": 3,
                "MatchPercent": 0.0,
                "SetsWon": 1,
                "SetsLost": 6,
                "SetPercent": 0.1429,
                "PointRatio": 0.7,
                "FinishRank": 4,
                "FinishRankText": "4th",
                "Club": None,
            },
        ],
    },
    "Matches": [
        {
            "MatchId": -51190,
            "MatchFullName": "Match 1",
            "MatchShortName": "M1",
            "FirstTeamId": 197665,
            "FirstTeamName": "GRV 12 Black",
            "FirstTeamText": "GRV 12 Black (HO) (1)",
            "FirstTeamWon": True,
            "SecondTeamId": 216147,
            "SecondTeamName": "513VB 12-4",
            "SecondTeamText": "513VB 12-4 (OV) (11)",
            "SecondTeamWon": False,
            "HasScores": True,
            "Sets": [
                {"FirstTeamScore": 25, "SecondTeamScore": 18, "ScoreText": "25-18", "IsDecidingSet": False},
                {"FirstTeamScore": 25, "SecondTeamScore": 18, "ScoreText": "25-18", "IsDecidingSet": False},
                {"FirstTeamScore": None, "SecondTeamScore": None, "ScoreText": "", "IsDecidingSet": True},
            ],
            "WorkTeamId": 186913,
            "WorkTeamText": "LAVA 12-1 A (OV) (10)",
            "Court": {"CourtId": -52201, "Name": "Court 3", "VideoLink": "https://video.example.com"},
            "ScheduledStartDateTime": "2026-02-07T07:30:00",
            "ScheduledEndDateTime": "2026-02-07T08:29:59",
        },
        {
            "MatchId": -51191,
            "MatchFullName": "Match 2",
            "MatchShortName": "M2",
            "FirstTeamId": 197665,
            "FirstTeamName": "GRV 12 Black",
            "FirstTeamText": "GRV 12 Black (HO) (1)",
            "FirstTeamWon": None,
            "SecondTeamId": 197666,
            "SecondTeamName": "Other Team",
            "SecondTeamText": "Other Team (HO) (2)",
            "SecondTeamWon": None,
            "HasScores": False,
            "Sets": [],
            "WorkTeamId": None,
            "WorkTeamText": None,
            "Court": None,
            "ScheduledStartDateTime": "2026-02-07T09:00:00",
            "ScheduledEndDateTime": None,
        },
    ],
    "FutureRoundMatches": [],
}


class TestPoolParser:
    def _parser(self, data=None):
        return PoolParser(data or POOLSHEET_DATA, "KEY", 193839)

    def test_parses_pool_metadata(self):
        pool = self._parser().parse()
        assert pool.play_id == -51151
        assert pool.full_name == "Pool 1"
        assert pool.short_name == "P1"
        assert pool.complete_name == "Round 1 Pool 1"
        assert pool.complete_short_name == "R1P1"
        assert pool.match_description == "2 of 3 to 25(15)"

    def test_parses_team_standings(self):
        pool = self._parser().parse()
        assert len(pool.teams) == 2
        grv = pool.teams[0]
        assert grv.team.team_id == 197665
        assert grv.team.name == "GRV 12 Black"
        assert grv.matches_won == 2
        assert grv.matches_lost == 1
        assert grv.match_percent == pytest.approx(0.6667)
        assert grv.sets_won == 4
        assert grv.set_percent == pytest.approx(0.6667)
        assert grv.point_ratio == pytest.approx(1.0703)
        assert grv.finish_rank == 2
        assert grv.finish_rank_text == "2nd"

    def test_parses_matches(self):
        pool = self._parser().parse()
        assert len(pool.matches) == 2

    def test_set_scores(self):
        pool = self._parser().parse()
        m = pool.matches[0]
        assert len(m.set_scores) == 2  # Third set (null scores) excluded
        assert m.set_scores[0].home_score == 25
        assert m.set_scores[0].away_score == 18
        assert m.set_scores[0].score_text == "25-18"
        assert m.set_scores[0].is_deciding_set is False

    def test_match_status_finished(self):
        pool = self._parser().parse()
        assert pool.matches[0].status == MatchStatus.FINISHED
        assert pool.matches[0].home_won is True

    def test_match_status_scheduled(self):
        pool = self._parser().parse()
        assert pool.matches[1].status == MatchStatus.SCHEDULED
        assert pool.matches[1].home_won is None

    def test_match_status_in_progress(self):
        data = {
            "Pool": {
                "PlayId": -1,
                "FullName": "Pool 1",
                "ShortName": "P1",
                "MatchDescription": "",
                "Courts": [],
                "Teams": [],
            },
            "Matches": [
                {
                    "MatchId": -999,
                    "MatchFullName": "Match 1",
                    "MatchShortName": "M1",
                    "FirstTeamId": 1,
                    "FirstTeamName": "Team A",
                    "FirstTeamText": "Team A",
                    "FirstTeamWon": None,
                    "SecondTeamId": 2,
                    "SecondTeamName": "Team B",
                    "SecondTeamText": "Team B",
                    "HasScores": True,
                    "Sets": [],
                    "Court": None,
                    "ScheduledStartDateTime": None,
                    "ScheduledEndDateTime": None,
                }
            ],
            "FutureRoundMatches": [],
        }
        pool = self._parser(data).parse()
        assert pool.matches[0].status == MatchStatus.IN_PROGRESS

    def test_seed_extraction(self):
        pool = self._parser().parse()
        assert pool.teams[0].team.seed == 1
        assert pool.teams[1].team.seed == 11

    def test_seed_extraction_no_seed(self):
        data = {**POOLSHEET_DATA}
        data["Pool"] = {
            **POOLSHEET_DATA["Pool"],
            "Teams": [
                {
                    "TeamId": 1,
                    "TeamName": "NoSeed Team",
                    "TeamText": "NoSeed Team",
                    "TeamCode": "ns",
                    "MatchesWon": 0, "MatchesLost": 0,
                    "MatchPercent": 0.0, "SetsWon": 0, "SetsLost": 0,
                    "SetPercent": 0.0, "PointRatio": 0.0,
                    "FinishRank": None, "FinishRankText": None,
                    "Club": None,
                }
            ],
        }
        pool = self._parser(data).parse()
        assert pool.teams[0].team.seed is None

    def test_court_parsing(self):
        pool = self._parser().parse()
        assert pool.courts[0].name == "Court 3"
        assert pool.courts[0].court_id == -52201
        assert pool.courts[0].video_link == "https://video.example.com"

    def test_match_court(self):
        pool = self._parser().parse()
        assert pool.matches[0].court is not None
        assert pool.matches[0].court.name == "Court 3"

    def test_match_no_court(self):
        pool = self._parser().parse()
        assert pool.matches[1].court is None

    def test_work_team(self):
        pool = self._parser().parse()
        assert pool.matches[0].work_team_text == "LAVA 12-1 A (OV) (10)"
        assert pool.matches[0].work_team_id == 186913

    def test_club_parsing(self):
        pool = self._parser().parse()
        assert pool.teams[0].team.club_name == "Gym Rats Volleyball"
        assert pool.teams[0].team.club_id == 31156
        # Team with None club
        assert pool.teams[1].team.club_name is None

    def test_play_id_on_match(self):
        pool = self._parser().parse()
        assert pool.matches[0].play_id == -51151

    def test_scheduled_datetime(self):
        pool = self._parser().parse()
        m = pool.matches[0]
        assert m.scheduled_start is not None
        assert m.scheduled_start.year == 2026
        assert m.scheduled_start.month == 2
        assert m.scheduled_start.day == 7

    def test_home_away_teams(self):
        pool = self._parser().parse()
        m = pool.matches[0]
        assert m.home_team is not None
        assert m.home_team.team_id == 197665
        assert m.away_team is not None
        assert m.away_team.team_id == 216147
