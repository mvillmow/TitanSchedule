"""Tests for PathPruner edge activation/deactivation."""

from scraper.graph.builder import GraphEdge, GraphNode
from scraper.graph.pruner import PathPruner


def make_node(node_id: str, status: str = "scheduled", home_won: bool | None = None,
              teams: list | None = None) -> GraphNode:
    return GraphNode(
        id=node_id,
        node_type="match",
        label=node_id,
        sublabel="",
        status=status,
        time=None,
        court=None,
        teams=teams or [],
        set_scores=[],
        home_won=home_won,
        aes_url=None,
        pool_name=None,
        bracket_name=None,
        round_name=None,
        match_name=None,
        layer=1,
        sublayer=0,
        phase=1,
        global_row=0.0,
        record=None,
        ranking=None,
    )


def make_edge(edge_id: str, source: str, target: str, edge_type: str = "team_flow",
              team_id: int | None = None, role: str | None = None,
              active: bool = True) -> GraphEdge:
    return GraphEdge(
        id=edge_id,
        source=source,
        target=target,
        edge_type=edge_type,
        team_id=team_id,
        team_name=None,
        role=role,
        active=active,
        label=None,
    )


class TestPathPruner:
    def test_all_edges_remain_active(self):
        """In the sorting network model, all edges remain active after prune()."""
        match_node = make_node("match1", status="finished", home_won=True,
                               teams=[{"id": 1, "name": "Home", "role": "home"},
                                      {"id": 2, "name": "Away", "role": "away"}])
        edge_home = make_edge("e1", "match1", "match2", team_id=1, role="home")
        edge_away = make_edge("e2", "match1", "match3", team_id=2, role="away")

        pruner = PathPruner([match_node], [edge_home, edge_away])
        edges = pruner.prune()

        assert all(e.active for e in edges)

    def test_unfinished_match_unchanged(self):
        """Scheduled match → all edges remain active."""
        match_node = make_node("match1", status="scheduled", home_won=None,
                               teams=[{"id": 1, "name": "Home", "role": "home"},
                                      {"id": 2, "name": "Away", "role": "away"}])
        edge1 = make_edge("e1", "match1", "match2", team_id=1)
        edge2 = make_edge("e2", "match1", "match3", team_id=2)

        pruner = PathPruner([match_node], [edge1, edge2])
        edges = pruner.prune()
        assert all(e.active for e in edges)

    def test_multiple_finished_matches(self):
        """Multiple finished matches — all edges remain active."""
        match1 = make_node("match1", "finished", home_won=True,
                           teams=[{"id": 1, "role": "home"}, {"id": 2, "role": "away"}])
        match2 = make_node("match2", "finished", home_won=False,
                           teams=[{"id": 3, "role": "home"}, {"id": 4, "role": "away"}])
        edge1 = make_edge("e1", "match1", "next1", team_id=1)
        edge2 = make_edge("e2", "match1", "next2", team_id=2)
        edge3 = make_edge("e3", "match2", "next3", team_id=3)
        edge4 = make_edge("e4", "match2", "next4", team_id=4)

        pruner = PathPruner([match1, match2], [edge1, edge2, edge3, edge4])
        edges = pruner.prune()

        assert all(e.active for e in edges)

    def test_empty_graph(self):
        pruner = PathPruner([], [])
        assert pruner.prune() == []

    def test_no_outgoing_edges(self):
        """Finished match with no outgoing edges is handled gracefully."""
        match_node = make_node("match1", "finished", home_won=True,
                               teams=[{"id": 1}, {"id": 2}])
        pruner = PathPruner([match_node], [])
        edges = pruner.prune()
        assert edges == []

    def test_returns_edge_list(self):
        """prune() returns the same edge list."""
        match_node = make_node("m1")
        edge = make_edge("e1", "m1", "m2", team_id=1)
        pruner = PathPruner([match_node], [edge])
        result = pruner.prune()
        assert result is not None
        assert len(result) == 1
