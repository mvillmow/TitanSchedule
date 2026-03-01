from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass

from scraper.models import Division, Match, MatchStatus


@dataclass
class GraphNode:
    """A node in the tournament sorting network DAG."""

    id: str
    node_type: str          # "ranking" | "match" | "port"
    label: str
    sublabel: str
    status: str             # "finished" | "scheduled" | "in_progress"
    time: str | None
    court: str | None
    teams: list[dict]       # [{id, name, role}] — role: "home"/"away"/"work"
    set_scores: list[dict]
    home_won: bool | None
    aes_url: str | None
    round_name: str | None
    match_name: str | None
    pool_name: str | None
    bracket_name: str | None
    layer: int
    sublayer: int
    phase: int
    global_row: float
    # Ranking-specific fields
    record: str | None      # "3-1" win-loss for ranking nodes
    ranking: int | None     # 1-based rank position for ranking nodes
    # Compound node fields
    parent: str | None = None       # compound parent node ID (for port children)
    port_role: str | None = None    # "home" | "away" | "work" (for port children)
    home_placeholder: str | None = None   # placeholder text for unassigned home slot
    away_placeholder: str | None = None   # placeholder text for unassigned away slot


@dataclass
class GraphEdge:
    """A directed edge in the tournament sorting network DAG."""

    id: str
    source: str
    target: str
    edge_type: str          # "team_flow" | "follow_on"
    team_id: int | None
    team_name: str | None
    role: str | None        # "home" | "away" | "work" — team's role at target node
    active: bool
    label: str | None


# ---------------------------------------------------------------------------
# Internal helper dataclass for match metadata during build
# ---------------------------------------------------------------------------

@dataclass
class _MatchInfo:
    match: Match
    round_name: str
    round_index: int        # sequential round number (0-based)
    pool_name: str | None
    bracket_name: str | None
    node_id: str


