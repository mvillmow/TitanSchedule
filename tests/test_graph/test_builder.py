"""Tests for scraper.graph.builder."""

from scraper.graph.builder import GraphBuilder
from scraper.models import BracketMatch, Division, Match, Pool, PoolStanding, Round, SetScore, Team


class TestGraphBuilderEmptyDivision:
    """Test GraphBuilder with empty divisions."""

    def test_empty_division(self) -> None:
        """Build graph from an empty division."""
        division = Division(id=1, name="Empty")
        builder = GraphBuilder()
        builder.build(division)
        assert len(builder.nodes) == 0
        assert len(builder.edges) == 0

    def test_division_with_teams_no_matches(self) -> None:
        """Division with teams but no matches creates start/end nodes only."""
        division = Division(
            id=1,
            name="14s",
            teams={
                1: Team(id=1, name="Team A", seed=1),
                2: Team(id=2, name="Team B", seed=2),
            },
        )
        builder = GraphBuilder()
        builder.build(division)
        # Should have start and end nodes for each team
        assert "start_1" in builder.nodes
        assert "start_2" in builder.nodes
        assert "end_1" in builder.nodes
        assert "end_2" in builder.nodes
        # Start nodes should be in phase 0
        assert builder.nodes["start_1"].phase == 0
        assert builder.nodes["start_2"].phase == 0
        # End nodes should be in phase 1
        assert builder.nodes["end_1"].phase == 1
        assert builder.nodes["end_2"].phase == 1
        # With no matches, no edges are wired (early return)
        assert len(builder.edges) == 0


