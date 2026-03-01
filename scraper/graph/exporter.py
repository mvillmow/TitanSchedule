import json

from scraper.graph.builder import GraphEdge, GraphNode
from scraper.models import Division


class CytoscapeExporter:
    """
    Serializes the DAG into Cytoscape.js-compatible JSON format.

    Output schema:
    {
        "metadata": { ... event/division info ... },
        "elements": {
            "nodes": [{"data": {...}}],
            "edges": [{"data": {...}}]
        }
    }
    """

    def __init__(
        self, nodes: list[GraphNode], edges: list[GraphEdge], division: Division
    ):
        self._nodes = nodes
        self._edges = edges
        self._division = division

    def export(self) -> dict:
        phases = self._build_phase_index()
        return {
            "metadata": {
                "event_key": self._division.event_key,
                "event_name": self._division.event_name,
                "division_id": self._division.division_id,
                "division_name": self._division.name,
                "aes_url": self._division.aes_url,
                "scraped_at": (
                    self._division.scraped_at.isoformat()
                    if self._division.scraped_at
                    else None
                ),
                "teams": [
                    {
                        "id": t.team_id,
                        "name": t.name,
                        "seed": t.seed,
                        "club": t.club_name,
                    }
                    for t in self._division.all_teams
                ],
                # phases: list of {phase, label, date, type} in phase order
                "phases": phases,
            },
            "elements": {
                "nodes": [self._export_node(n) for n in self._nodes],
                "edges": [self._export_edge(e) for e in self._edges],
            },
        }

    def _export_node(self, node: GraphNode) -> dict:
        data: dict = {
            "id": node.id,
            "label": node.label,
            "sublabel": node.sublabel,
            "type": node.node_type,
            "status": node.status,
            "time": node.time,
            "court": node.court,
            "teams": node.teams,
            "setScores": node.set_scores,
            "aesUrl": node.aes_url,
            "poolName": node.pool_name,
            "bracketName": node.bracket_name,
            "roundName": node.round_name,
            "matchName": node.match_name,
            "homeWon": node.home_won,
            "layer": node.layer,
            "sublayer": node.sublayer,
            "phase": node.phase,
            "globalRow": node.global_row,
            "record": node.record,
            "ranking": node.ranking,
        }
        # Compound node fields — use "parentId" (not "parent") because Cytoscape.js
        # reserves "data.parent" for compound node hierarchy, which would override
        # the preset layout by auto-positioning port nodes as compound children.
        if node.parent is not None:
            data["parentId"] = node.parent
        if node.port_role is not None:
            data["portRole"] = node.port_role
        if node.home_placeholder is not None:
            data["homePlaceholder"] = node.home_placeholder
        if node.away_placeholder is not None:
            data["awayPlaceholder"] = node.away_placeholder
        return {"data": data}

    def _export_edge(self, edge: GraphEdge) -> dict:
        return {
            "data": {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "type": edge.edge_type,
                "teamId": edge.team_id,
                "teamName": edge.team_name,
                "role": edge.role,
                "active": edge.active,
                "label": edge.label,
            },
        }

    def _build_phase_index(self) -> list[dict]:
        """Build a sorted list of phase descriptors from the node data."""
        from collections import defaultdict
        phase_info: dict[int, dict] = defaultdict(lambda: {
            "phase": 0, "label": "", "date": None, "type": "unknown",
            "roundNames": set(),
        })
        # Collect all phases from nodes first, then determine types in phase order
        for node in self._nodes:
            # Skip port nodes — they share a phase with their parent match node
            if node.node_type == "port":
                continue
            p = node.phase
            phase_info[p]["phase"] = p
            ntype = node.node_type
            if ntype == "ranking":
                if p == 0:
                    phase_info[p]["type"] = "ranking_start"
                    phase_info[p]["label"] = "Seeds"
                elif node.id.startswith("ranking_day_"):
                    # Intermediate day-boundary ranking — extract date from node id
                    # Format: ranking_day_{date}_{team_id}
                    parts = node.id.split("_")
                    # parts[0]="ranking", parts[1]="day", parts[2]=date, parts[3]=team_id
                    if len(parts) >= 4:
                        date_str = parts[2]
                        if phase_info[p]["type"] not in ("ranking_intermediate",):
                            phase_info[p]["type"] = "ranking_intermediate"
                            phase_info[p]["label"] = "Standings"
                            phase_info[p]["date"] = date_str
                else:
                    phase_info[p]["type"] = "ranking_end"
                    phase_info[p]["label"] = "Final"
            elif ntype == "match":
                phase_info[p]["type"] = "match"
                if node.round_name:
                    phase_info[p]["roundNames"].add(node.round_name)
                    # Use first-seen round name as label (deterministic; roundNames tracks all)
                    if not phase_info[p]["label"]:
                        phase_info[p]["label"] = node.round_name
                if node.time and not phase_info[p].get("date"):
                    phase_info[p]["date"] = node.time[:10]

        result = []
        for p in sorted(phase_info.keys()):
            info = phase_info[p]
            result.append({
                "phase": p,
                "label": info["label"],
                "date": info.get("date"),
                "type": info["type"],
                "roundNames": sorted(info["roundNames"]),
            })
        return result

    def export_to_file(self, path: str):
        with open(path, "w") as f:
            json.dump(self.export(), f, indent=2, default=str)
