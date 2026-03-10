"""Sorting network DAG builder for tournament schedules."""

from __future__ import annotations

from dataclasses import dataclass, field

from scraper.models import Division, Match


@dataclass
class Node:
    """A node in the sorting network DAG."""

    id: str
    type: str  # "ranking" | "match" | "port"
    phase: int
    data: dict[str, object] = field(default_factory=dict)


@dataclass
class Edge:
    """An edge in the sorting network DAG."""

    source: str  # node id
    target: str  # node id
    team_id: int | None
    team_name: str
    role: str  # "home" | "away" | "work"


class GraphBuilder:
    """Builds a sorting network DAG from a Division."""

    def __init__(self) -> None:
        """Initialize the GraphBuilder."""
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.division_name: str = ""

    def build(self, division: Division) -> None:
        """Build the sorting network DAG from a division.

        Algorithm:
        1. Reset nodes/edges, set division_name
        2. Collect all matches (pool + bracket), determine round indices
        3. Create start ranking nodes (phase 0)
        4. Group matches by (round_index, date, time), assign phases
        5. Create match and port nodes, internal edges
        6. Create end ranking nodes (phase N+1)
        7. Wire team_flow edges (start → matches → end)
        """
        # Step 1: Reset and initialize
        self.nodes = {}
        self.edges = []
        self.division_name = division.name

        # Step 2: Collect all matches with round indices and metadata
        # Each entry: (match, round_index, round_name, group_name)
        all_matches: list[tuple[Match, int, str, str]] = []

        # Build maps for round lookup
        round_by_play_id: dict[int, int] = {}  # play_id -> round_index
        round_by_group_id: dict[int, int] = {}  # group_id -> round_index
        round_list = division.rounds

        for round_index, round_obj in enumerate(round_list):
            if round_obj.type == "pool":
                round_by_play_id[round_obj.id] = round_index
            elif round_obj.type == "bracket":
                if round_obj.group_id is not None:
                    round_by_group_id[round_obj.group_id] = round_index

        # Collect pool matches — round_name = pool name, group_name from round
        for pool in division.pools:
            round_index = round_by_play_id.get(pool.play_id, -1)
            matched_round = (
                round_list[round_index] if 0 <= round_index < len(round_list) else None
            )
            group_name = matched_round.group_name if matched_round else ""
            for match in pool.matches:
                all_matches.append((match, round_index, pool.name, group_name))

        # Collect bracket matches
        for bracket_match in division.bracket_matches:
            round_index = (
                round_by_group_id.get(bracket_match.group_id, -1)
                if bracket_match.group_id is not None
                else -1
            )
            matched_round = (
                round_list[round_index] if 0 <= round_index < len(round_list) else None
            )
            round_name = matched_round.name if matched_round else bracket_match.group_name
            group_name = bracket_match.group_name
            all_matches.append((bracket_match, round_index, round_name, group_name))

        # If no matches, create only start/end nodes
        if not all_matches:
            self._create_start_ranking_nodes(division)
            self._create_end_ranking_nodes(division)
            return

        # Step 3: Create start ranking nodes (phase 0)
        self._create_start_ranking_nodes(division)

        # Step 4: Group matches by (round_index, date, time) and assign phases
        match_groups: dict[tuple[int, str, str], list[Match]] = {}
        for match, round_index, _, _ in all_matches:
            key = (round_index, match.date, match.time)
            if key not in match_groups:
                match_groups[key] = []
            match_groups[key].append(match)

        # Sort groups chronologically: by round_index asc, then date, then time
        sorted_groups = sorted(
            match_groups.items(),
            key=lambda x: (x[0][0], x[0][1], x[0][2]),
        )

        # Assign phases 1..N
        match_to_phase: dict[int, int] = {}
        for phase, (_, matches) in enumerate(sorted_groups, start=1):
            for match in matches:
                match_to_phase[match.id] = phase

        # Step 5: Create match and port nodes
        for match, _, round_name, group_name in all_matches:
            phase = match_to_phase.get(match.id, 1)
            status = self._get_match_status(match)

            # Convert SetScore objects to [home, away] lists
            scores: list[list[int]] = [[s.home, s.away] for s in match.scores]

            # Match node
            match_node = Node(
                id=f"match_{match.id}",
                type="match",
                phase=phase,
                data={
                    "match_id": match.id,
                    "home_team_id": match.home_team_id,
                    "away_team_id": match.away_team_id,
                    "home_team_name": match.home_team_name,
                    "away_team_name": match.away_team_name,
                    "work_team_id": match.work_team_id,
                    "work_team_name": match.work_team_name,
                    "court": match.court,
                    "date": match.date,
                    "time": match.time,
                    "home_sets_won": match.home_sets_won,
                    "away_sets_won": match.away_sets_won,
                    "status": status,
                    "round_name": round_name,
                    "group_name": group_name,
                    "scores": scores,
                },
            )
            self.nodes[match_node.id] = match_node

            # Port nodes and internal edges
            for role in ["home", "away", "work"]:
                port_id = f"port_{match.id}_{role}"
                port_node = Node(
                    id=port_id,
                    type="port",
                    phase=phase,
                    data={"match_id": match.id, "role": role},
                )
                self.nodes[port_node.id] = port_node

                # Internal edge: port → match
                team_id = None
                team_name = ""
                if role == "home":
                    team_id = match.home_team_id
                    team_name = match.home_team_name
                elif role == "away":
                    team_id = match.away_team_id
                    team_name = match.away_team_name
                elif role == "work":
                    team_id = match.work_team_id
                    team_name = match.work_team_name

                self.edges.append(
                    Edge(
                        source=port_id,
                        target=match_node.id,
                        team_id=team_id,
                        team_name=team_name,
                        role=role,
                    )
                )

        # Step 6: Create end ranking nodes (phase N+1)
        num_phases = max((node.phase for node in self.nodes.values()), default=0)
        end_phase = num_phases + 1
        self._create_end_ranking_nodes(division, end_phase)

        # Step 7: Wire team_flow edges
        self._wire_team_flow_edges(division, match_to_phase)

    def _create_start_ranking_nodes(self, division: Division) -> None:
        """Create start ranking nodes for all teams in the division."""
        for team_id, team in division.teams.items():
            start_node = Node(
                id=f"start_{team_id}",
                type="ranking",
                phase=0,
                data={
                    "team_id": team_id,
                    "team_name": team.name,
                    "club": team.club,
                    "seed": team.seed,
                },
            )
            self.nodes[start_node.id] = start_node

    def _create_end_ranking_nodes(
        self, division: Division, phase: int | None = None
    ) -> None:
        """Create end ranking nodes with final records and standings."""
        if phase is None:
            phase = max((node.phase for node in self.nodes.values()), default=0) + 1

        # Build mapping of team_id -> (wins, losses)
        team_record: dict[int, tuple[int, int]] = {}
        for team_id in division.teams:
            team_record[team_id] = (0, 0)

        # Count wins/losses from finished matches
        for pool in division.pools:
            for match in pool.matches:
                if not match.is_finished:
                    continue
                if match.home_team_id is not None and match.away_team_id is not None:
                    home_wins, home_losses = team_record.get(match.home_team_id, (0, 0))
                    away_wins, away_losses = team_record.get(match.away_team_id, (0, 0))
                    if match.home_sets_won > match.away_sets_won:
                        team_record[match.home_team_id] = (home_wins + 1, home_losses)
                        team_record[match.away_team_id] = (away_wins, away_losses + 1)
                    else:
                        team_record[match.home_team_id] = (home_wins, home_losses + 1)
                        team_record[match.away_team_id] = (away_wins + 1, away_losses)

        for bracket_match in division.bracket_matches:
            if not bracket_match.is_finished:
                continue
            if (
                bracket_match.home_team_id is not None
                and bracket_match.away_team_id is not None
            ):
                home_wins, home_losses = team_record.get(
                    bracket_match.home_team_id, (0, 0)
                )
                away_wins, away_losses = team_record.get(
                    bracket_match.away_team_id, (0, 0)
                )
                if bracket_match.home_sets_won > bracket_match.away_sets_won:
                    team_record[bracket_match.home_team_id] = (home_wins + 1, home_losses)
                    team_record[bracket_match.away_team_id] = (away_wins, away_losses + 1)
                else:
                    team_record[bracket_match.home_team_id] = (
                        home_wins,
                        home_losses + 1,
                    )
                    team_record[bracket_match.away_team_id] = (
                        away_wins + 1,
                        away_losses,
                    )

        # Build mapping of team_id -> rank from pool standings
        team_rank: dict[int, int] = {}
        for pool in division.pools:
            for standing in pool.standings:
                team_rank[standing.team_id] = standing.rank

        # Create end nodes
        for team_id, team in division.teams.items():
            wins, losses = team_record.get(team_id, (0, 0))
            rank = team_rank.get(team_id, 0)

            end_node = Node(
                id=f"end_{team_id}",
                type="ranking",
                phase=phase,
                data={
                    "team_id": team_id,
                    "team_name": team.name,
                    "wins": wins,
                    "losses": losses,
                    "rank": rank,
                },
            )
            self.nodes[end_node.id] = end_node

    def _get_match_status(self, match: Match) -> str:
        """Determine match status from match state."""
        if match.is_finished:
            return "final"
        if match.is_in_progress:
            return "in_progress"
        if match.home_team_id is not None and match.away_team_id is not None:
            return "scheduled"
        return "conditional"

    def _wire_team_flow_edges(
        self, division: Division, match_to_phase: dict[int, int]
    ) -> None:
        """Create team_flow edges from start → matches → end."""
        # For each team, track which matches it participates in
        # team_id -> [(match_id, role, phase), ...]
        team_matches: dict[int, list[tuple[int, str, int]]] = {}

        # Collect from pool matches
        for pool in division.pools:
            for match in pool.matches:
                phase = match_to_phase.get(match.id, 1)
                if match.home_team_id is not None:
                    if match.home_team_id not in team_matches:
                        team_matches[match.home_team_id] = []
                    team_matches[match.home_team_id].append((match.id, "home", phase))
                if match.away_team_id is not None:
                    if match.away_team_id not in team_matches:
                        team_matches[match.away_team_id] = []
                    team_matches[match.away_team_id].append((match.id, "away", phase))
                if match.work_team_id is not None:
                    if match.work_team_id not in team_matches:
                        team_matches[match.work_team_id] = []
                    team_matches[match.work_team_id].append((match.id, "work", phase))

        # Collect from bracket matches
        for bracket_match in division.bracket_matches:
            phase = match_to_phase.get(bracket_match.id, 1)
            if bracket_match.home_team_id is not None:
                if bracket_match.home_team_id not in team_matches:
                    team_matches[bracket_match.home_team_id] = []
                team_matches[bracket_match.home_team_id].append(
                    (bracket_match.id, "home", phase)
                )
            if bracket_match.away_team_id is not None:
                if bracket_match.away_team_id not in team_matches:
                    team_matches[bracket_match.away_team_id] = []
                team_matches[bracket_match.away_team_id].append(
                    (bracket_match.id, "away", phase)
                )
            if bracket_match.work_team_id is not None:
                if bracket_match.work_team_id not in team_matches:
                    team_matches[bracket_match.work_team_id] = []
                team_matches[bracket_match.work_team_id].append(
                    (bracket_match.id, "work", phase)
                )

        # Wire edges for each team
        for team_id, matches_list in team_matches.items():
            # Sort matches by phase and match_id for chronological order
            matches_list.sort(key=lambda x: (x[2], x[0]))

            team = division.teams.get(team_id)
            team_name = team.name if team else ""

            # start → first match
            if matches_list:
                first_match_id, first_role, _ = matches_list[0]
                port_id = f"port_{first_match_id}_{first_role}"
                self.edges.append(
                    Edge(
                        source=f"start_{team_id}",
                        target=port_id,
                        team_id=team_id,
                        team_name=team_name,
                        role=first_role,
                    )
                )

                # match → next match
                for i in range(len(matches_list) - 1):
                    current_match_id, current_role, _ = matches_list[i]
                    next_match_id, next_role, _ = matches_list[i + 1]

                    current_port = f"port_{current_match_id}_{current_role}"
                    next_port = f"port_{next_match_id}_{next_role}"

                    self.edges.append(
                        Edge(
                            source=current_port,
                            target=next_port,
                            team_id=team_id,
                            team_name=team_name,
                            role=next_role,
                        )
                    )

                # last match → end
                last_match_id, last_role, _ = matches_list[-1]
                last_port = f"port_{last_match_id}_{last_role}"
                self.edges.append(
                    Edge(
                        source=last_port,
                        target=f"end_{team_id}",
                        team_id=team_id,
                        team_name=team_name,
                        role=last_role,
                    )
                )
            else:
                # No matches for this team: direct start → end
                self.edges.append(
                    Edge(
                        source=f"start_{team_id}",
                        target=f"end_{team_id}",
                        team_id=team_id,
                        team_name=team_name,
                        role="",
                    )
                )