class TestGraphBuilderSimplePool:
    """Test GraphBuilder with single pool."""

    def test_simple_pool(self) -> None:
        """Build graph from a division with one pool and two teams."""
        division = Division(
            id=1,
            name="14s",
            rounds=[Round(id=-100, name="Round 1", short_name="R1P1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    teams=[
                        Team(id=1, name="Team A", seed=1),
                        Team(id=2, name="Team B", seed=2),
                    ],
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="Team A",
                            away_team_name="Team B",
                            date="2025-03-08",
                            time="08:00",
                            is_finished=True,
                            home_sets_won=2,
                            away_sets_won=0,
                            scores=[
                                SetScore(home=25, away=18),
                                SetScore(home=25, away=21),
                            ],
                        )
                    ],
                    standings=[
                        PoolStanding(
                            team_id=1, team_name="Team A", rank=1, wins=1, losses=0
                        ),
                        PoolStanding(
                            team_id=2, team_name="Team B", rank=2, wins=0, losses=1
                        ),
                    ],
                )
            ],
            teams={
                1: Team(id=1, name="Team A", seed=1),
                2: Team(id=2, name="Team B", seed=2),
            },
        )
        builder = GraphBuilder()
        builder.build(division)

        # Assert start nodes exist
        assert "start_1" in builder.nodes
        assert "start_2" in builder.nodes

        # Assert match node exists
        assert "match_-200" in builder.nodes
        match_node = builder.nodes["match_-200"]
        assert match_node.type == "match"
        assert match_node.phase == 1
        assert match_node.data["status"] == "final"
        assert match_node.data["home_team_id"] == 1
        assert match_node.data["away_team_id"] == 2

        # Assert port nodes exist
        assert "port_-200_home" in builder.nodes
        assert "port_-200_away" in builder.nodes
        assert "port_-200_work" in builder.nodes

        # Assert end nodes exist
        assert "end_1" in builder.nodes
        assert "end_2" in builder.nodes
        end_node_1 = builder.nodes["end_1"]
        assert end_node_1.data["wins"] == 1
        assert end_node_1.data["losses"] == 0
        assert end_node_1.data["rank"] == 1

        # Assert edges exist for both teams
        team_1_edges = [e for e in builder.edges if e.team_id == 1]
        team_2_edges = [e for e in builder.edges if e.team_id == 2]
        assert len(team_1_edges) >= 2  # start→match, match→end
        assert len(team_2_edges) >= 2

    def test_pool_match_status_final(self) -> None:
        """Pool match with is_finished=True should have status 'final'."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="A",
                            away_team_name="B",
                            date="2025-03-08",
                            time="08:00",
                            is_finished=True,
                        )
                    ],
                )
            ],
            teams={1: Team(id=1, name="A"), 2: Team(id=2, name="B")},
        )
        builder = GraphBuilder()
        builder.build(division)
        assert builder.nodes["match_-200"].data["status"] == "final"

    def test_pool_match_status_in_progress(self) -> None:
        """Pool match with is_in_progress=True should have status 'in_progress'."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="A",
                            away_team_name="B",
                            date="2025-03-08",
                            time="08:00",
                            is_in_progress=True,
                        )
                    ],
                )
            ],
            teams={1: Team(id=1, name="A"), 2: Team(id=2, name="B")},
        )
        builder = GraphBuilder()
        builder.build(division)
        assert builder.nodes["match_-200"].data["status"] == "in_progress"

    def test_pool_match_status_scheduled(self) -> None:
        """Match with both teams and no finish state should be 'scheduled'."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="A",
                            away_team_name="B",
                            date="2025-03-08",
                            time="08:00",
                        )
                    ],
                )
            ],
            teams={1: Team(id=1, name="A"), 2: Team(id=2, name="B")},
        )
        builder = GraphBuilder()
        builder.build(division)
        assert builder.nodes["match_-200"].data["status"] == "scheduled"

    def test_conditional_match_missing_away_team(self) -> None:
        """Match with missing away_team should have status 'conditional'."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=None,
                            home_team_name="A",
                            away_team_name="",
                            date="2025-03-08",
                            time="08:00",
                        )
                    ],
                )
            ],
            teams={1: Team(id=1, name="A")},
        )
        builder = GraphBuilder()
        builder.build(division)
        assert builder.nodes["match_-200"].data["status"] == "conditional"

    def test_conditional_match_missing_home_team(self) -> None:
        """Match with missing home_team should have status 'conditional'."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=None,
                            away_team_id=2,
                            home_team_name="",
                            away_team_name="B",
                            date="2025-03-08",
                            time="08:00",
                        )
                    ],
                )
            ],
            teams={2: Team(id=2, name="B")},
        )
        builder = GraphBuilder()
        builder.build(division)
        assert builder.nodes["match_-200"].data["status"] == "conditional"


class TestGraphBuilderBracketMatches:
    """Test GraphBuilder with bracket matches."""

    def test_bracket_match(self) -> None:
        """Build graph including bracket matches."""
        division = Division(
            id=1,
            name="14s",
            rounds=[
                Round(id=-100, name="Pool", type="pool"),
                Round(
                    id=-200, name="Bracket", type="bracket", group_id=-50, group_name="Gold"
                ),
            ],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    teams=[
                        Team(id=1, name="Team A", seed=1),
                        Team(id=2, name="Team B", seed=2),
                    ],
                    matches=[
                        Match(
                            id=-201,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="Team A",
                            away_team_name="Team B",
                            date="2025-03-08",
                            time="08:00",
                            is_finished=True,
                            home_sets_won=2,
                            away_sets_won=0,
                        )
                    ],
                    standings=[
                        PoolStanding(team_id=1, team_name="Team A", rank=1, wins=1, losses=0),
                        PoolStanding(team_id=2, team_name="Team B", rank=2, wins=0, losses=1),
                    ],
                )
            ],
            bracket_matches=[
                BracketMatch(
                    id=-300,
                    home_team_id=1,
                    away_team_id=2,
                    home_team_name="Team A",
                    away_team_name="Team B",
                    home_seed=1,
                    away_seed=2,
                    group_id=-50,
                    group_name="Gold",
                    date="2025-03-09",
                    time="09:00",
                    is_finished=True,
                    home_sets_won=2,
                    away_sets_won=1,
                )
            ],
            teams={
                1: Team(id=1, name="Team A", seed=1),
                2: Team(id=2, name="Team B", seed=2),
            },
        )
        builder = GraphBuilder()
        builder.build(division)

        # Assert bracket match node exists
        assert "match_-300" in builder.nodes
        bracket_node = builder.nodes["match_-300"]
        assert bracket_node.type == "match"
        assert bracket_node.data["status"] == "final"

        # Bracket match should be in phase 2 (after pool phase)
        assert bracket_node.phase == 2


class TestGraphBuilderMultipleRounds:
    """Test GraphBuilder with multiple rounds."""

    def test_multiple_rounds_chronological_phases(self) -> None:
        """Multiple rounds create multiple phases in chronological order."""
        division = Division(
            id=1,
            name="14s",
            rounds=[
                Round(id=-100, name="Round 1", type="pool"),
                Round(id=-200, name="Round 2", type="pool"),
            ],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    teams=[Team(id=1, name="Team A", seed=1)],
                    matches=[
                        Match(
                            id=-1001,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="Team A",
                            away_team_name="Team B",
                            date="2025-03-08",
                            time="08:00",
                        )
                    ],
                ),
                Pool(
                    play_id=-200,
                    name="Pool B",
                    teams=[Team(id=1, name="Team A")],
                    matches=[
                        Match(
                            id=-1002,
                            home_team_id=1,
                            away_team_id=3,
                            home_team_name="Team A",
                            away_team_name="Team C",
                            date="2025-03-09",
                            time="08:00",
                        )
                    ],
                ),
            ],
            teams={
                1: Team(id=1, name="Team A", seed=1),
                2: Team(id=2, name="Team B", seed=2),
                3: Team(id=3, name="Team C", seed=3),
            },
        )
        builder = GraphBuilder()
        builder.build(division)

        # Pool match should be in phase 1
        assert builder.nodes["match_-1001"].phase == 1

        # Round 2 match should be in phase 2
        assert builder.nodes["match_-1002"].phase == 2


class TestGraphBuilderWorkTeams:
    """Test GraphBuilder with work teams."""

    def test_work_team_edges(self) -> None:
        """Work teams get edges in the graph."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    teams=[
                        Team(id=1, name="Team A"),
                        Team(id=2, name="Team B"),
                        Team(id=3, name="Team C"),
                    ],
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            work_team_id=3,
                            home_team_name="Team A",
                            away_team_name="Team B",
                            work_team_name="Team C",
                            date="2025-03-08",
                            time="08:00",
                        )
                    ],
                )
            ],
            teams={
                1: Team(id=1, name="Team A"),
                2: Team(id=2, name="Team B"),
                3: Team(id=3, name="Team C"),
            },
        )
        builder = GraphBuilder()
        builder.build(division)

        # Work team should have edges
        work_edges = [e for e in builder.edges if e.team_id == 3]
        assert len(work_edges) >= 1

        # Verify that one of the edges involves the work port
        has_work_port = any("port_-200_work" in [e.source, e.target] for e in work_edges)
        assert has_work_port


