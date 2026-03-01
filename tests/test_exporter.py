"""Tests for CytoscapeExporter JSON output."""
import json
from datetime import datetime

from scraper.graph.builder import GraphEdge, GraphNode
from scraper.graph.exporter import CytoscapeExporter
from scraper.models import Division, Team


def make_node(node_id: str, layer: int = 0, node_type: str = "ranking",
              parent: str | None = None, port_role: str | None = None,
              home_placeholder: str | None = None, away_placeholder: str | None = None) -> GraphNode:
    return GraphNode(
        id=node_id,
        node_type=node_type,
        label="Test Label",
        sublabel="Sub",
        status="scheduled",
        time=None,
        court=None,
        teams=[{"id": 1, "name": "Team A", "role": "home"}],
        set_scores=[],
        home_won=None,
        aes_url=None,
        pool_name=None,
        bracket_name=None,
        round_name=None,
        match_name=None,
        layer=layer,
        sublayer=0,
        phase=0,
        global_row=0.0,
        record=None,
        ranking=None,
        parent=parent,
        port_role=port_role,
        home_placeholder=home_placeholder,
        away_placeholder=away_placeholder,
    )


def make_edge(edge_id: str, source: str, target: str) -> GraphEdge:
    return GraphEdge(
        id=edge_id,
        source=source,
        target=target,
        edge_type="team_flow",
        team_id=1,
        team_name="Team A",
        role="home",
        active=True,
        label=None,
    )


def make_division() -> Division:
    return Division(
        division_id=199194,
        name="12 Girls",
        event_key="PTAwMDAwNDE4MzE90",
        event_name="Test Event",
        all_teams=[
            Team(team_id=1, name="Team A", display_text="Team A (HO) (1)", code="ta", seed=1, club_name="Club A"),
            Team(team_id=2, name="Team B", display_text="Team B (HO) (2)", code="tb", seed=2, club_name=None),
        ],
        aes_url="https://results.advancedeventsystems.com/event/KEY/divisions/199194/overview",
        scraped_at=datetime(2026, 2, 7, 12, 0, 0),
    )


