from scraper.graph.builder import GraphEdge, GraphNode


class PathPruner:
    """
    Activates/deactivates DAG edges based on known match results.

    In the sorting network model, every team continues through the tournament
    regardless of win/loss (they go to different brackets). All team_flow edges
    are therefore always active. The pruner currently performs a no-op but is
    kept for future use (e.g., marking edges inactive when a team's next
    assignment is uncertain due to an unfinished match).
    """

    def __init__(self, nodes: list[GraphNode], edges: list[GraphEdge]):
        self._nodes_by_id: dict[str, GraphNode] = {n.id: n for n in nodes}
        self._edges = edges

    def prune(self) -> list[GraphEdge]:
        """
        Process all edges and return the updated edge list.
        Currently all team_flow edges remain active.
        """
        return self._edges