class TestGraphBuilderEdgeStructure:
    """Test GraphBuilder edge wiring and structure."""

    def test_edge_from_start_to_first_match(self) -> None:
        """First match should have edge from start node."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="A",
                            away_team_name="B",
                            date="2025-03-08",
                            time="08:00",
                        )
                    ],
                )
            ],
            teams={1: Team(id=1, name="A"), 2: Team(id=2, name="B")},
        )
        builder = GraphBuilder()
        builder.build(division)

        # Team 1 should have an edge from start to first match
        start_edges = [e for e in builder.edges if e.source == "start_1"]
        assert len(start_edges) >= 1
        assert any(e.target == "port_-200_home" for e in start_edges)

    def test_edge_from_match_to_end(self) -> None:
        """Last match should have edge to end node."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="A",
                            away_team_name="B",
                            date="2025-03-08",
                            time="08:00",
                        )
                    ],
                )
            ],
            teams={1: Team(id=1, name="A"), 2: Team(id=2, name="B")},
        )
        builder = GraphBuilder()
        builder.build(division)

        # Team 1 should have an edge from match port to end
        end_edges = [e for e in builder.edges if e.target == "end_1"]
        assert len(end_edges) >= 1


class TestGraphBuilderStartNodeData:
    """Test start node data structure."""

    def test_start_node_contains_team_data(self) -> None:
        """Start node should contain team metadata."""
        team = Team(id=42, name="Super Team", club="Awesome Club", seed=3)
        division = Division(
            id=1,
            name="Test",
            teams={42: team},
        )
        builder = GraphBuilder()
        builder.build(division)

        start_node = builder.nodes["start_42"]
        assert start_node.data["team_id"] == 42
        assert start_node.data["team_name"] == "Super Team"
        assert start_node.data["club"] == "Awesome Club"
        assert start_node.data["seed"] == 3