class TestCytoscapeExporter:
    def _exporter(self, nodes=None, edges=None, division=None):
        return CytoscapeExporter(
            nodes or [make_node("n1")],
            edges or [make_edge("e1", "n1", "n2")],
            division or make_division(),
        )

    def test_json_schema(self):
        output = self._exporter().export()
        assert "metadata" in output
        assert "elements" in output
        assert "nodes" in output["elements"]
        assert "edges" in output["elements"]

    def test_nodes_have_required_fields(self):
        output = self._exporter().export()
        for node in output["elements"]["nodes"]:
            data = node["data"]
            assert "id" in data
            assert "label" in data
            assert "type" in data
            assert "status" in data

    def test_edges_have_required_fields(self):
        output = self._exporter().export()
        for edge in output["elements"]["edges"]:
            data = edge["data"]
            assert "id" in data
            assert "source" in data
            assert "target" in data
            assert "type" in data
            assert "active" in data

    def test_metadata_teams(self):
        output = self._exporter().export()
        teams = output["metadata"]["teams"]
        assert len(teams) == 2
        assert teams[0]["id"] == 1
        assert teams[0]["name"] == "Team A"
        assert teams[0]["seed"] == 1
        assert teams[0]["club"] == "Club A"
        assert teams[1]["club"] is None

    def test_metadata_event_info(self):
        output = self._exporter().export()
        meta = output["metadata"]
        assert meta["event_key"] == "PTAwMDAwNDE4MzE90"
        assert meta["event_name"] == "Test Event"
        assert meta["division_id"] == 199194
        assert meta["division_name"] == "12 Girls"

    def test_metadata_scraped_at(self):
        output = self._exporter().export()
        assert output["metadata"]["scraped_at"] == "2026-02-07T12:00:00"

    def test_node_data_fields(self):
        output = self._exporter().export()
        node_data = output["elements"]["nodes"][0]["data"]
        assert node_data["id"] == "n1"
        assert node_data["label"] == "Test Label"
        assert node_data["type"] == "ranking"
        assert node_data["status"] == "scheduled"
        assert node_data["teams"] == [{"id": 1, "name": "Team A", "role": "home"}]
        assert node_data["layer"] == 0

    def test_edge_data_fields(self):
        output = self._exporter().export()
        edge_data = output["elements"]["edges"][0]["data"]
        assert edge_data["id"] == "e1"
        assert edge_data["source"] == "n1"
        assert edge_data["target"] == "n2"
        assert edge_data["active"] is True
        assert edge_data["teamId"] == 1
        assert edge_data["role"] == "home"

    def test_edge_has_role_field(self):
        """New model: edges carry role field."""
        output = self._exporter().export()
        edge_data = output["elements"]["edges"][0]["data"]
        assert "role" in edge_data

    def test_node_has_record_field(self):
        """New model: nodes carry record field."""
        output = self._exporter().export()
        node_data = output["elements"]["nodes"][0]["data"]
        assert "record" in node_data

    def test_node_has_ranking_field(self):
        """New model: nodes carry ranking field."""
        output = self._exporter().export()
        node_data = output["elements"]["nodes"][0]["data"]
        assert "ranking" in node_data

    def test_roundtrip_json(self):
        """Export → serialize to string → parse → all data preserved."""
        exporter = self._exporter()
        output = exporter.export()
        serialized = json.dumps(output, default=str)
        parsed = json.loads(serialized)
        assert parsed["metadata"]["division_id"] == 199194
        assert len(parsed["elements"]["nodes"]) == 1

    def test_multiple_nodes_and_edges(self):
        nodes = [make_node(f"n{i}") for i in range(5)]
        edges = [make_edge(f"e{i}", f"n{i}", f"n{i+1}") for i in range(4)]
        output = CytoscapeExporter(nodes, edges, make_division()).export()
        assert len(output["elements"]["nodes"]) == 5
        assert len(output["elements"]["edges"]) == 4

    def test_export_to_file(self, tmp_path):
        path = tmp_path / "output.json"
        exporter = self._exporter()
        exporter.export_to_file(str(path))
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert "elements" in data

    def test_empty_elements(self):
        output = CytoscapeExporter([], [], make_division()).export()
        assert output["elements"]["nodes"] == []
        assert output["elements"]["edges"] == []

    def test_aes_url_in_metadata(self):
        output = self._exporter().export()
        assert "aes_url" in output["metadata"]
        assert "advancedeventsystems" in output["metadata"]["aes_url"]

    def test_phase_index_ranking_types(self):
        """Phase index should identify ranking_start and ranking_end types."""
        start = make_node("s1", layer=0, node_type="ranking")
        start_copy = GraphNode(
            **{**start.__dict__, "id": "s1", "phase": 0}
        )
        end = GraphNode(
            **{**start.__dict__, "id": "e1", "phase": 5, "layer": 99}
        )
        output = CytoscapeExporter([start_copy, end], [], make_division()).export()
        phases = {p["phase"]: p for p in output["metadata"]["phases"]}
        assert phases[0]["type"] == "ranking_start"
        assert phases[5]["type"] == "ranking_end"

    def test_port_node_exports_parent_field(self):
        """Port nodes should export a 'parentId' field (not 'parent') in their data.
        Using 'parentId' avoids Cytoscape.js compound node auto-layout behaviour."""
        parent_node = make_node("match_1", node_type="match")
        port_node = make_node("match_1_home", node_type="port",
                               parent="match_1", port_role="home")
        output = CytoscapeExporter([parent_node, port_node], [], make_division()).export()
        nodes_by_id = {n["data"]["id"]: n["data"] for n in output["elements"]["nodes"]}
        assert "parentId" in nodes_by_id["match_1_home"]
        assert nodes_by_id["match_1_home"]["parentId"] == "match_1"

    def test_port_node_exports_port_role(self):
        """Port nodes should export a 'portRole' field."""
        parent_node = make_node("match_1", node_type="match")
        port_node = make_node("match_1_away", node_type="port",
                               parent="match_1", port_role="away")
        output = CytoscapeExporter([parent_node, port_node], [], make_division()).export()
        nodes_by_id = {n["data"]["id"]: n["data"] for n in output["elements"]["nodes"]}
        assert "portRole" in nodes_by_id["match_1_away"]
        assert nodes_by_id["match_1_away"]["portRole"] == "away"

    def test_non_port_node_has_no_parent_field(self):
        """Non-port nodes should not export a 'parentId' field."""
        node = make_node("n1", node_type="ranking")
        output = CytoscapeExporter([node], [], make_division()).export()
        node_data = output["elements"]["nodes"][0]["data"]
        assert "parentId" not in node_data

    def test_match_node_exports_placeholders(self):
        """Match nodes with placeholder text should export homePlaceholder/awayPlaceholder."""
        node = make_node("match_1", node_type="match",
                          home_placeholder="1st R1P1", away_placeholder="2nd R1P1")
        output = CytoscapeExporter([node], [], make_division()).export()
        node_data = output["elements"]["nodes"][0]["data"]
        assert node_data.get("homePlaceholder") == "1st R1P1"
        assert node_data.get("awayPlaceholder") == "2nd R1P1"

    def test_phase_label_is_deterministic_first_seen(self):
        """Phase label should be the first-seen round_name, not arbitrary last-seen."""
        def _match_node(node_id, phase, round_name):
            n = make_node(node_id, node_type="match")
            return GraphNode(**{**n.__dict__, "id": node_id, "phase": phase,
                                "round_name": round_name})

        n1 = _match_node("m1", 1, "Round 1")
        n2 = _match_node("m2", 1, "Gold Bracket")  # same phase, different round_name
        ranking_start = make_node("s1", node_type="ranking")
        ranking_end = GraphNode(**{**ranking_start.__dict__, "id": "e1", "phase": 5})
        output = CytoscapeExporter([ranking_start, n1, n2, ranking_end], [], make_division()).export()
        phases = {p["phase"]: p for p in output["metadata"]["phases"]}
        # Both round names should be in roundNames
        assert "Round 1" in phases[1]["roundNames"]
        assert "Gold Bracket" in phases[1]["roundNames"]
        # Label should be the first-seen one (Round 1, as n1 was added first)
        assert phases[1]["label"] == "Round 1"

    def test_port_nodes_skipped_in_phase_index(self):
        """Port nodes should not affect the phase index."""
        match_node = make_node("match_1", node_type="match")
        match_node_with_phase = GraphNode(**{**match_node.__dict__, "phase": 1, "round_name": "Round 1"})
        port_node = make_node("match_1_home", node_type="port", parent="match_1", port_role="home")
        port_node_with_phase = GraphNode(**{**port_node.__dict__, "phase": 1})
        ranking_start = make_node("s1", node_type="ranking")
        ranking_end = GraphNode(**{**ranking_start.__dict__, "id": "e1", "phase": 5})
        output = CytoscapeExporter(
            [ranking_start, match_node_with_phase, port_node_with_phase, ranking_end],
            [], make_division()
        ).export()
        phases = {p["phase"]: p for p in output["metadata"]["phases"]}
        # Phase 1 should be a "match" phase from the match node, not affected by port
        assert phases[1]["type"] == "match"
