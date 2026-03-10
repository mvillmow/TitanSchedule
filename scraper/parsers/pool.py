"""PoolParser — extracts matches, teams, and standings from poolsheet response."""

from __future__ import annotations

import logging
from typing import Any

from scraper.models import Match, Pool, PoolStanding, SetScore, Team

logger = logging.getLogger(__name__)


def _parse_datetime(dt_str: str) -> tuple[str, str]:
    """Extract date and time from ISO datetime like '2026-01-31T08:00:00'."""
    if not dt_str or "T" not in dt_str:
        return "", ""
    date_part, time_part = dt_str.split("T", 1)
    # Truncate time to HH:MM
    return date_part, time_part[:5]


def parse_pool_sheet(data: dict[str, Any]) -> Pool:
    """Parse a poolsheet API response into a Pool model.

    The API returns: {"Pool": {...}, "Matches": [...], "FutureRoundMatches": [...]}
    Pool contains team info. Matches are at the top level, not inside Pool.
    """
    # Unwrap: API returns {"Pool": {...}, "Matches": [...]} at top level
    pool_data: dict[str, Any] = data.get("Pool", data)
    top_matches: list[dict[str, Any]] = data.get("Matches") or []

    play_id = int(pool_data.get("PlayId", 0))
    name = str(pool_data.get("FullName", "") or pool_data.get("Name", ""))

    # Parse teams — API uses Club.Name, FinishRank, MatchesWon/Lost
    teams: list[Team] = []
    standings: list[PoolStanding] = []
    teams_data: list[dict[str, Any]] = pool_data.get("Teams") or []
    for t in teams_data:
        team_id = int(t.get("TeamId") or 0)
        team_name = str(t.get("TeamName") or "Unknown")
        club_obj = t.get("Club")
        club_name = str(club_obj.get("Name", "")) if isinstance(club_obj, dict) else ""
        seed = t.get("Seed")

        teams.append(Team(id=team_id, name=team_name, club=club_name, seed=seed))

        # Build standings from team data (FinishRank, MatchesWon, MatchesLost)
        rank = t.get("FinishRank")
        if rank is not None:
            standings.append(
                PoolStanding(
                    team_id=team_id,
                    team_name=team_name,
                    rank=int(rank),
                    wins=int(t.get("MatchesWon", 0)),
                    losses=int(t.get("MatchesLost", 0)),
                )
            )

    # Parse matches — API uses First/Second instead of Home/Away
    matches: list[Match] = []
    for m in top_matches:
        scores: list[SetScore] = []
        sets_data: list[dict[str, Any]] = m.get("Sets") or []
        first_sets_won = 0
        second_sets_won = 0
        for s in sets_data:
            first_score = int(s.get("FirstTeamScore") or 0)
            second_score = int(s.get("SecondTeamScore") or 0)
            scores.append(SetScore(home=first_score, away=second_score))
            if first_score > second_score:
                first_sets_won += 1
            elif second_score > first_score:
                second_sets_won += 1

        # Extract court name from nested Court object
        court_obj = m.get("Court")
        court_name = str(court_obj.get("Name", "")) if isinstance(court_obj, dict) else ""

        # Extract date and time from ScheduledStartDateTime
        date, time = _parse_datetime(str(m.get("ScheduledStartDateTime", "")))

        # Determine finished/in-progress state
        has_scores = bool(m.get("HasScores", False))
        first_won = m.get("FirstTeamWon")
        second_won = m.get("SecondTeamWon")
        is_finished = has_scores and (first_won is True or second_won is True)
        # TypeOfOutcome: 0=not played, 1=in progress, 2=finished
        type_of_outcome = m.get("TypeOfOutcome", 0)
        if type_of_outcome == 2:
            is_finished = True
        is_in_progress = type_of_outcome == 1

        # Work team — API has WorkTeamId and WorkTeamText (not WorkTeamName)
        work_team_id = m.get("WorkTeamId")
        work_team_name = str(m.get("WorkTeamText", ""))

        matches.append(
            Match(
                id=int(m.get("MatchId", 0)),
                home_team_id=m.get("FirstTeamId"),
                away_team_id=m.get("SecondTeamId"),
                home_team_name=str(m.get("FirstTeamName", "")),
                away_team_name=str(m.get("SecondTeamName", "")),
                work_team_id=work_team_id,
                work_team_name=work_team_name,
                court=court_name,
                date=date,
                time=time,
                scores=scores,
                home_sets_won=first_sets_won,
                away_sets_won=second_sets_won,
                is_finished=is_finished,
                is_in_progress=is_in_progress,
            )
        )

    if not matches:
        logger.warning("Pool %r (PlayId=%d) has no matches", name, play_id)

    return Pool(
        play_id=play_id,
        name=name,
        matches=matches,
        standings=standings,
        teams=teams,
    )
