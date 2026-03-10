"""Tests for TeamScheduleExporter."""

from __future__ import annotations

from scraper.graph.builder import Edge, GraphBuilder, Node
from scraper.graph.team_exporter import TeamScheduleExporter
from scraper.models import Division


class TestTeamScheduleExporter:
    """Test cases for TeamScheduleExporter.export()."""

    def _make_builder(self) -> GraphBuilder:
        """Helper to create a populated GraphBuilder for tests."""
        builder = GraphBuilder()
        builder.division_name = "14s"

        # Add start ranking nodes
        builder.nodes["start_1"] = Node(
            id="start_1",
            type="ranking",
            phase=0,
            data={
                "team_id": 1,
                "team_name": "Team A",
                "club": "Club A",
                "seed": 1,
            },
        )
        builder.nodes["start_2"] = Node(
            id="start_2",
            type="ranking",
            phase=0,
            data={
                "team_id": 2,
                "team_name": "Team B",
                "club": "Club B",
                "seed": 2,
            },
        )

        # Add match node
        builder.nodes["match_-200"] = Node(
            id="match_-200",
            type="match",
            phase=1,
            data={
                "match_id": -200,
                "date": "2025-03-08",
                "time": "08:00",
                "court": "Court 3",
                "round_name": "Pool A",
                "group_name": "",
                "status": "final",
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team_name": "Team A",
                "away_team_name": "Team B",
                "work_team_id": None,
                "work_team_name": "",
                "scores": [[25, 18], [25, 21]],
                "home_sets_won": 2,
                "away_sets_won": 0,
            },
        )

        # Add port nodes
        builder.nodes["port_-200_home"] = Node(
            id="port_-200_home",
            type="port",
            phase=1,
            data={"match_id": -200, "role": "home"},
        )
        builder.nodes["port_-200_away"] = Node(
            id="port_-200_away",
            type="port",
            phase=1,
            data={"match_id": -200, "role": "away"},
        )

        # Add end ranking nodes
        builder.nodes["end_1"] = Node(
            id="end_1",
            type="ranking",
            phase=2,
            data={
                "team_id": 1,
                "team_name": "Team A",
                "wins": 1,
                "losses": 0,
                "rank": 1,
            },
        )
        builder.nodes["end_2"] = Node(
            id="end_2",
            type="ranking",
            phase=2,
            data={
                "team_id": 2,
                "team_name": "Team B",
                "wins": 0,
                "losses": 1,
                "rank": 2,
            },
        )

        # Add edges
        builder.edges = [
            Edge(
                source="start_1",
                target="port_-200_home",
                team_id=1,
                team_name="Team A",
                role="home",
            ),
            Edge(
                source="start_2",
                target="port_-200_away",
                team_id=2,
                team_name="Team B",
                role="away",
            ),
            Edge(
                source="port_-200_home",
                target="end_1",
                team_id=1,
                team_name="Team A",
                role="home",
            ),
            Edge(
                source="port_-200_away",
                target="end_2",
                team_id=2,
                team_name="Team B",
                role="away",
            ),
        ]

        return builder

    def test_basic_export(self) -> None:
        """Test basic export with two teams and one match."""
        builder = self._make_builder()
        division = Division(id=1, name="14s")
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)

        # Check division name
        assert result["division"] == "14s"

        # Check dates
        assert "2025-03-08" in result["dates"]
        assert len(result["dates"]) == 1

        # Check teams exist
        assert "1" in result["teams"]
        assert "2" in result["teams"]

        # Check Team A
        team_a = result["teams"]["1"]
        assert team_a["name"] == "Team A"
        assert team_a["club"] == "Club A"
        assert team_a["seed"] == 1
        assert team_a["rank"] == 1
        assert team_a["record"] == "1-0"
        assert len(team_a["games"]) == 1

        # Check Team A's game
        game = team_a["games"][0]
        assert game["opponent"] == "Team B"
        assert game["opponent_id"] == "2"
        assert game["opponent_text"] is None
        assert game["date"] == "2025-03-08"
        assert game["time"] == "08:00"
        assert game["court"] == "Court 3"
        assert game["role"] == "home"
        assert game["round"] == "Pool A"
        assert game["status"] == "final"
        assert game["scores"] == [[25, 18], [25, 21]]
        assert game["won"] is True

    def test_away_team_perspective(self) -> None:
        """Test that away team sees correct opponent and won=False."""
        builder = self._make_builder()
        division = Division(id=1, name="14s")
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)

        # Check Team B
        team_b = result["teams"]["2"]
        assert team_b["name"] == "Team B"
        assert team_b["seed"] == 2
        assert team_b["rank"] == 2
        assert team_b["record"] == "0-1"
        assert len(team_b["games"]) == 1

        # Check Team B's game
        game = team_b["games"][0]
        assert game["opponent"] == "Team A"
        assert game["opponent_id"] == "1"
        assert game["role"] == "away"
        assert game["status"] == "final"
        assert game["won"] is False

    def test_conditional_game(self) -> None:
        """Test conditional match with missing opponent."""
        builder = GraphBuilder()
        builder.division_name = "16s"

        # Add start node
        builder.nodes["start_5"] = Node(
            id="start_5",
            type="ranking",
            phase=0,
            data={
                "team_id": 5,
                "team_name": "Team E",
                "club": "Club E",
                "seed": 1,
            },
        )

        # Add conditional match (no away team)
        builder.nodes["match_-300"] = Node(
            id="match_-300",
            type="match",
            phase=1,
            data={
                "match_id": -300,
                "date": "2025-03-09",
                "time": "10:00",
                "court": "Court 1",
                "round_name": "Bracket",
                "group_name": "Gold",
                "status": "conditional",
                "home_team_id": 5,
                "away_team_id": None,
                "home_team_name": "Team E",
                "away_team_name": "",
                "work_team_id": None,
                "work_team_name": "",
                "scores": [],
                "home_sets_won": 0,
                "away_sets_won": 0,
            },
        )

        builder.nodes["port_-300_home"] = Node(
            id="port_-300_home",
            type="port",
            phase=1,
            data={"match_id": -300, "role": "home"},
        )

        # End node
        builder.nodes["end_5"] = Node(
            id="end_5",
            type="ranking",
            phase=2,
            data={
                "team_id": 5,
                "team_name": "Team E",
                "wins": 0,
                "losses": 0,
                "rank": None,
            },
        )

        builder.edges = [
            Edge(
                source="start_5",
                target="port_-300_home",
                team_id=5,
                team_name="Team E",
                role="home",
            ),
            Edge(
                source="port_-300_home",
                target="end_5",
                team_id=5,
                team_name="Team E",
                role="home",
            ),
        ]

        division = Division(id=1, name="16s")
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)

        team_e = result["teams"]["5"]
        assert len(team_e["games"]) == 1
        game = team_e["games"][0]
        assert game["status"] == "conditional"
        assert game["opponent"] is None
        assert game["opponent_id"] is None
        assert game["opponent_text"] == "TBD"
        assert game["won"] is None

    def test_conditional_game_with_follow_on_text(self) -> None:
        """Conditional match with descriptive away_team_name uses it as opponent_text."""
        builder = GraphBuilder()
        builder.division_name = "16s"
        builder.nodes["start_5"] = Node(
            id="start_5", type="ranking", phase=0,
            data={"team_id": 5, "team_name": "Team E", "club": "Club E", "seed": 1},
        )
        builder.nodes["match_-300"] = Node(
            id="match_-300", type="match", phase=1,
            data={
                "match_id": -300, "date": "2025-03-09", "time": "10:00",
                "court": "Court 1", "round_name": "Bracket", "group_name": "Gold",
                "status": "conditional", "home_team_id": 5, "away_team_id": None,
                "home_team_name": "Team E", "away_team_name": "1st R1P1",
                "work_team_id": None, "work_team_name": "",
                "scores": [], "home_sets_won": 0, "away_sets_won": 0,
            },
        )
        builder.nodes["port_-300_home"] = Node(
            id="port_-300_home", type="port", phase=1, data={"match_id": -300, "role": "home"},
        )
        builder.nodes["end_5"] = Node(
            id="end_5", type="ranking", phase=2,
            data={"team_id": 5, "team_name": "Team E", "wins": 0, "losses": 0, "rank": None},
        )
        builder.edges = [
            Edge(source="start_5", target="port_-300_home",
                 team_id=5, team_name="Team E", role="home"),
            Edge(source="port_-300_home", target="end_5",
                 team_id=5, team_name="Team E", role="home"),
        ]
        division = Division(id=1, name="16s")
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)
        game = result["teams"]["5"]["games"][0]
        assert game["opponent_text"] == "1st R1P1"
        assert game["opponent"] is None

    def test_work_team(self) -> None:
        """Test work team (ref) participation in a match."""
        builder = GraphBuilder()
        builder.division_name = "U12"

        # Add three teams
        for i in range(3):
            builder.nodes[f"start_{i}"] = Node(
                id=f"start_{i}",
                type="ranking",
                phase=0,
                data={
                    "team_id": i,
                    "team_name": f"Team {chr(65 + i)}",
                    "club": f"Club {chr(65 + i)}",
                    "seed": i + 1,
                },
            )

        # Match with work team
        builder.nodes["match_-400"] = Node(
            id="match_-400",
            type="match",
            phase=1,
            data={
                "match_id": -400,
                "date": "2025-03-10",
                "time": "09:00",
                "court": "Court 2",
                "round_name": "Pool",
                "group_name": "",
                "status": "final",
                "home_team_id": 0,
                "away_team_id": 1,
                "home_team_name": "Team A",
                "away_team_name": "Team B",
                "work_team_id": 2,
                "work_team_name": "Team C",
                "scores": [[25, 23], [26, 24]],
                "home_sets_won": 2,
                "away_sets_won": 0,
            },
        )

        # Port nodes for all three teams
        for role in ["home", "away", "work"]:
            builder.nodes[f"port_-400_{role}"] = Node(
                id=f"port_-400_{role}",
                type="port",
                phase=1,
                data={"match_id": -400, "role": role},
            )

        # End nodes
        for i in range(3):
            builder.nodes[f"end_{i}"] = Node(
                id=f"end_{i}",
                type="ranking",
                phase=2,
                data={
                    "team_id": i,
                    "team_name": f"Team {chr(65 + i)}",
                    "wins": 0,
                    "losses": 0,
                    "rank": None,
                },
            )

        # Edges
        builder.edges = [
            Edge(
                source="start_0",
                target="port_-400_home",
                team_id=0,
                team_name="Team A",
                role="home",
            ),
            Edge(
                source="start_1",
                target="port_-400_away",
                team_id=1,
                team_name="Team B",
                role="away",
            ),
            Edge(
                source="start_2",
                target="port_-400_work",
                team_id=2,
                team_name="Team C",
                role="work",
            ),
            Edge(
                source="port_-400_home",
                target="end_0",
                team_id=0,
                team_name="Team A",
                role="home",
            ),
            Edge(
                source="port_-400_away",
                target="end_1",
                team_id=1,
                team_name="Team B",
                role="away",
            ),
            Edge(
                source="port_-400_work",
                target="end_2",
                team_id=2,
                team_name="Team C",
                role="work",
            ),
        ]

        division = Division(id=1, name="U12")
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)

        # Check home team
        team_a = result["teams"]["0"]
        game_a = team_a["games"][0]
        assert game_a["role"] == "home"
        assert game_a["won"] is True
        assert team_a["record"] == "1-0"

        # Check away team
        team_b = result["teams"]["1"]
        game_b = team_b["games"][0]
        assert game_b["role"] == "away"
        assert game_b["won"] is False
        assert team_b["record"] == "0-1"

        # Check work team
        team_c = result["teams"]["2"]
        game_c = team_c["games"][0]
        assert game_c["role"] == "work"
        assert game_c["won"] is None
        assert game_c["opponent"] == "Team A vs Team B"
        # Work team should not count in record
        assert team_c["record"] == "0-0"

    def test_empty_graph(self) -> None:
        """Test export with empty graph."""
        builder = GraphBuilder()
        builder.division_name = "Empty"
        division = Division(id=1, name="Empty")
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)

        assert result["division"] == "Empty"
        assert result["teams"] == {}
        assert result["dates"] == []

    def test_multiple_games_per_team(self) -> None:
        """Test team with multiple games across different dates."""
        builder = GraphBuilder()
        builder.division_name = "18s"

        # Add two teams
        builder.nodes["start_10"] = Node(
            id="start_10",
            type="ranking",
            phase=0,
            data={
                "team_id": 10,
                "team_name": "Team X",
                "club": "Club X",
                "seed": 1,
            },
        )
        builder.nodes["start_11"] = Node(
            id="start_11",
            type="ranking",
            phase=0,
            data={
                "team_id": 11,
                "team_name": "Team Y",
                "club": "Club Y",
                "seed": 2,
            },
        )
        builder.nodes["start_12"] = Node(
            id="start_12",
            type="ranking",
            phase=0,
            data={
                "team_id": 12,
                "team_name": "Team Z",
                "club": "Club Z",
                "seed": 3,
            },
        )

        # Match 1 on Day 1
        builder.nodes["match_-500"] = Node(
            id="match_-500",
            type="match",
            phase=1,
            data={
                "match_id": -500,
                "date": "2025-03-15",
                "time": "08:00",
                "court": "Court A",
                "round_name": "R1",
                "group_name": "",
                "status": "final",
                "home_team_id": 10,
                "away_team_id": 11,
                "home_team_name": "Team X",
                "away_team_name": "Team Y",
                "work_team_id": None,
                "work_team_name": "",
                "scores": [[25, 10]],
                "home_sets_won": 1,
                "away_sets_won": 0,
            },
        )

        builder.nodes["port_-500_home"] = Node(
            id="port_-500_home", type="port", phase=1, data={}
        )
        builder.nodes["port_-500_away"] = Node(
            id="port_-500_away", type="port", phase=1, data={}
        )

        # Match 2 on Day 2
        builder.nodes["match_-501"] = Node(
            id="match_-501",
            type="match",
            phase=2,
            data={
                "match_id": -501,
                "date": "2025-03-16",
                "time": "09:00",
                "court": "Court B",
                "round_name": "R2",
                "group_name": "",
                "status": "scheduled",
                "home_team_id": 10,
                "away_team_id": 12,
                "home_team_name": "Team X",
                "away_team_name": "Team Z",
                "work_team_id": None,
                "work_team_name": "",
                "scores": [],
                "home_sets_won": 0,
                "away_sets_won": 0,
            },
        )

        builder.nodes["port_-501_home"] = Node(
            id="port_-501_home", type="port", phase=2, data={}
        )
        builder.nodes["port_-501_away"] = Node(
            id="port_-501_away", type="port", phase=2, data={}
        )

        # End nodes
        builder.nodes["end_10"] = Node(
            id="end_10",
            type="ranking",
            phase=3,
            data={
                "team_id": 10,
                "team_name": "Team X",
                "wins": 1,
                "losses": 0,
                "rank": 1,
            },
        )
        builder.nodes["end_11"] = Node(
            id="end_11",
            type="ranking",
            phase=3,
            data={
                "team_id": 11,
                "team_name": "Team Y",
                "wins": 0,
                "losses": 1,
                "rank": 2,
            },
        )
        builder.nodes["end_12"] = Node(
            id="end_12",
            type="ranking",
            phase=3,
            data={
                "team_id": 12,
                "team_name": "Team Z",
                "wins": 0,
                "losses": 0,
                "rank": 3,
            },
        )

        # Edges
        builder.edges = [
            # Match 1
            Edge(
                source="start_10",
                target="port_-500_home",
                team_id=10,
                team_name="Team X",
                role="home",
            ),
            Edge(
                source="start_11",
                target="port_-500_away",
                team_id=11,
                team_name="Team Y",
                role="away",
            ),
            # Match 2
            Edge(
                source="start_10",
                target="port_-501_home",
                team_id=10,
                team_name="Team X",
                role="home",
            ),
            Edge(
                source="start_12",
                target="port_-501_away",
                team_id=12,
                team_name="Team Z",
                role="away",
            ),
            # End
            Edge(
                source="port_-500_home",
                target="end_10",
                team_id=10,
                team_name="Team X",
                role="home",
            ),
            Edge(
                source="port_-500_away",
                target="end_11",
                team_id=11,
                team_name="Team Y",
                role="away",
            ),
            Edge(
                source="port_-501_home",
                target="end_10",
                team_id=10,
                team_name="Team X",
                role="home",
            ),
            Edge(
                source="port_-501_away",
                target="end_12",
                team_id=12,
                team_name="Team Z",
                role="away",
            ),
        ]

        division = Division(id=1, name="18s")
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)

        # Check dates
        assert set(result["dates"]) == {"2025-03-15", "2025-03-16"}

        # Check Team X has 2 games, sorted by date then time
        team_x = result["teams"]["10"]
        assert len(team_x["games"]) == 2
        assert team_x["games"][0]["date"] == "2025-03-15"
        assert team_x["games"][1]["date"] == "2025-03-16"
        assert team_x["record"] == "1-0"  # Only final game counted

    def test_scheduled_and_inprogress_games(self) -> None:
        """Test status values for scheduled and in-progress games."""
        builder = GraphBuilder()
        builder.division_name = "15s"

        # Add teams
        builder.nodes["start_20"] = Node(
            id="start_20",
            type="ranking",
            phase=0,
            data={
                "team_id": 20,
                "team_name": "Team P",
                "club": "Club P",
                "seed": None,
            },
        )
        builder.nodes["start_21"] = Node(
            id="start_21",
            type="ranking",
            phase=0,
            data={
                "team_id": 21,
                "team_name": "Team Q",
                "club": "Club Q",
                "seed": None,
            },
        )

        # Scheduled match
        builder.nodes["match_-600"] = Node(
            id="match_-600",
            type="match",
            phase=1,
            data={
                "match_id": -600,
                "date": "2025-03-20",
                "time": "10:00",
                "court": "Court 5",
                "round_name": "F",
                "group_name": "",
                "status": "scheduled",
                "home_team_id": 20,
                "away_team_id": 21,
                "home_team_name": "Team P",
                "away_team_name": "Team Q",
                "work_team_id": None,
                "work_team_name": "",
                "scores": [],
                "home_sets_won": 0,
                "away_sets_won": 0,
            },
        )

        builder.nodes["port_-600_home"] = Node(
            id="port_-600_home", type="port", phase=1, data={}
        )
        builder.nodes["port_-600_away"] = Node(
            id="port_-600_away", type="port", phase=1, data={}
        )

        # In-progress match
        builder.nodes["match_-601"] = Node(
            id="match_-601",
            type="match",
            phase=1,
            data={
                "match_id": -601,
                "date": "2025-03-20",
                "time": "11:00",
                "court": "Court 6",
                "round_name": "F",
                "group_name": "",
                "status": "in_progress",
                "home_team_id": 20,
                "away_team_id": 21,
                "home_team_name": "Team P",
                "away_team_name": "Team Q",
                "work_team_id": None,
                "work_team_name": "",
                "scores": [[15, 12]],
                "home_sets_won": 1,
                "away_sets_won": 0,
            },
        )

        builder.nodes["port_-601_home"] = Node(
            id="port_-601_home", type="port", phase=1, data={}
        )
        builder.nodes["port_-601_away"] = Node(
            id="port_-601_away", type="port", phase=1, data={}
        )

        # End nodes
        builder.nodes["end_20"] = Node(
            id="end_20",
            type="ranking",
            phase=2,
            data={
                "team_id": 20,
                "team_name": "Team P",
                "wins": 0,
                "losses": 0,
                "rank": None,
            },
        )
        builder.nodes["end_21"] = Node(
            id="end_21",
            type="ranking",
            phase=2,
            data={
                "team_id": 21,
                "team_name": "Team Q",
                "wins": 0,
                "losses": 0,
                "rank": None,
            },
        )

        builder.edges = [
            Edge(
                source="start_20",
                target="port_-600_home",
                team_id=20,
                team_name="Team P",
                role="home",
            ),
            Edge(
                source="start_21",
                target="port_-600_away",
                team_id=21,
                team_name="Team Q",
                role="away",
            ),
            Edge(
                source="start_20",
                target="port_-601_home",
                team_id=20,
                team_name="Team P",
                role="home",
            ),
            Edge(
                source="start_21",
                target="port_-601_away",
                team_id=21,
                team_name="Team Q",
                role="away",
            ),
            Edge(
                source="port_-600_home",
                target="end_20",
                team_id=20,
                team_name="Team P",
                role="home",
            ),
            Edge(
                source="port_-600_away",
                target="end_21",
                team_id=21,
                team_name="Team Q",
                role="away",
            ),
            Edge(
                source="port_-601_home",
                target="end_20",
                team_id=20,
                team_name="Team P",
                role="home",
            ),
            Edge(
                source="port_-601_away",
                target="end_21",
                team_id=21,
                team_name="Team Q",
                role="away",
            ),
        ]

        division = Division(id=1, name="15s")
        exporter = TeamScheduleExporter()
        result = exporter.export(builder, division)

        team_p = result["teams"]["20"]
        assert len(team_p["games"]) == 2

        scheduled_game = team_p["games"][0]
        assert scheduled_game["status"] == "scheduled"
        assert scheduled_game["won"] is None
        assert scheduled_game["scores"] == []

        inprogress_game = team_p["games"][1]
        assert inprogress_game["status"] == "in_progress"
        assert inprogress_game["won"] is None  # Not final
        assert inprogress_game["scores"] == [[15, 12]]

        # Record only counts final games
        assert team_p["record"] == "0-0"
