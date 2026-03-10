"""Tests for scraper.models."""

from scraper.models import (
    BracketMatch,
    Court,
    Division,
    FollowOnEdge,
    Match,
    Pool,
    Round,
    SetScore,
    Team,
)


class TestTeam:
    def test_construction(self) -> None:
        t = Team(id=12345, name="Club Titans 14-1", club="Club Titans", seed=3)
        assert t.id == 12345
        assert t.name == "Club Titans 14-1"
        assert t.club == "Club Titans"
        assert t.seed == 3

    def test_defaults(self) -> None:
        t = Team(id=1, name="T")
        assert t.club == ""
        assert t.seed is None


class TestSetScore:
    def test_construction(self) -> None:
        s = SetScore(home=25, away=18)
        assert s.home == 25
        assert s.away == 18


class TestMatch:
    def test_negative_id(self) -> None:
        m = Match(id=-51190)
        assert m.id == -51190

    def test_defaults(self) -> None:
        m = Match(id=-1)
        assert m.home_team_id is None
        assert m.scores == []
        assert m.is_finished is False
        assert m.is_in_progress is False


class TestBracketMatch:
    def test_inherits_match(self) -> None:
        bm = BracketMatch(id=-100, home_seed=1, away_seed=2, group_name="Gold")
        assert bm.id == -100
        assert bm.home_seed == 1
        assert bm.group_name == "Gold"
        assert bm.courts == []

    def test_with_courts(self) -> None:
        c = Court(id=-10, name="Court 1", video_link="https://example.com")
        bm = BracketMatch(id=-1, courts=[c])
        assert len(bm.courts) == 1
        assert bm.courts[0].video_link == "https://example.com"


class TestRound:
    def test_pool_type(self) -> None:
        r = Round(id=-100, name="Round 1", type="pool")
        assert r.type == "pool"

    def test_bracket_type(self) -> None:
        r = Round(id=-200, name="Gold Bracket", type="bracket")
        assert r.type == "bracket"

    def test_default_type(self) -> None:
        r = Round(id=-1, name="R")
        assert r.type == "pool"

    def test_play_id_and_order(self) -> None:
        r = Round(id=-100, name="R1", play_id=-51151, order=1, date="2025-03-08")
        assert r.play_id == -51151
        assert r.order == 1
        assert r.date == "2025-03-08"

    def test_defaults_new_fields(self) -> None:
        r = Round(id=-1, name="R")
        assert r.play_id is None
        assert r.order == 0
        assert r.date == ""


class TestFollowOnEdge:
    def test_construction(self) -> None:
        e = FollowOnEdge(
            source_round_id=-100, source_rank=1, target_round_id=-200, target_slot="R1P1"
        )
        assert e.source_rank == 1
        assert e.target_slot == "R1P1"


class TestPool:
    def test_empty_pool(self) -> None:
        p = Pool(play_id=-51151, name="Pool A")
        assert p.matches == []
        assert p.standings == []
        assert p.teams == []


class TestDivision:
    def test_construction(self) -> None:
        d = Division(id=199189, name="14s Power League")
        assert d.id == 199189
        assert d.rounds == []
        assert d.teams == {}
        assert d.dates == []
        assert d.is_finished is False

    def test_with_teams(self) -> None:
        t = Team(id=1, name="T1")
        d = Division(id=1, name="D", teams={1: t})
        assert d.teams[1].name == "T1"
