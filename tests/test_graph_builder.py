"""Tests for DAG construction from a parsed Division."""
from datetime import datetime

from scraper.graph.builder import GraphBuilder
from scraper.models import (
    Bracket,
    BracketMatch,
    Division,
    FollowOnEdge,
    Match,
    MatchStatus,
    Pool,
    Round,
    Team,
    TeamStanding,
)


def make_team(team_id: int, name: str, seed: int) -> Team:
    return Team(team_id=team_id, name=name, display_text=f"{name} (HO) ({seed})",
                code=name.lower(), seed=seed)


def make_standing(team: Team, rank: int | None = None) -> TeamStanding:
    return TeamStanding(
        team=team,
        matches_won=2 if rank == 1 else 1,
        matches_lost=1 if rank == 1 else 2,
        match_percent=0.667 if rank == 1 else 0.333,
        sets_won=4, sets_lost=2, set_percent=0.667,
        point_ratio=1.07,
        finish_rank=rank,
        finish_rank_text=f"{rank}st" if rank == 1 else f"{rank}nd" if rank == 2 else f"{rank}rd" if rank == 3 else f"{rank}th",
    )


def make_match(match_id: int, home: Team, away: Team,
               status: MatchStatus = MatchStatus.SCHEDULED,
               home_won: bool | None = None,
               start: str | None = None,
               work_team_id: int | None = None) -> Match:
    dt = datetime.fromisoformat(start) if start else None
    return Match(
        match_id=match_id,
        match_name=f"Match {abs(match_id)}",
        match_short_name=f"M{abs(match_id)}",
        home_team=home,
        away_team=away,
        status=status,
        home_won=home_won,
        has_scores=(status == MatchStatus.FINISHED),
        scheduled_start=dt,
        play_id=-99,
        work_team_id=work_team_id,
    )


