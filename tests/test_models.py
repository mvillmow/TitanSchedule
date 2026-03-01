
import pytest

from scraper.models import (
    Court,
    Division,
    FollowOnEdge,
    Match,
    MatchStatus,
    PlayType,
    Pool,
    SetScore,
    Team,
    TeamStanding,
)


class TestSetScore:
    def test_frozen(self):
        score = SetScore(home_score=25, away_score=18, score_text="25-18", is_deciding_set=False)
        with pytest.raises((AttributeError, TypeError)):
            score.home_score = 0  # type: ignore[misc]

    def test_construction(self):
        score = SetScore(25, 18, "25-18", False)
        assert score.home_score == 25
        assert score.away_score == 18
        assert score.score_text == "25-18"
        assert score.is_deciding_set is False


class TestCourt:
    def test_frozen(self):
        court = Court(court_id=-52201, name="Court 3", video_link=None)
        with pytest.raises((AttributeError, TypeError)):
            court.name = "Court 4"  # type: ignore[misc]

    def test_optional_video_link(self):
        court = Court(-52201, "Court 3", None)
        assert court.video_link is None
        court2 = Court(-52201, "Court 3", "https://example.com/video")
        assert court2.video_link == "https://example.com/video"


class TestTeam:
    def test_defaults(self):
        team = Team(team_id=12345, name="Test Team", display_text="Test Team (HO) (1)", code="testcode")
        assert team.club_name is None
        assert team.seed is None
        assert team.aes_url is None

    def test_mutable(self):
        team = Team(team_id=12345, name="Test Team", display_text="Test", code="tc")
        team.seed = 3
        assert team.seed == 3


class TestTeamStanding:
    def test_construction(self):
        team = Team(1, "Team A", "Team A (HO) (1)", "ta")
        standing = TeamStanding(
            team=team,
            matches_won=2,
            matches_lost=1,
            match_percent=0.667,
            sets_won=4,
            sets_lost=2,
            set_percent=0.667,
            point_ratio=1.07,
            finish_rank=2,
            finish_rank_text="2nd",
        )
        assert standing.finish_rank == 2
        assert standing.finish_rank_text == "2nd"

    def test_unfinished_pool_none_rank(self):
        team = Team(1, "Team A", "Team A", "ta")
        standing = TeamStanding(
            team=team,
            matches_won=0,
            matches_lost=0,
            match_percent=0.0,
            sets_won=0,
            sets_lost=0,
            set_percent=0.0,
            point_ratio=0.0,
            finish_rank=None,
            finish_rank_text=None,
        )
        assert standing.finish_rank is None


class TestMatch:
    def test_defaults(self):
        match = Match(match_id=-51190, match_name="Match 1", match_short_name="M1")
        assert match.status == MatchStatus.SCHEDULED
        assert match.set_scores == []
        assert match.home_team is None
        assert match.away_team is None
        assert match.has_scores is False
        assert match.home_won is None

    def test_with_teams(self):
        home = Team(1, "Home Team", "Home Team", "ht")
        away = Team(2, "Away Team", "Away Team", "at")
        match = Match(
            match_id=-51190,
            match_name="Match 1",
            match_short_name="M1",
            home_team=home,
            away_team=away,
            status=MatchStatus.FINISHED,
            has_scores=True,
            home_won=True,
        )
        assert match.home_won is True
        assert match.status == MatchStatus.FINISHED


class TestPool:
    def test_defaults(self):
        pool = Pool(
            play_id=-51151,
            full_name="Pool 1",
            short_name="P1",
            complete_name="Round 1 Pool 1",
            complete_short_name="R1P1",
            round_id=-50094,
            round_name="Round 1",
            match_description="2 of 3 to 25(15)",
        )
        assert pool.teams == []
        assert pool.matches == []
        assert pool.courts == []
        assert pool.order == 0


class TestMatchStatus:
    def test_values(self):
        assert MatchStatus.SCHEDULED.value == "scheduled"
        assert MatchStatus.IN_PROGRESS.value == "in_progress"
        assert MatchStatus.FINISHED.value == "finished"
        assert MatchStatus.FORFEIT.value == "forfeit"


class TestPlayType:
    def test_values(self):
        assert PlayType.POOL.value == 0
        assert PlayType.BRACKET.value == 1


class TestDivision:
    def test_defaults(self):
        div = Division(
            division_id=199194,
            name="12 Girls",
            event_key="PTAwMDAwNDE4MzE90",
            event_name="Test Event",
        )
        assert div.rounds == []
        assert div.follow_on_edges == []
        assert div.all_teams == []
        assert div.aes_url is None
        assert div.scraped_at is None


class TestFollowOnEdge:
    def test_construction(self):
        edge = FollowOnEdge(
            source_play_id=-51151,
            source_rank=1,
            source_text="1st R1P1",
            target_match_id=-52001,
            target_text="1st R1P1",
        )
        assert edge.source_rank == 1
        assert edge.target_match_id == -52001