class TestGraphBuilderEndNodeData:
    """Test end node data structure."""

    def test_end_node_contains_record_and_rank(self) -> None:
        """End node should contain W-L record and rank."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="A",
                            away_team_name="B",
                            date="2025-03-08",
                            time="08:00",
                            is_finished=True,
                            home_sets_won=2,
                            away_sets_won=0,
                        ),
                        Match(
                            id=-201,
                            home_team_id=1,
                            away_team_id=3,
                            home_team_name="A",
                            away_team_name="C",
                            date="2025-03-08",
                            time="09:00",
                            is_finished=True,
                            home_sets_won=2,
                            away_sets_won=1,
                        ),
                    ],
                    standings=[
                        PoolStanding(team_id=1, team_name="A", rank=1, wins=2, losses=0),
                        PoolStanding(team_id=2, team_name="B", rank=2, wins=0, losses=1),
                        PoolStanding(team_id=3, team_name="C", rank=3, wins=0, losses=1),
                    ],
                )
            ],
            teams={
                1: Team(id=1, name="A"),
                2: Team(id=2, name="B"),
                3: Team(id=3, name="C"),
            },
        )
        builder = GraphBuilder()
        builder.build(division)

        end_node = builder.nodes["end_1"]
        assert end_node.data["wins"] == 2
        assert end_node.data["losses"] == 0
        assert end_node.data["rank"] == 1


class TestGraphBuilderMatchNodeMetadata:
    """Test match node metadata."""

    def test_match_node_has_team_and_court_data(self) -> None:
        """Match node should contain match metadata."""
        division = Division(
            id=1,
            name="Test",
            rounds=[Round(id=-100, name="R1", type="pool")],
            pools=[
                Pool(
                    play_id=-100,
                    name="Pool A",
                    matches=[
                        Match(
                            id=-200,
                            home_team_id=1,
                            away_team_id=2,
                            home_team_name="Team Alpha",
                            away_team_name="Team Beta",
                            work_team_id=3,
                            work_team_name="Team Gamma",
                            court="Court 3",
                            date="2025-03-08",
                            time="10:30",
                        )
                    ],
                )
            ],
            teams={
                1: Team(id=1, name="Team Alpha"),
                2: Team(id=2, name="Team Beta"),
                3: Team(id=3, name="Team Gamma"),
            },
        )
        builder = GraphBuilder()
        builder.build(division)

        match_node = builder.nodes["match_-200"]
        assert match_node.data["home_team_id"] == 1
        assert match_node.data["away_team_id"] == 2
        assert match_node.data["work_team_id"] == 3
        assert match_node.data["home_team_name"] == "Team Alpha"
        assert match_node.data["away_team_name"] == "Team Beta"
        assert match_node.data["work_team_name"] == "Team Gamma"
        assert match_node.data["court"] == "Court 3"
        assert match_node.data["date"] == "2025-03-08"
        assert match_node.data["time"] == "10:30"


class TestGraphBuilderDivisionName:
    """Test division_name tracking."""

    def test_division_name_set_during_build(self) -> None:
        """GraphBuilder should track the division name."""
        division = Division(id=1, name="U14 Girls")
        builder = GraphBuilder()
        builder.build(division)
        assert builder.division_name == "U14 Girls"