def make_division(num_teams: int = 4, num_matches_per_pool: int = 2) -> Division:
    """Build a minimal Division with one pool round and one bracket round."""
    teams = [make_team(i, f"Team {i}", i) for i in range(1, num_teams + 1)]

    # Pool with matches between each pair
    pool_matches = []
    for i in range(num_teams // 2):
        home = teams[i * 2]
        away = teams[i * 2 + 1]
        pool_matches.append(make_match(
            -(100 + i * 2),
            home, away,
            status=MatchStatus.FINISHED,
            home_won=(i % 2 == 0),
            start=f"2026-02-07T0{7 + i}:00:00",
        ))
        pool_matches.append(make_match(
            -(101 + i * 2),
            away, home,
            status=MatchStatus.SCHEDULED,
            start=f"2026-02-07T0{8 + i}:00:00",
        ))

    standings = [make_standing(t, rank=i + 1) for i, t in enumerate(teams)]

    pool = Pool(
        play_id=-51151,
        full_name="Pool 1",
        short_name="P1",
        complete_name="Round 1 Pool 1",
        complete_short_name="R1P1",
        round_id=-50094,
        round_name="Round 1",
        match_description="2 of 3 to 25(15)",
        teams=standings,
        matches=pool_matches,
    )

    round1 = Round(round_id=-50094, round_name="Round 1", pools=[pool])

    # Bracket with one match
    bracket_match = Match(
        match_id=-52001,
        match_name="Gold M1",
        match_short_name="GM1",
        home_team=None,
        away_team=None,
        home_placeholder="1st R1P1",
        away_placeholder="2nd R1P1",
        status=MatchStatus.SCHEDULED,
    )
    bm = BracketMatch(match=bracket_match, x=1.0, y=0.0, key=0)
    bracket = Bracket(
        play_id=-52481,
        full_name="Gold",
        short_name="G1",
        complete_name="Gold Bracket Gold",
        complete_short_name="GoldG1",
        round_id=-52479,
        round_name="Gold Bracket",
        group_name="GoldBracket",
        bracket_matches=[bm],
    )
    round2 = Round(round_id=-52479, round_name="Gold Bracket", brackets=[bracket])

    follow_on_edges = [
        FollowOnEdge(
            source_play_id=-51151,
            source_rank=1,
            source_text="1st R1P1",
            target_match_id=-52001,
            target_text="1st R1P1",
        ),
        FollowOnEdge(
            source_play_id=-51151,
            source_rank=2,
            source_text="2nd R1P1",
            target_match_id=-52001,
            target_text="2nd R1P1",
        ),
    ]

    return Division(
        division_id=193839,
        name="12 Girls",
        event_key="KEY",
        event_name="Test Event",
        rounds=[round1, round2],
        follow_on_edges=follow_on_edges,
        all_teams=teams,
        scraped_at=datetime.now(),
    )


def make_division_with_work_team() -> Division:
    """Division with 3 teams where one team works in each match."""
    teams = [make_team(i, f"Team {i}", i) for i in range(1, 4)]
    t1, t2, t3 = teams

    # 3-team pool: each pair plays, 3rd team works
    pool_matches = [
        make_match(-100, t1, t2, work_team_id=3, start="2026-02-07T07:00:00"),
        make_match(-101, t2, t3, work_team_id=1, start="2026-02-07T08:00:00"),
        make_match(-102, t1, t3, work_team_id=2, start="2026-02-07T09:00:00"),
    ]

    standings = [make_standing(t, rank=i + 1) for i, t in enumerate(teams)]
    pool = Pool(
        play_id=-51151,
        full_name="Pool 1",
        short_name="P1",
        complete_name="Round 1 Pool 1",
        complete_short_name="R1P1",
        round_id=-50094,
        round_name="Round 1",
        match_description="2 of 3 to 25(15)",
        teams=standings,
        matches=pool_matches,
    )
    round1 = Round(round_id=-50094, round_name="Round 1", pools=[pool])

    return Division(
        division_id=100,
        name="Test Division",
        event_key="KEY",
        event_name="Test Event",
        rounds=[round1],
        follow_on_edges=[],
        all_teams=teams,
        scraped_at=datetime.now(),
    )


class TestRankingNodes:
    def test_start_ranking_nodes_count(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        start_nodes = [n for n in nodes if n.node_type == "ranking" and n.phase == 0]
        assert len(start_nodes) == 4

    def test_end_ranking_nodes_count(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        end_nodes = [n for n in nodes if n.node_type == "ranking" and n.phase != 0]
        assert len(end_nodes) == 4

    def test_start_ranking_node_ids(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        start_ids = {n.id for n in nodes if n.node_type == "ranking" and n.phase == 0}
        expected = {f"ranking_start_{i}" for i in range(1, 5)}
        assert start_ids == expected

    def test_end_ranking_node_ids(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        end_ids = {n.id for n in nodes if n.node_type == "ranking" and n.phase != 0}
        expected = {f"ranking_end_{i}" for i in range(1, 5)}
        assert end_ids == expected

    def test_start_ranking_node_label(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        node = next(n for n in nodes if n.id == "ranking_start_1")
        assert node.label == "Team 1"
        assert node.sublabel == "Seed 1"

    def test_start_ranking_node_seed_sublabel(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        for i in range(1, 5):
            node = next(n for n in nodes if n.id == f"ranking_start_{i}")
            assert f"Seed {i}" in node.sublabel

    def test_end_ranking_node_record_finished(self):
        """End ranking nodes should show win-loss record for finished matches."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        end_nodes = {n.id: n for n in nodes if n.node_type == "ranking" and n.phase != 0}
        # At least some teams should have records
        records = [n.record for n in end_nodes.values() if n.record]
        assert len(records) > 0
        # Each record should be in "W-L" format
        for r in records:
            parts = r.split("-")
            assert len(parts) == 2
            assert all(p.isdigit() for p in parts)

    def test_start_ranking_phase_is_zero(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        start_nodes = [n for n in nodes if n.node_type == "ranking" and "start" in n.id]
        assert all(n.phase == 0 for n in start_nodes)

    def test_end_ranking_phase_is_last(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        max_phase = max(n.phase for n in nodes)
        end_nodes = [n for n in nodes if n.node_type == "ranking" and "end" in n.id]
        assert all(n.phase == max_phase for n in end_nodes)


class TestMatchNodes:
    def test_match_nodes_count(self):
        """Should have one match node per match, no seed/placement nodes."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_nodes = [n for n in nodes if n.node_type == "match"]
        # 4 pool matches + 1 bracket match = 5
        assert len(match_nodes) == 5

    def test_no_seed_nodes(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        seed_nodes = [n for n in nodes if n.node_type == "seed"]
        assert len(seed_nodes) == 0

    def test_no_placement_nodes(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        placement_nodes = [n for n in nodes if n.node_type == "pool_placement"]
        assert len(placement_nodes) == 0

    def test_match_node_id_format(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_ids = {n.id for n in nodes if n.node_type == "match"}
        # All match node IDs should start with "match_"
        assert all(mid.startswith("match_") for mid in match_ids)

    def test_match_node_teams_have_roles(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_nodes = [n for n in nodes if n.node_type == "match"]
        for node in match_nodes:
            for team in node.teams:
                assert "role" in team
                assert team["role"] in ("home", "away", "work")

    def test_match_node_status_values(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_nodes = [n for n in nodes if n.node_type == "match"]
        statuses = {n.status for n in match_nodes}
        assert "finished" in statuses
        assert "scheduled" in statuses

    def test_pool_match_has_pool_name(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_nodes = [n for n in nodes if n.node_type == "match" and n.pool_name]
        assert len(match_nodes) == 4  # 4 pool matches

    def test_bracket_match_has_bracket_name(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_nodes = [n for n in nodes if n.node_type == "match" and n.bracket_name]
        assert len(match_nodes) == 1  # 1 bracket match


class TestEdges:
    def test_all_edges_are_team_flow(self):
        """In the model, edges should be team_flow or follow_on type."""
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        edge_types = {e.edge_type for e in edges}
        assert edge_types <= {"team_flow", "follow_on"}

    def test_edges_have_team_id(self):
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        # Every team_flow edge should have a team_id
        for edge in edges:
            assert edge.team_id is not None

    def test_edge_roles(self):
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        # Edges connecting to match nodes should have role set
        roles = {e.role for e in edges if e.role is not None}
        assert "home" in roles
        assert "away" in roles

    def test_each_team_has_correct_edge_count(self):
        """Each team should have at least (assigned_matches + 1) team_flow edges.
        Teams feeding unscheduled follow-on bracket matches get additional
        ranking_end edges — one per bracket port — so the count is higher."""
        div = make_division(num_teams=4)
        nodes, edges = GraphBuilder(div).build()

        # Count matches where the team is explicitly assigned (has a teams entry)
        match_nodes = [n for n in nodes if n.node_type == "match"]
        team_match_counts: dict[int, int] = {}
        for node in match_nodes:
            for team in node.teams:
                tid = team["id"]
                if tid is not None:
                    team_match_counts[tid] = team_match_counts.get(tid, 0) + 1

        # Only count team_flow edges
        team_edge_counts: dict[int, int] = {}
        for edge in edges:
            if edge.edge_type != "team_flow":
                continue
            tid = edge.team_id
            if tid is not None:
                team_edge_counts[tid] = team_edge_counts.get(tid, 0) + 1

        # Each team must have at least (assigned_matches + 1) team_flow edges.
        # Teams with follow-on unscheduled brackets will have more (one extra
        # ranking_end edge per bracket port connected).
        for team_id, match_count in team_match_counts.items():
            assert team_edge_counts.get(team_id, 0) >= match_count + 1, (
                f"Team {team_id}: expected at least {match_count + 1} edges, "
                f"got {team_edge_counts.get(team_id, 0)}"
            )

    def test_all_edges_active(self):
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        assert all(e.active for e in edges)

    def test_no_dangling_edges(self):
        """All edge source/target IDs should reference existing nodes."""
        div = make_division(num_teams=4)
        nodes, edges = GraphBuilder(div).build()
        node_ids = {n.id for n in nodes}
        for edge in edges:
            assert edge.source in node_ids, f"Edge source {edge.source!r} not in nodes"
            assert edge.target in node_ids, f"Edge target {edge.target!r} not in nodes"


class TestWorkTeam:
    def test_work_team_role_in_match(self):
        """Matches with work_team_id should include a work-role team entry."""
        div = make_division_with_work_team()
        nodes, _ = GraphBuilder(div).build()
        match_nodes = [n for n in nodes if n.node_type == "match"]
        work_team_matches = [
            n for n in match_nodes
            if any(t["role"] == "work" for t in n.teams)
        ]
        assert len(work_team_matches) == 3  # all 3 matches have a work team

    def test_work_team_edges(self):
        """Work team should have team_flow edges with role='work'."""
        div = make_division_with_work_team()
        _, edges = GraphBuilder(div).build()
        work_edges = [e for e in edges if e.role == "work"]
        assert len(work_edges) > 0


class TestPhaseOrdering:
    def test_start_ranking_before_matches(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        start_phases = {n.phase for n in nodes if n.node_type == "ranking" and "start" in n.id}
        match_phases = {n.phase for n in nodes if n.node_type == "match"}
        assert max(start_phases) < min(match_phases)

    def test_matches_before_end_ranking(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_phases = {n.phase for n in nodes if n.node_type == "match"}
        end_phases = {n.phase for n in nodes if n.node_type == "ranking" and "end" in n.id}
        assert max(match_phases) < min(end_phases)

    def test_timeslot_grouping(self):
        """Matches at the same start time in the same round share a phase."""
        teams = [make_team(i, f"Team {i}", i) for i in range(1, 5)]
        # Two matches at the same start time
        pool_matches = [
            make_match(-100, teams[0], teams[1], start="2026-02-07T09:00:00"),
            make_match(-101, teams[2], teams[3], start="2026-02-07T09:00:00"),  # same time
            make_match(-102, teams[0], teams[2], start="2026-02-07T10:00:00"),  # different time
        ]
        standings = [make_standing(t, rank=i + 1) for i, t in enumerate(teams)]
        pool = Pool(
            play_id=-51151,
            full_name="Pool 1", short_name="P1",
            complete_name="Round 1 Pool 1", complete_short_name="R1P1",
            round_id=-50094, round_name="Round 1",
            match_description="",
            teams=standings,
            matches=pool_matches,
        )
        div = Division(
            division_id=1, name="Test", event_key="KEY", event_name="Test",
            rounds=[Round(round_id=-50094, round_name="Round 1", pools=[pool])],
            all_teams=teams,
        )
        nodes, _ = GraphBuilder(div).build()
        match_nodes = {n.id: n for n in nodes if n.node_type == "match"}
        # First two matches (same time) should share a phase
        assert match_nodes["match_-100"].phase == match_nodes["match_-101"].phase
        # Third match (different time) should have a different phase
        assert match_nodes["match_-102"].phase != match_nodes["match_-100"].phase


class TestDAGProperties:
    def test_no_duplicate_nodes(self):
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        ids = [n.id for n in nodes]
        assert len(ids) == len(set(ids))

    def test_no_cycles(self):
        """Topological sort must succeed (no cycles = DAG property)."""
        div = make_division(num_teams=4)
        nodes, edges = GraphBuilder(div).build()
        node_ids = {n.id for n in nodes}

        # Build adjacency list
        adj: dict[str, list[str]] = {n.id: [] for n in nodes}
        for e in edges:
            if e.source in adj and e.target in adj:
                adj[e.source].append(e.target)

        # Kahn's algorithm
        in_degree: dict[str, int] = {n: 0 for n in node_ids}
        for _src, targets in adj.items():
            for t in targets:
                in_degree[t] = in_degree.get(t, 0) + 1

        queue = [n for n in node_ids if in_degree.get(n, 0) == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        assert visited == len(node_ids), "Graph has a cycle"

    def test_global_row_between_teams(self):
        """Match node globalRow should be average of its playing teams' rows."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_nodes = [n for n in nodes if n.node_type == "match"]
        for node in match_nodes:
            playing_teams = [t for t in node.teams if t["role"] in ("home", "away")]
            if len(playing_teams) == 2:
                # Both teams known — globalRow should be their average
                t1_id = playing_teams[0]["id"]
                t2_id = playing_teams[1]["id"]
                # Seeds are 1-indexed, rows are 0-indexed
                t1_row = t1_id - 1  # seed == team_id in our test data
                t2_row = t2_id - 1
                expected = (t1_row + t2_row) / 2.0
                assert abs(node.global_row - expected) < 0.01, (
                    f"Node {node.id}: expected row {expected}, got {node.global_row}"
                )


def make_division_two_days() -> Division:
    """Division with matches on two different dates — should produce one intermediate ranking."""
    teams = [make_team(i, f"Team {i}", i) for i in range(1, 3)]
    t1, t2 = teams

    # Day 1 matches
    pool_matches_day1 = [
        make_match(-100, t1, t2, status=MatchStatus.FINISHED, home_won=True,
                   start="2026-01-31T09:00:00"),  # t1 wins
        make_match(-101, t2, t1, status=MatchStatus.FINISHED, home_won=False,
                   start="2026-01-31T10:00:00"),   # t1 wins again
    ]
    # Day 2 matches
    pool_matches_day2 = [
        make_match(-102, t2, t1, status=MatchStatus.FINISHED, home_won=True,
                   start="2026-02-01T09:00:00"),  # t2 wins
    ]
    all_matches = pool_matches_day1 + pool_matches_day2

    standings = [make_standing(t, rank=i + 1) for i, t in enumerate(teams)]
    pool = Pool(
        play_id=-51151,
        full_name="Pool 1", short_name="P1",
        complete_name="Round 1 Pool 1", complete_short_name="R1P1",
        round_id=-50094, round_name="Round 1",
        match_description="",
        teams=standings,
        matches=all_matches,
    )
    div = Division(
        division_id=1, name="Test", event_key="KEY", event_name="Test",
        rounds=[Round(round_id=-50094, round_name="Round 1", pools=[pool])],
        all_teams=teams,
    )
    return div


class TestIntermediateRankings:
    def test_intermediate_nodes_created_for_two_dates(self):
        """Division with 2 dates should produce intermediate ranking nodes for day 1."""
        div = make_division_two_days()
        nodes, _ = GraphBuilder(div).build()
        inter_nodes = [n for n in nodes if n.id.startswith("ranking_day_")]
        assert len(inter_nodes) > 0, "Expected at least one intermediate ranking node"

    def test_intermediate_nodes_one_per_team_per_boundary(self):
        """Each boundary date should have one node per team."""
        div = make_division_two_days()
        nodes, _ = GraphBuilder(div).build()
        inter_nodes = [n for n in nodes if n.id.startswith("ranking_day_")]
        # One boundary date (2026-01-31), 2 teams → 2 intermediate nodes
        assert len(inter_nodes) == 2

    def test_intermediate_node_record_scoped_to_date(self):
        """Intermediate ranking records should only reflect matches up to that date."""
        div = make_division_two_days()
        nodes, _ = GraphBuilder(div).build()
        # After day 1 (2026-01-31): t1 won 2, t2 won 0
        inter_nodes = {n.id: n for n in nodes if n.id.startswith("ranking_day_2026-01-31_")}
        assert len(inter_nodes) == 2
        # t1 (id=1) should have record "2-0" after day 1
        assert inter_nodes["ranking_day_2026-01-31_1"].record == "2-0"
        # t2 (id=2) should have record "0-2" after day 1
        assert inter_nodes["ranking_day_2026-01-31_2"].record == "0-2"

    def test_intermediate_nodes_phase_between_days(self):
        """Intermediate ranking phase should be between last day-1 match phase and first day-2 match phase."""
        div = make_division_two_days()
        nodes, _ = GraphBuilder(div).build()
        inter_nodes = [n for n in nodes if n.id.startswith("ranking_day_2026-01-31_")]
        day1_matches = [n for n in nodes if n.node_type == "match"
                        and n.time and n.time.startswith("2026-01-31")]
        day2_matches = [n for n in nodes if n.node_type == "match"
                        and n.time and n.time.startswith("2026-02-01")]
        assert inter_nodes, "Intermediate nodes missing"
        assert day1_matches, "Day 1 match nodes missing"
        assert day2_matches, "Day 2 match nodes missing"
        inter_phase = inter_nodes[0].phase
        max_day1_phase = max(n.phase for n in day1_matches)
        min_day2_phase = min(n.phase for n in day2_matches)
        assert max_day1_phase < inter_phase <= min_day2_phase

    def test_edges_route_through_intermediate_nodes(self):
        """Team flow edges should pass through intermediate ranking nodes at day boundaries."""
        div = make_division_two_days()
        nodes, edges = GraphBuilder(div).build()
        inter_node_ids = {n.id for n in nodes if n.id.startswith("ranking_day_")}
        # At least some edges should connect to or from intermediate nodes
        inter_connected = [
            e for e in edges
            if e.source in inter_node_ids or e.target in inter_node_ids
        ]
        assert len(inter_connected) > 0, "No edges connect to intermediate ranking nodes"

    def test_dag_acyclic_with_intermediate_nodes(self):
        """DAG must remain acyclic after adding intermediate ranking nodes."""
        div = make_division_two_days()
        nodes, edges = GraphBuilder(div).build()
        node_ids = {n.id for n in nodes}

        adj: dict[str, list[str]] = {n.id: [] for n in nodes}
        for e in edges:
            if e.source in adj and e.target in adj:
                adj[e.source].append(e.target)

        in_degree: dict[str, int] = {n: 0 for n in node_ids}
        for _src, targets in adj.items():
            for t in targets:
                in_degree[t] = in_degree.get(t, 0) + 1

        queue = [n for n in node_ids if in_degree.get(n, 0) == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        assert visited == len(node_ids), "Graph has a cycle with intermediate ranking nodes"

    def test_single_date_no_intermediate_nodes(self):
        """Division with all matches on one date should NOT produce intermediate nodes."""
        div = make_division(num_teams=4)  # all matches on same date
        nodes, _ = GraphBuilder(div).build()
        inter_nodes = [n for n in nodes if n.id.startswith("ranking_day_")]
        assert len(inter_nodes) == 0

    def test_no_orphan_intermediate_ranking_nodes(self):
        """Every intermediate ranking node must have at least one incoming and one outgoing edge."""
        div = make_division_two_days()
        nodes, edges = GraphBuilder(div).build()
        inter_node_ids = {n.id for n in nodes if n.id.startswith("ranking_day_")}
        if not inter_node_ids:
            return  # nothing to check

        sources = {e.source for e in edges}
        targets = {e.target for e in edges}

        for node_id in inter_node_ids:
            assert node_id in targets, (
                f"Intermediate ranking node {node_id!r} has no incoming edges (orphan)"
            )
            assert node_id in sources, (
                f"Intermediate ranking node {node_id!r} has no outgoing edges (orphan)"
            )


class TestEndRankingGlobalRow:
    def test_end_ranking_global_row_by_rank_not_seed(self):
        """End ranking nodes should be vertically ordered by W-L rank, not seed."""
        # Team 1 has seed=1 (better seed) but loses; Team 2 has seed=2 but wins.
        # After ranking by W-L: Team 2 should be rank 1 (row 0), Team 1 rank 2 (row 1).
        teams = [make_team(1, "Team 1", 1), make_team(2, "Team 2", 2)]
        t1, t2 = teams
        pool_matches = [
            make_match(-100, t2, t1, status=MatchStatus.FINISHED, home_won=True,
                       start="2026-02-07T07:00:00"),  # t2 wins
        ]
        standings = [make_standing(t, rank=i + 1) for i, t in enumerate(teams)]
        pool = Pool(
            play_id=-51151,
            full_name="Pool 1", short_name="P1",
            complete_name="Round 1 Pool 1", complete_short_name="R1P1",
            round_id=-50094, round_name="Round 1",
            match_description="",
            teams=standings,
            matches=pool_matches,
        )
        div = Division(
            division_id=1, name="Test", event_key="KEY", event_name="Test",
            rounds=[Round(round_id=-50094, round_name="Round 1", pools=[pool])],
            all_teams=teams,
        )
        nodes, _ = GraphBuilder(div).build()
        end_nodes = {n.id: n for n in nodes if "ranking_end" in n.id}
        # Team 2 won → ranked #1 → global_row = 0
        # Team 1 lost → ranked #2 → global_row = 1
        assert end_nodes["ranking_end_2"].global_row == 0.0, (
            f"Expected ranking_end_2 global_row=0.0 (rank #1), got {end_nodes['ranking_end_2'].global_row}"
        )
        assert end_nodes["ranking_end_1"].global_row == 1.0, (
            f"Expected ranking_end_1 global_row=1.0 (rank #2), got {end_nodes['ranking_end_1'].global_row}"
        )
        # Higher-ranked team should have lower global_row
        assert end_nodes["ranking_end_2"].global_row < end_nodes["ranking_end_1"].global_row


class TestEndRankingRecord:
    def test_win_loss_record_accuracy(self):
        """End ranking records should accurately reflect finished match results."""
        teams = [make_team(i, f"Team {i}", i) for i in range(1, 3)]
        t1, t2 = teams
        # Team 1 wins 2 matches, Team 2 loses 2
        pool_matches = [
            make_match(-100, t1, t2, status=MatchStatus.FINISHED, home_won=True,
                       start="2026-02-07T07:00:00"),
            make_match(-101, t1, t2, status=MatchStatus.FINISHED, home_won=True,
                       start="2026-02-07T08:00:00"),
        ]
        standings = [make_standing(t, rank=i + 1) for i, t in enumerate(teams)]
        pool = Pool(
            play_id=-51151,
            full_name="Pool 1", short_name="P1",
            complete_name="Round 1 Pool 1", complete_short_name="R1P1",
            round_id=-50094, round_name="Round 1",
            match_description="",
            teams=standings,
            matches=pool_matches,
        )
        div = Division(
            division_id=1, name="Test", event_key="KEY", event_name="Test",
            rounds=[Round(round_id=-50094, round_name="Round 1", pools=[pool])],
            all_teams=teams,
        )
        nodes, _ = GraphBuilder(div).build()
        end_nodes = {n.id: n for n in nodes if "ranking_end" in n.id}
        assert end_nodes["ranking_end_1"].record == "2-0"
        assert end_nodes["ranking_end_2"].record == "0-2"


class TestCompoundNodeStructure:
    def test_match_emits_parent_and_port_children(self):
        """Each match should emit 1 parent + 2 or 3 port children."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_parents = [n for n in nodes if n.node_type == "match"]
        port_nodes = [n for n in nodes if n.node_type == "port"]
        # Each match with home+away should have at least 2 ports
        assert len(port_nodes) >= len(match_parents) * 2

    def test_port_node_ids_follow_convention(self):
        """Port node IDs should be match_{id}_{role}."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        port_nodes = [n for n in nodes if n.node_type == "port"]
        for pn in port_nodes:
            assert "_home" in pn.id or "_away" in pn.id or "_work" in pn.id

    def test_port_nodes_have_parent_field(self):
        """Each port node should have parent set to its match parent's ID."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        port_nodes = [n for n in nodes if n.node_type == "port"]
        assert all(pn.parent is not None for pn in port_nodes)
        # Parent IDs should all be existing match parent nodes
        match_ids = {n.id for n in nodes if n.node_type == "match"}
        for pn in port_nodes:
            assert pn.parent in match_ids, f"Port {pn.id} parent {pn.parent!r} not in match nodes"

    def test_port_nodes_have_port_role(self):
        """Each port node should have port_role set."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        port_nodes = [n for n in nodes if n.node_type == "port"]
        for pn in port_nodes:
            assert pn.port_role in ("home", "away", "work"), f"Unexpected port_role: {pn.port_role}"

    def test_edges_target_port_nodes(self):
        """Edges connecting to match nodes should target port nodes, not parents."""
        div = make_division(num_teams=4)
        nodes, edges = GraphBuilder(div).build()
        match_ids = {n.id for n in nodes if n.node_type == "match"}
        # No edge should have its target be a match parent node
        for edge in edges:
            assert edge.target not in match_ids, (
                f"Edge {edge.id} targets match parent {edge.target!r} — should target a port"
            )
            assert edge.source not in match_ids, (
                f"Edge {edge.id} sourced from match parent {edge.source!r} — should source from a port"
            )

    def test_work_team_port_node_exists(self):
        """Matches with work team should have a work port child."""
        div = make_division_with_work_team()
        nodes, _ = GraphBuilder(div).build()
        work_ports = [n for n in nodes if n.node_type == "port" and n.port_role == "work"]
        assert len(work_ports) == 3  # 3 matches with work teams

    def test_bracket_match_placeholders(self):
        """Bracket matches with no assigned teams carry home/away placeholder text."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        bracket_parents = [
            n for n in nodes if n.node_type == "match" and n.bracket_name is not None
        ]
        assert len(bracket_parents) >= 1
        bracket_match = bracket_parents[0]
        # Bracket match has no real teams but has placeholder text
        if not bracket_match.teams:
            assert bracket_match.home_placeholder is not None or bracket_match.away_placeholder is not None

    def test_end_ranking_has_computed_ranking(self):
        """End ranking nodes should have a 1-based ranking field."""
        teams = [make_team(i, f"Team {i}", i) for i in range(1, 3)]
        t1, t2 = teams
        pool_matches = [
            make_match(-100, t1, t2, status=MatchStatus.FINISHED, home_won=True,
                       start="2026-02-07T07:00:00"),
        ]
        standings = [make_standing(t, rank=i + 1) for i, t in enumerate(teams)]
        pool = Pool(
            play_id=-51151,
            full_name="Pool 1", short_name="P1",
            complete_name="Round 1 Pool 1", complete_short_name="R1P1",
            round_id=-50094, round_name="Round 1",
            match_description="",
            teams=standings,
            matches=pool_matches,
        )
        div = Division(
            division_id=1, name="Test", event_key="KEY", event_name="Test",
            rounds=[Round(round_id=-50094, round_name="Round 1", pools=[pool])],
            all_teams=teams,
        )
        nodes, _ = GraphBuilder(div).build()
        end_nodes = {n.id: n for n in nodes if "ranking_end" in n.id}
        # Team 1 won → should be ranked #1
        assert end_nodes["ranking_end_1"].ranking == 1
        assert end_nodes["ranking_end_2"].ranking == 2

    def test_port_nodes_inherit_match_status(self):
        """Port nodes should have the same status as their parent match node."""
        div = make_division(num_teams=4)
        nodes, _ = GraphBuilder(div).build()
        match_nodes = {n.id: n for n in nodes if n.node_type == "match"}
        port_nodes = [n for n in nodes if n.node_type == "port"]
        for pn in port_nodes:
            parent_status = match_nodes[pn.parent].status
            assert pn.status == parent_status, (
                f"Port {pn.id} has status={pn.status!r} but parent match has {parent_status!r}"
            )

    def test_team_timeline_order_with_negative_ids(self):
        """Timeline tiebreaker must sort less-negative match IDs first (earlier in time)."""
        teams = [make_team(i, f"Team {i}", i) for i in range(1, 3)]
        t1, t2 = teams
        # Same timeslot — sort order must be determined by match_id tiebreaker.
        # Less-negative = earlier match in AES convention.
        pool_matches = [
            make_match(-200, t1, t2, start="2026-02-07T09:00:00"),  # more negative = later
            make_match(-100, t1, t2, start="2026-02-07T09:00:00"),  # less negative = earlier
        ]
        standings = [make_standing(t, rank=i + 1) for i, t in enumerate(teams)]
        pool = Pool(
            play_id=-51151,
            full_name="Pool 1", short_name="P1",
            complete_name="Round 1 Pool 1", complete_short_name="R1P1",
            round_id=-50094, round_name="Round 1",
            match_description="",
            teams=standings,
            matches=pool_matches,
        )
        div = Division(
            division_id=1, name="Test", event_key="KEY", event_name="Test",
            rounds=[Round(round_id=-50094, round_name="Round 1", pools=[pool])],
            all_teams=teams,
        )
        nodes, edges = GraphBuilder(div).build()
        # Find the edge from ranking_start_1 to first match port for team 1
        start_edge = next(
            e for e in edges
            if e.source == "ranking_start_1" and e.team_id == 1
        )
        # The first match visited should be match_-100 (less negative = earlier)
        assert "match_-100" in start_edge.target, (
            f"Expected first match to be match_-100 (less negative), got {start_edge.target!r}"
        )

    def test_dag_acyclic_with_port_nodes(self):
        """DAG must remain acyclic after adding port nodes."""
        div = make_division(num_teams=4)
        nodes, edges = GraphBuilder(div).build()
        node_ids = {n.id for n in nodes}

        adj: dict[str, list[str]] = {n.id: [] for n in nodes}
        for e in edges:
            if e.source in adj and e.target in adj:
                adj[e.source].append(e.target)

        in_degree: dict[str, int] = {n: 0 for n in node_ids}
        for _src, targets in adj.items():
            for t in targets:
                in_degree[t] = in_degree.get(t, 0) + 1

        queue = [n for n in node_ids if in_degree.get(n, 0) == 0]
        visited = 0
        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        assert visited == len(node_ids), "Graph has a cycle after adding port nodes"


class TestFollowOnEdges:
    def test_follow_on_edges_created(self):
        """Follow-on edges connect pool teams to unscheduled bracket matches."""
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        fo = [e for e in edges if e.edge_type == "follow_on"]
        assert len(fo) > 0

    def test_follow_on_edge_count(self):
        """4 teams × 1 target match × 2 ports = 8 follow-on edges."""
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        fo = [e for e in edges if e.edge_type == "follow_on"]
        assert len(fo) == 8

    def test_follow_on_edge_type_and_role(self):
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        for e in [e for e in edges if e.edge_type == "follow_on"]:
            assert e.role == "potential"
            assert e.active is True

    def test_follow_on_all_teams_represented(self):
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        team_ids = {e.team_id for e in edges if e.edge_type == "follow_on"}
        assert team_ids == {1, 2, 3, 4}

    def test_follow_on_targets_bracket_ports(self):
        div = make_division(num_teams=4)
        _, edges = GraphBuilder(div).build()
        for e in [e for e in edges if e.edge_type == "follow_on"]:
            assert e.target in ("match_-52001_home", "match_-52001_away")

    def test_no_follow_on_for_assigned_matches(self):
        """If bracket match has teams, normal flow handles it — no follow-on edges."""
        div = make_division(num_teams=4)
        for rnd in div.rounds:
            for bracket in rnd.brackets:
                for bm in bracket.bracket_matches:
                    bm.match.home_team = div.all_teams[0]
                    bm.match.away_team = div.all_teams[1]
        _, edges = GraphBuilder(div).build()
        fo = [e for e in edges if e.edge_type == "follow_on"]
        assert len(fo) == 0

    def test_no_follow_on_without_edges(self):
        div = make_division(num_teams=4)
        div.follow_on_edges = []
        _, edges = GraphBuilder(div).build()
        fo = [e for e in edges if e.edge_type == "follow_on"]
        assert len(fo) == 0

    def test_no_dangling_follow_on_edges(self):
        div = make_division(num_teams=4)
        nodes, edges = GraphBuilder(div).build()
        node_ids = {n.id for n in nodes}
        for e in [e for e in edges if e.edge_type == "follow_on"]:
            assert e.source in node_ids
            assert e.target in node_ids