class GraphBuilder:
    """
    Builds the tournament sorting network DAG from a parsed Division.

    Model:
    - Phase 0: Start ranking nodes (one per team, ordered by seed)
    - Phases 1..N: Match nodes grouped by (round, time-slot within round)
      Each match emits: 1 parent node + 2-3 port children (home/away/work)
    - Phase N+1: End ranking nodes (one per team, showing final record + ranking)

    Edges are "team_flow" type carrying team_id, team_name, and the team's
    role at the target node ("home"/"away"/"work"). Edges connect to port nodes,
    not to the parent match node directly.
    """

    def __init__(self, division: Division):
        self._division = division
        self._nodes: list[GraphNode] = []
        self._edges: list[GraphEdge] = []
        self._node_ids: set[str] = set()
        self._edge_ids: set[str] = set()
        # Map team_id -> 0-based seed row
        self._team_to_row: dict[int, int] = {}
        # Map ISO date string -> phase number for intermediate day-boundary rankings
        self._day_boundary_phases: dict[str, int] = {}
        # Map team_id -> team name for O(1) lookup
        self._team_name_map: dict[int, str] = {
            t.team_id: t.name for t in division.all_teams if t.team_id is not None
        }
        # team_id -> last port before ranking_end for teams deferred via follow-on brackets
        self._deferred_ranking_end: dict[int, str] = {}

    def build(self) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Build the complete DAG and return (nodes, edges)."""
        self._build_team_row_map()

        all_match_infos = self._collect_all_matches()
        phase_map = self._compute_phase_map(all_match_infos)

        self._build_start_ranking_nodes()
        self._build_match_nodes(all_match_infos, phase_map)
        self._build_intermediate_ranking_nodes(all_match_infos, phase_map)
        self._build_end_ranking_nodes(all_match_infos, phase_map)
        self._build_team_flow_edges(all_match_infos, phase_map)
        self._build_follow_on_edges(all_match_infos, phase_map)

        return self._nodes, self._edges

    # ------------------------------------------------------------------ #
    # Team-row lookup                                                      #
    # ------------------------------------------------------------------ #

    def _build_team_row_map(self):
        """Map each team_id to its 0-based seed row (seed 1 → row 0)."""
        sorted_teams = sorted(
            (t for t in self._division.all_teams if t.team_id is not None),
            key=lambda t: t.seed or 999,
        )
        for idx, team in enumerate(sorted_teams):
            self._team_to_row[team.team_id] = idx

    def _global_row(self, team_ids: list[int]) -> float:
        """Return the average seed row for a list of team IDs."""
        rows = [self._team_to_row[tid] for tid in team_ids if tid in self._team_to_row]
        return sum(rows) / len(rows) if rows else 0.0

    # ------------------------------------------------------------------ #
    # Match collection                                                     #
    # ------------------------------------------------------------------ #

    def _collect_all_matches(self) -> list[_MatchInfo]:
        """Flatten all matches (pool + bracket) into a single list with metadata."""
        all_infos: list[_MatchInfo] = []

        for round_index, rnd in enumerate(self._division.rounds):
            for pool in rnd.pools:
                for match in pool.matches:
                    node_id = f"match_{match.match_id}"
                    all_infos.append(_MatchInfo(
                        match=match,
                        round_name=rnd.round_name,
                        round_index=round_index,
                        pool_name=pool.complete_short_name,
                        bracket_name=None,
                        node_id=node_id,
                    ))

            for bracket in rnd.brackets:
                for bm in bracket.bracket_matches:
                    match = bm.match
                    node_id = f"match_{match.match_id}"
                    all_infos.append(_MatchInfo(
                        match=match,
                        round_name=rnd.round_name,
                        round_index=round_index,
                        pool_name=None,
                        bracket_name=bracket.complete_short_name,
                        node_id=node_id,
                    ))

        return all_infos

    # ------------------------------------------------------------------ #
    # Phase computation                                                    #
    # ------------------------------------------------------------------ #

    def _compute_phase_map(self, all_match_infos: list[_MatchInfo]) -> dict[str, int]:
        """
        Assign a phase (column index) to each match node_id.

        Strategy: group by (round_index, time_slot_within_round).
        Phase 0 = start ranking. Each (round, timeslot) gets the next phase.
        When the date changes between consecutive timeslots, a day-boundary ranking
        phase is inserted. End ranking gets the last phase.

        Returns dict mapping node_id -> phase integer.
        """
        # Group matches by round_index, then by start time within round
        round_timeslots: dict[int, list] = defaultdict(list)

        for info in all_match_infos:
            start = info.match.scheduled_start
            slot = start.isoformat() if start else None
            round_timeslots[info.round_index].append(slot)

        # For each round, get the sorted unique time slots
        round_slot_phases: dict[int, dict] = {}
        current_phase = 1  # phase 0 is start ranking

        # Collect all timeslots in global order to detect date changes
        # Each item: (sort_key, slot_iso, round_index)
        all_timeslots_ordered: list[tuple] = []
        for round_index in sorted(round_timeslots.keys()):
            slots = round_timeslots[round_index]
            unique_slots = sorted(set(slots), key=lambda s: (s is not None, s or ""))
            for slot in unique_slots:
                # sort_key: (round_index, slot_or_empty)
                sort_key = (round_index, slot or "")
                all_timeslots_ordered.append((sort_key, slot, round_index))

        # Sort globally by (round_index, slot)
        all_timeslots_ordered.sort(key=lambda x: x[0])

        # Assign phases, inserting day-boundary phases at date changes
        self._day_boundary_phases = {}
        round_slot_phases_flat: dict[tuple, int] = {}  # (round_index, slot) -> phase

        prev_date: str | None = None
        for _sort_key, slot, round_index in all_timeslots_ordered:
            # Extract date from slot (first 10 chars of ISO datetime)
            curr_date = slot[:10] if slot else None

            # Insert a day-boundary ranking phase when date changes (not at start)
            if curr_date and prev_date and curr_date != prev_date:
                # Only insert if we haven't already added a boundary for prev_date
                if prev_date not in self._day_boundary_phases:
                    self._day_boundary_phases[prev_date] = current_phase
                    current_phase += 1

            key = (round_index, slot)
            if key not in round_slot_phases_flat:
                round_slot_phases_flat[key] = current_phase
                current_phase += 1

            if curr_date:
                prev_date = curr_date

        # Build round_slot_phases nested dict for lookup below
        for (round_index, slot), phase in round_slot_phases_flat.items():
            if round_index not in round_slot_phases:
                round_slot_phases[round_index] = {}
            round_slot_phases[round_index][slot] = phase

        # Build node_id -> phase mapping
        phase_map: dict[str, int] = {}
        for info in all_match_infos:
            start = info.match.scheduled_start
            slot = start.isoformat() if start else None
            slot_phases = round_slot_phases.get(info.round_index, {})
            phase = slot_phases.get(slot, current_phase)
            phase_map[info.node_id] = phase

        # Record the next phase for end ranking
        self._end_ranking_phase = current_phase

        return phase_map

    # ------------------------------------------------------------------ #
    # Node builders                                                        #
    # ------------------------------------------------------------------ #

    def _build_start_ranking_nodes(self):
        """Phase 0: one ranking node per team, ordered by seed."""
        for team in sorted(self._division.all_teams, key=lambda t: t.seed or 999):
            if team.team_id is None:
                continue
            node_id = f"ranking_start_{team.team_id}"
            row = self._team_to_row.get(team.team_id, 0)
            self._add_node(GraphNode(
                id=node_id,
                node_type="ranking",
                label=team.name,
                sublabel=f"Seed {team.seed}" if team.seed else "",
                status="finished",
                time=None,
                court=None,
                teams=[{"id": team.team_id, "name": team.name, "role": "home"}],
                set_scores=[],
                home_won=None,
                aes_url=team.aes_url,
                round_name=None,
                match_name=None,
                pool_name=None,
                bracket_name=None,
                layer=0,
                sublayer=team.seed or 0,
                phase=0,
                global_row=float(row),
                record=None,
                ranking=team.seed,
            ))

    def _build_match_nodes(self, all_match_infos: list[_MatchInfo], phase_map: dict[str, int]):
        """Create one parent match node + port children per match."""
        for info in all_match_infos:
            match = info.match
            node_id = info.node_id

            teams_list = []
            if match.home_team:
                teams_list.append({
                    "id": match.home_team.team_id,
                    "name": match.home_team.name,
                    "role": "home",
                })
            if match.away_team:
                teams_list.append({
                    "id": match.away_team.team_id,
                    "name": match.away_team.name,
                    "role": "away",
                })
            # Work team from match.work_team_id if available
            if match.work_team_id is not None:
                # Find team name from division teams
                work_team_name = self._find_team_name(match.work_team_id)
                teams_list.append({
                    "id": match.work_team_id,
                    "name": work_team_name or match.work_team_text or f"Team {match.work_team_id}",
                    "role": "work",
                })

            phase = phase_map.get(node_id, 1)

            # Label: court name if available, else match short name
            label = match.court.name if match.court else match.match_short_name

            # Sublabel: pool or bracket context + match name
            if info.pool_name:
                sublabel = f"{info.pool_name} {match.match_short_name}"
            elif info.bracket_name:
                sublabel = f"{info.bracket_name} {match.match_short_name}"
            else:
                sublabel = match.match_short_name

            # Global row = average of participating (non-work) teams
            playing_team_ids = [
                t["id"] for t in teams_list
                if t["role"] in ("home", "away") and t["id"] is not None
            ]
            row = self._global_row(playing_team_ids)

            # Placeholder text for bracket matches with no assigned teams
            home_placeholder = match.home_placeholder
            away_placeholder = match.away_placeholder

            # --- Parent match node ---
            self._add_node(GraphNode(
                id=node_id,
                node_type="match",
                label=label,
                sublabel=sublabel,
                status=match.status.value,
                time=(
                    match.scheduled_start.isoformat()
                    if match.scheduled_start
                    else None
                ),
                court=match.court.name if match.court else None,
                teams=teams_list,
                set_scores=[
                    {
                        "home": s.home_score,
                        "away": s.away_score,
                        "text": s.score_text,
                    }
                    for s in match.set_scores
                ],
                home_won=match.home_won,
                aes_url=None,
                round_name=info.round_name,
                match_name=match.match_short_name,
                pool_name=info.pool_name,
                bracket_name=info.bracket_name,
                layer=info.round_index + 1,
                sublayer=0,
                phase=phase,
                global_row=row,
                record=None,
                ranking=None,
                parent=None,
                port_role=None,
                home_placeholder=home_placeholder,
                away_placeholder=away_placeholder,
            ))

            # --- Port children ---
            has_home = match.home_team is not None or home_placeholder is not None
            has_away = match.away_team is not None or away_placeholder is not None

            match_status = match.status.value
            if has_home:
                self._add_port_node(node_id, "home", phase, row, match_status)
            if has_away:
                self._add_port_node(node_id, "away", phase, row, match_status)
            if match.work_team_id is not None:
                self._add_port_node(node_id, "work", phase, row, match_status)

    def _add_port_node(self, parent_id: str, role: str, phase: int, global_row: float, status: str = "scheduled"):
        """Add an invisible port child node for edge routing."""
        port_id = f"{parent_id}_{role}"
        self._add_node(GraphNode(
            id=port_id,
            node_type="port",
            label="",
            sublabel="",
            status=status,
            time=None,
            court=None,
            teams=[],
            set_scores=[],
            home_won=None,
            aes_url=None,
            round_name=None,
            match_name=None,
            pool_name=None,
            bracket_name=None,
            layer=0,
            sublayer=0,
            phase=phase,
            global_row=global_row,
            record=None,
            ranking=None,
            parent=parent_id,
            port_role=role,
        ))

    def _compute_records_as_of(
        self, all_match_infos: list[_MatchInfo], phase_map: dict[str, int], max_phase: int
    ) -> dict[int, dict]:
        """
        Compute W-L records for all teams from matches whose phase <= max_phase
        and whose status is FINISHED.

        Returns dict[team_id, {"wins": N, "losses": M}].
        """
        records: dict[int, dict] = defaultdict(lambda: {"wins": 0, "losses": 0})
        for info in all_match_infos:
            if phase_map.get(info.node_id, 999) > max_phase:
                continue
            match = info.match
            if match.status not in (MatchStatus.FINISHED, MatchStatus.FORFEIT) or match.home_won is None:
                continue
            if match.home_team and match.home_team.team_id is not None:
                if match.home_won:
                    records[match.home_team.team_id]["wins"] += 1
                else:
                    records[match.home_team.team_id]["losses"] += 1
            if match.away_team and match.away_team.team_id is not None:
                if not match.home_won:
                    records[match.away_team.team_id]["wins"] += 1
                else:
                    records[match.away_team.team_id]["losses"] += 1
        return records

    def _build_intermediate_ranking_nodes(
        self, all_match_infos: list[_MatchInfo], phase_map: dict[str, int]
    ):
        """
        For each day boundary, insert a ranking column showing cumulative W-L records
        as of that day. Teams are ordered by (-wins, losses, seed).
        """
        for date_str, boundary_phase in self._day_boundary_phases.items():
            # max_phase for this date = boundary_phase - 1 (last match phase before boundary)
            max_match_phase = boundary_phase - 1
            records = self._compute_records_as_of(all_match_infos, phase_map, max_match_phase)

            # Sort teams by W-L rank for this day
            teams_with_records = []
            for team in self._division.all_teams:
                if team.team_id is None:
                    continue
                rec = records.get(team.team_id, {"wins": 0, "losses": 0})
                teams_with_records.append((team, rec))

            teams_with_records.sort(
                key=lambda x: (-x[1]["wins"], x[1]["losses"], x[0].seed or 999)
            )

            for rank_pos, (team, rec) in enumerate(teams_with_records, start=1):
                node_id = f"ranking_day_{date_str}_{team.team_id}"
                record_str = f"{rec['wins']}-{rec['losses']}"
                self._add_node(GraphNode(
                    id=node_id,
                    node_type="ranking",
                    label=team.name,
                    sublabel=record_str,
                    status="finished",
                    time=None,
                    court=None,
                    teams=[{"id": team.team_id, "name": team.name, "role": "home"}],
                    set_scores=[],
                    home_won=None,
                    aes_url=team.aes_url,
                    round_name=None,
                    match_name=None,
                    pool_name=None,
                    bracket_name=None,
                    layer=0,
                    sublayer=team.seed or 0,
                    phase=boundary_phase,
                    global_row=float(rank_pos - 1),
                    record=record_str,
                    ranking=rank_pos,
                ))

    def _build_end_ranking_nodes(self, all_match_infos: list[_MatchInfo], phase_map: dict[str, int]):
        """Last phase: one ranking node per team with computed record and ranking position."""
        # Reuse _compute_records_as_of with max_phase=sys.maxsize to include all matches
        team_records = self._compute_records_as_of(all_match_infos, phase_map, sys.maxsize)

        end_phase = self._end_ranking_phase

        # Sort teams by wins desc, then by team_id for deterministic ordering
        teams_with_records = []
        for team in self._division.all_teams:
            if team.team_id is None:
                continue
            rec = team_records.get(team.team_id, {"wins": 0, "losses": 0})
            teams_with_records.append((team, rec))

        # Sort: wins descending, then losses ascending (fewer losses = better), then seed
        teams_with_records.sort(
            key=lambda x: (-x[1]["wins"], x[1]["losses"], x[0].seed or 999)
        )

        # Assign ranking positions
        team_rankings: dict[int, int] = {}
        for rank_pos, (team, _) in enumerate(teams_with_records, start=1):
            team_rankings[team.team_id] = rank_pos

        for team in sorted(self._division.all_teams, key=lambda t: t.seed or 999):
            if team.team_id is None:
                continue
            node_id = f"ranking_end_{team.team_id}"
            rank_pos = team_rankings.get(team.team_id, 999)
            row = rank_pos - 1  # rank 1 → row 0, rank 2 → row 1
            rec = team_records.get(team.team_id, {"wins": 0, "losses": 0})
            record_str = f"{rec['wins']}-{rec['losses']}"
            ranking_pos = team_rankings.get(team.team_id)

            self._add_node(GraphNode(
                id=node_id,
                node_type="ranking",
                label=team.name,
                sublabel=record_str,
                status="finished",
                time=None,
                court=None,
                teams=[{"id": team.team_id, "name": team.name, "role": "home"}],
                set_scores=[],
                home_won=None,
                aes_url=team.aes_url,
                round_name=None,
                match_name=None,
                pool_name=None,
                bracket_name=None,
                layer=99,
                sublayer=team.seed or 0,
                phase=end_phase,
                global_row=float(row),
                record=record_str,
                ranking=ranking_pos,
            ))

    # ------------------------------------------------------------------ #
    # Edge builders                                                        #
    # ------------------------------------------------------------------ #

    def _build_team_flow_edges(self, all_match_infos: list[_MatchInfo], phase_map: dict[str, int]):
        """
        Wire up team_flow edges for each team's chronological path:
        ranking_start → port_node → ... → [ranking_day_DATE] → ... → ranking_end

        Intermediate day-boundary ranking nodes are inserted between matches that
        span a date boundary. Edges connect to port nodes (not parent match nodes)
        for precise routing.

        Teams whose pool feeds unscheduled follow-on bracket matches have their
        ranking_end edge deferred (stored in self._deferred_ranking_end) so that
        _build_follow_on_edges can route ranking_end from the bracket port instead.
        """
        deferred_team_ids = self._build_follow_on_team_set()

        # Build sorted list of (date, boundary_phase) pairs for easy lookup
        sorted_boundaries = sorted(
            self._day_boundary_phases.items(),
            key=lambda item: item[1]  # sort by phase number
        )

        # Build team timeline: team_id -> sorted list of _MatchInfo
        team_timelines: dict[int, list[_MatchInfo]] = defaultdict(list)

        for info in all_match_infos:
            match = info.match
            for team in [match.home_team, match.away_team]:
                if team and team.team_id is not None:
                    team_timelines[team.team_id].append(info)
            # Work team also gets a timeline entry
            if match.work_team_id is not None:
                team_timelines[match.work_team_id].append(info)

        # Sort each team's timeline by (round_index, scheduled_start, -match_id).
        # AES IDs are negative integers; less-negative = earlier match.
        # Negating match_id gives ascending sort where less-negative IDs sort first.
        for team_id in team_timelines:
            team_timelines[team_id].sort(
                key=lambda info: (
                    info.round_index,
                    info.match.scheduled_start.isoformat()
                    if info.match.scheduled_start
                    else "",
                    -info.match.match_id,
                )
            )

        # Create edges for each team
        for team in self._division.all_teams:
            team_id = team.team_id
            if team_id is None:
                continue

            start_node_id = f"ranking_start_{team_id}"
            end_node_id = f"ranking_end_{team_id}"
            timeline = team_timelines.get(team_id, [])

            if not timeline:
                # No matches — route through any intermediate ranking nodes
                prev_node = start_node_id
                for date_str, _ in sorted_boundaries:
                    mid_node = f"ranking_day_{date_str}_{team_id}"
                    if prev_node in self._node_ids and mid_node in self._node_ids:
                        self._add_edge(GraphEdge(
                            id=f"flow_{team_id}_{prev_node}_to_day_{date_str}",
                            source=prev_node,
                            target=mid_node,
                            edge_type="team_flow",
                            team_id=team_id,
                            team_name=team.name,
                            role=None,
                            active=True,
                            label=None,
                        ))
                        prev_node = mid_node
                if prev_node in self._node_ids and end_node_id in self._node_ids:
                    self._add_edge(GraphEdge(
                        id=f"flow_{team_id}_start_to_end",
                        source=prev_node,
                        target=end_node_id,
                        edge_type="team_flow",
                        team_id=team_id,
                        team_name=team.name,
                        role=None,
                        active=True,
                        label=None,
                    ))
                continue

            # Build a full sequence: interleave match infos and intermediate ranking nodes
            # by comparing match phases to boundary phases
            # sequence items: either _MatchInfo or ("boundary", date_str)
            if sorted_boundaries:
                # For each gap between consecutive matches, check if any boundaries fall in between
                result_seq: list = []
                for i, info in enumerate(timeline):
                    result_seq.append(info)
                    if i < len(timeline) - 1:
                        curr_phase = phase_map.get(info.node_id, 0)
                        next_phase = phase_map.get(timeline[i + 1].node_id, 0)
                        # Insert any boundary phases that fall between curr_phase and next_phase
                        for date_str, boundary_phase in sorted_boundaries:
                            if curr_phase < boundary_phase <= next_phase:
                                result_seq.append(("boundary", date_str))

                # Also insert boundaries AFTER the last match (before end ranking)
                if timeline:
                    last_phase = phase_map.get(timeline[-1].node_id, 0)
                    for date_str, boundary_phase in sorted_boundaries:
                        if boundary_phase > last_phase:
                            result_seq.append(("boundary", date_str))

                # Also insert boundaries BEFORE the first match (after start ranking, phase 0)
                if timeline:
                    first_phase = phase_map.get(timeline[0].node_id, 0)
                    pre_boundaries = []
                    for date_str, boundary_phase in sorted_boundaries:
                        if boundary_phase < first_phase:
                            pre_boundaries.append(("boundary", date_str))
                    result_seq = pre_boundaries + result_seq
            else:
                result_seq = list(timeline)

            # Now build edges along result_seq
            # prev_endpoint is the source node id for the next edge
            prev_endpoint = start_node_id

            for item in result_seq:
                if isinstance(item, tuple) and item[0] == "boundary":
                    date_str = item[1]
                    mid_node = f"ranking_day_{date_str}_{team_id}"
                    if prev_endpoint in self._node_ids and mid_node in self._node_ids:
                        self._add_edge(GraphEdge(
                            id=f"flow_{team_id}_{prev_endpoint}_to_day_{date_str}",
                            source=prev_endpoint,
                            target=mid_node,
                            edge_type="team_flow",
                            team_id=team_id,
                            team_name=team.name,
                            role=None,
                            active=True,
                            label=None,
                        ))
                        prev_endpoint = mid_node
                else:
                    info = item
                    role = self._get_team_role(info.match, team_id)
                    port_id = f"{info.node_id}_{role}" if role else info.node_id
                    if prev_endpoint in self._node_ids and port_id in self._node_ids:
                        edge_id = f"flow_{team_id}_{prev_endpoint}_to_{info.match.match_id}"
                        self._add_edge(GraphEdge(
                            id=edge_id,
                            source=prev_endpoint,
                            target=port_id,
                            edge_type="team_flow",
                            team_id=team_id,
                            team_name=team.name,
                            role=role,
                            active=True,
                            label=None,
                        ))
                        prev_endpoint = port_id

            # Edge: last endpoint → ranking_end
            # Defer for teams feeding unscheduled follow-on brackets — the
            # ranking_end edge will originate from the bracket port instead.
            if team_id in deferred_team_ids:
                self._deferred_ranking_end[team_id] = prev_endpoint
            elif prev_endpoint in self._node_ids and end_node_id in self._node_ids:
                self._add_edge(GraphEdge(
                    id=f"flow_{team_id}_{prev_endpoint}_to_end",
                    source=prev_endpoint,
                    target=end_node_id,
                    edge_type="team_flow",
                    team_id=team_id,
                    team_name=team.name,
                    role=None,
                    active=True,
                    label=None,
                ))

    # ------------------------------------------------------------------ #
    # Follow-on fan-out edges                                             #
    # ------------------------------------------------------------------ #

    def _build_pool_lookup(self) -> dict[int, list[int]]:
        """Map pool play_id -> list of team_ids in that pool."""
        lookup: dict[int, list[int]] = {}
        for rnd in self._division.rounds:
            for pool in rnd.pools:
                team_ids = [
                    ts.team.team_id for ts in pool.teams
                    if ts.team.team_id is not None
                ]
                lookup[pool.play_id] = team_ids
        return lookup

    def _build_follow_on_team_set(self) -> set[int]:
        """
        Return the set of team_ids that are pool members feeding into unscheduled
        follow-on bracket matches (no home/away teams assigned yet).
        These teams need their ranking_end edge deferred until after follow-on
        fan-out so it originates from the bracket port rather than the pool port.
        """
        if not self._division.follow_on_edges:
            return set()

        pool_lookup = self._build_pool_lookup()

        # Build match_id -> Match for all bracket matches
        unscheduled_bracket_match_ids: set[int] = set()
        for rnd in self._division.rounds:
            for bracket in rnd.brackets:
                for bm in bracket.bracket_matches:
                    m = bm.match
                    if m.home_team is None and m.away_team is None:
                        unscheduled_bracket_match_ids.add(m.match_id)

        deferred: set[int] = set()
        for edge in self._division.follow_on_edges:
            if edge.target_match_id in unscheduled_bracket_match_ids:
                for tid in pool_lookup.get(edge.source_play_id, []):
                    deferred.add(tid)
        return deferred

    def _build_follow_on_lookup(self) -> dict[int, set[int]]:
        """Map source_play_id -> set of target bracket match IDs."""
        lookup: dict[int, set[int]] = defaultdict(set)
        for edge in self._division.follow_on_edges:
            lookup[edge.source_play_id].add(edge.target_match_id)
        return lookup

    def _build_follow_on_edges(self, all_match_infos: list[_MatchInfo], phase_map: dict[str, int]):
        """
        Fan-out edges from pool teams to unscheduled bracket matches.
        For each pool->bracket follow-on, connect ALL pool teams to the
        target bracket match's home/away ports. Uses edge_type="follow_on"
        so the frontend can style them as dashed/dimmed.
        """
        if not self._division.follow_on_edges:
            # No follow-on edges — emit any deferred ranking_end edges now
            for team_id, prev_endpoint in self._deferred_ranking_end.items():
                end_node_id = f"ranking_end_{team_id}"
                team_name = self._find_team_name(team_id) or f"Team {team_id}"
                if prev_endpoint in self._node_ids and end_node_id in self._node_ids:
                    self._add_edge(GraphEdge(
                        id=f"flow_{team_id}_{prev_endpoint}_to_end",
                        source=prev_endpoint,
                        target=end_node_id,
                        edge_type="team_flow",
                        team_id=team_id,
                        team_name=team_name,
                        role=None,
                        active=True,
                        label=None,
                    ))
            return

        follow_on_lookup = self._build_follow_on_lookup()
        pool_lookup = self._build_pool_lookup()

        # match_id -> _MatchInfo for target bracket matches
        match_info_by_id: dict[int, _MatchInfo] = {}
        for info in all_match_infos:
            match_info_by_id[info.match.match_id] = info

        # Source port for follow-on edges: use deferred last-port for teams
        # whose ranking_end was deferred; fall back to scanning edges for others.
        team_last_port: dict[int, str] = dict(self._deferred_ranking_end)
        for edge in self._edges:
            if edge.edge_type == "team_flow" and edge.team_id is not None:
                if edge.target.startswith("ranking_end_") and edge.team_id not in team_last_port:
                    team_last_port[edge.team_id] = edge.source

        # Track which bracket ports each deferred team connects to so we can
        # wire bracket_port → ranking_end after the fan-out.
        # deferred_bracket_ports[team_id] = list of port node ids
        deferred_bracket_ports: dict[int, list[str]] = defaultdict(list)

        for play_id, target_match_ids in follow_on_lookup.items():
            team_ids = pool_lookup.get(play_id, [])
            if not team_ids:
                continue

            for target_match_id in target_match_ids:
                target_info = match_info_by_id.get(target_match_id)
                if not target_info:
                    continue

                target_match = target_info.match
                # Only fan out to matches with no teams assigned
                if target_match.home_team is not None or target_match.away_team is not None:
                    continue

                target_node_id = target_info.node_id

                for team_id in team_ids:
                    source_port = team_last_port.get(team_id)
                    if not source_port:
                        continue

                    team_name = self._find_team_name(team_id) or f"Team {team_id}"

                    # Connect to home port
                    home_port_id = f"{target_node_id}_home"
                    if source_port in self._node_ids and home_port_id in self._node_ids:
                        self._add_edge(GraphEdge(
                            id=f"followon_{team_id}_{source_port}_to_{target_match_id}_home",
                            source=source_port,
                            target=home_port_id,
                            edge_type="follow_on",
                            team_id=team_id,
                            team_name=team_name,
                            role="potential",
                            active=True,
                            label=None,
                        ))
                        if team_id in self._deferred_ranking_end:
                            deferred_bracket_ports[team_id].append(home_port_id)

                    # Connect to away port
                    away_port_id = f"{target_node_id}_away"
                    if source_port in self._node_ids and away_port_id in self._node_ids:
                        self._add_edge(GraphEdge(
                            id=f"followon_{team_id}_{source_port}_to_{target_match_id}_away",
                            source=source_port,
                            target=away_port_id,
                            edge_type="follow_on",
                            team_id=team_id,
                            team_name=team_name,
                            role="potential",
                            active=True,
                            label=None,
                        ))
                        if team_id in self._deferred_ranking_end:
                            deferred_bracket_ports[team_id].append(away_port_id)

        # Wire bracket_port → ranking_end for deferred teams.
        # Each bracket port (home and away) gets its own edge to ranking_end so
        # that whichever slot the team ultimately fills, the flow continues.
        for team_id, prev_endpoint in self._deferred_ranking_end.items():
            end_node_id = f"ranking_end_{team_id}"
            team_name = self._find_team_name(team_id) or f"Team {team_id}"
            bracket_ports = deferred_bracket_ports.get(team_id, [])
            if bracket_ports:
                for bp in bracket_ports:
                    if bp in self._node_ids and end_node_id in self._node_ids:
                        self._add_edge(GraphEdge(
                            id=f"flow_{team_id}_{bp}_to_end",
                            source=bp,
                            target=end_node_id,
                            edge_type="team_flow",
                            team_id=team_id,
                            team_name=team_name,
                            role=None,
                            active=True,
                            label=None,
                        ))
            else:
                # No follow-on bracket was actually wired (e.g., target already
                # has teams assigned) — fall back to direct pool → ranking_end.
                if prev_endpoint in self._node_ids and end_node_id in self._node_ids:
                    self._add_edge(GraphEdge(
                        id=f"flow_{team_id}_{prev_endpoint}_to_end",
                        source=prev_endpoint,
                        target=end_node_id,
                        edge_type="team_flow",
                        team_id=team_id,
                        team_name=team_name,
                        role=None,
                        active=True,
                        label=None,
                    ))

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _get_team_role(self, match: Match, team_id: int) -> str | None:
        """Return the role ("home"/"away"/"work") a team plays in a match."""
        if match.home_team and match.home_team.team_id == team_id:
            return "home"
        if match.away_team and match.away_team.team_id == team_id:
            return "away"
        if match.work_team_id == team_id:
            return "work"
        return None

    def _find_team_name(self, team_id: int) -> str | None:
        """Look up team name from pre-built dict."""
        return self._team_name_map.get(team_id)

    def _add_node(self, node: GraphNode):
        if node.id not in self._node_ids:
            self._nodes.append(node)
            self._node_ids.add(node.id)

    def _add_edge(self, edge: GraphEdge):
        if edge.id not in self._edge_ids:
            self._edges.append(edge)
            self._edge_ids.add(edge.id)
