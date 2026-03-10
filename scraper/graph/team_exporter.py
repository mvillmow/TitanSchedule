"""Convert sorting network DAG to team-centric JSON export."""

from __future__ import annotations

from typing import Any, TypedDict

from scraper.graph.builder import Edge, GraphBuilder, Node
from scraper.models import Division


class GameDict(TypedDict, total=False):
    """Type for game objects in team schedule."""

    date: str
    time: str
    opponent: str | None
    opponent_id: str | None
    opponent_text: str | None
    court: str
    role: str
    round: str
    group: str
    status: str
    scores: list[list[int]]
    won: bool | None


class TeamDict(TypedDict, total=False):
    """Type for team objects in export."""

    name: str
    club: str
    seed: int | None
    games: list[GameDict]
    record: str
    rank: int | None


class ExportDict(TypedDict, total=False):
    """Type for the root export object."""

    division: str
    dates: list[str]
    teams: dict[str, TeamDict]


class TeamScheduleExporter:
    """Converts a sorting network DAG into team-centric JSON."""

    def export(self, builder: GraphBuilder, division: Division) -> ExportDict:
        """Convert the graph into team-centric JSON.

        Args:
            builder: The populated GraphBuilder with nodes and edges
            division: The Division model (for context, not strictly used)

        Returns:
            A dictionary with keys: division, dates, teams
        """
        result: ExportDict = {
            "division": builder.division_name,
            "dates": [],
            "teams": {},
        }

        # Step 1: Collect teams from start ranking nodes (phase 0)
        teams_data: dict[int, dict[str, Any]] = {}
        for node_id, node in builder.nodes.items():
            if node.type == "ranking" and node.phase == 0:
                data: dict[str, Any] = node.data
                team_id: int | None = data.get("team_id")
                if team_id is not None:
                    teams_data[team_id] = {
                        "name": data.get("team_name", ""),
                        "club": data.get("club", ""),
                        "seed": data.get("seed"),
                        "games": [],
                    }

        # Step 2: For each match node, emit game entries
        all_dates: set[str] = set()
        for node_id, node in builder.nodes.items():
            if node.type == "match":
                self._process_match_node(
                    node, builder.edges, teams_data, all_dates
                )

        # Step 3: Sort each team's games by (date, time)
        for tid in teams_data:
            team_entry = teams_data[tid]
            games_list: list[Any] = team_entry["games"]
            games_list.sort(
                key=lambda g: (g.get("date", ""), g.get("time", ""))
            )

        # Step 4: Compute records (count wins/losses from final games)
        for tid in teams_data:
            team_entry = teams_data[tid]
            games_list = team_entry["games"]
            wins = sum(1 for g in games_list if g.get("won") is True)
            losses = sum(1 for g in games_list if g.get("won") is False)
            team_entry["record"] = f"{wins}-{losses}"

        # Step 5: Extract rank from end ranking nodes
        for node_id, node in builder.nodes.items():
            if node.type == "ranking" and node.phase > 0:
                data = node.data
                node_team_id: Any = data.get("team_id")
                if isinstance(node_team_id, int) and node_team_id in teams_data:
                    teams_data[node_team_id]["rank"] = data.get("rank")

        # Step 6: Build output with team_id as string keys
        teams_output: dict[str, TeamDict] = {}
        for tid in teams_data:
            team_dict: dict[str, Any] = teams_data[tid]
            teams_output[str(tid)] = {
                "name": team_dict.get("name", ""),
                "club": team_dict.get("club", ""),
                "seed": team_dict.get("seed"),
                "games": team_dict.get("games", []),
                "record": team_dict.get("record", "0-0"),
                "rank": team_dict.get("rank"),
            }
        result["teams"] = teams_output
        result["dates"] = sorted(list(all_dates))

        return result

    def _process_match_node(
        self,
        match_node: Node,
        edges: list[Edge],
        teams_data: dict[int, dict[str, Any]],
        all_dates: set[str],
    ) -> None:
        """Process a single match node and emit game entries for involved teams.

        Args:
            match_node: The match node to process
            edges: All edges in the graph
            teams_data: Mutable dict of team data (populated)
            all_dates: Mutable set of dates (populated)
        """
        data: dict[str, Any] = match_node.data
        match_id: int | None = data.get("match_id")
        date: str = data.get("date", "")
        time: str = data.get("time", "")
        court: str = data.get("court", "")
        round_name: str = data.get("round_name", "")
        group_name: str = data.get("group_name", "")
        status: str = data.get("status", "")
        scores: list[list[int]] = data.get("scores", [])

        home_team_id: int | None = data.get("home_team_id")
        away_team_id: int | None = data.get("away_team_id")
        home_team_name: str = data.get("home_team_name", "")
        away_team_name: str = data.get("away_team_name", "")

        home_sets_won: int = data.get("home_sets_won", 0)
        away_sets_won: int = data.get("away_sets_won", 0)

        # Record the date
        if date:
            all_dates.add(date)

        # Find teams in this match by looking at edges targeting port nodes
        port_node_prefix = f"port_{match_id}_"
        role_by_team_id: dict[int | None, str] = {}

        for edge in edges:
            if edge.target.startswith(port_node_prefix) and edge.team_id is not None:
                role_by_team_id[edge.team_id] = edge.role

        # Emit games for involved teams
        for team_id in list(role_by_team_id.keys()):
            if team_id is None or team_id not in teams_data:
                continue

            role = role_by_team_id[team_id]

            # Determine opponent and opponent_id
            opponent: str | None = None
            opponent_id: str | None = None
            opponent_text: str | None = None

            if role == "home":
                opponent = away_team_name if away_team_id else None
                opponent_id = str(away_team_id) if away_team_id else None
            elif role == "away":
                opponent = home_team_name if home_team_id else None
                opponent_id = str(home_team_id) if home_team_id else None
            elif role == "work":
                if home_team_name and away_team_name:
                    opponent = f"{home_team_name} vs {away_team_name}"
                else:
                    opponent = None
                opponent_id = None

            # For conditional games, check if opponent is missing
            if status == "conditional" and opponent_id is None:
                opponent_text = "TBD"
                opponent = None

            # Determine won (only for final games)
            won: bool | None = None
            if status == "final":
                if role == "home":
                    won = home_sets_won > away_sets_won
                elif role == "away":
                    won = away_sets_won > home_sets_won
                # work role: won stays None

            # Build game entry
            game: GameDict = {
                "date": date,
                "time": time,
                "opponent": opponent,
                "opponent_id": opponent_id,
                "opponent_text": opponent_text,
                "court": court,
                "role": role,
                "round": round_name,
                "group": group_name,
                "status": status,
                "scores": scores,
                "won": won,
            }

            team_entry = teams_data[team_id]
            games_list = team_entry["games"]
            games_list.append(game)
