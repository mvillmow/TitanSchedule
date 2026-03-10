"""PoolParser — extracts matches, teams, and standings from poolsheet response."""

from __future__ import annotations

import logging
from typing import Any

from scraper.models import Match, Pool, PoolStanding, SetScore, Team

logger = logging.getLogger(__name__)


def parse_pool_sheet(data: dict[str, Any]) -> Pool:
    """Parse a poolsheet API response into a Pool model.

    Handles empty pools (no matches) and missing team data gracefully.
    Logs a warning for empty pools.
    """
    play_id: int = int(data.get("PlayId", 0))
    name: str = str(data.get("Name", ""))

    # Parse teams
    teams: list[Team] = []
    teams_data: list[dict[str, Any]] = data.get("Teams") or []
    for t in teams_data:
        teams.append(
            Team(
                id=int(t.get("TeamId", 0)),
                name=str(t.get("TeamName", "Unknown")),
                club=str(t.get("ClubName", "")),
                seed=t.get("Seed"),
            )
        )

    # Parse matches
    matches: list[Match] = []
    matches_data: list[dict[str, Any]] = data.get("Matches") or []
    for m in matches_data:
        scores: list[SetScore] = []
        set_scores: list[dict[str, Any]] = m.get("SetScores") or []
        for s in set_scores:
            scores.append(
                SetScore(
                    home=int(s.get("HomeScore", 0)),
                    away=int(s.get("AwayScore", 0)),
                )
            )
        matches.append(
            Match(
                id=int(m.get("MatchId", 0)),
                home_team_id=m.get("HomeTeamId"),
                away_team_id=m.get("AwayTeamId"),
                home_team_name=str(m.get("HomeTeamName", "")),
                away_team_name=str(m.get("AwayTeamName", "")),
                work_team_id=m.get("WorkTeamId"),
                work_team_name=str(m.get("WorkTeamName", "")),
                court=str(m.get("CourtName", "")),
                date=str(m.get("MatchDate", "")),
                time=str(m.get("MatchTime", "")),
                scores=scores,
                home_sets_won=int(m.get("HomeSetsWon", 0)),
                away_sets_won=int(m.get("AwaySetsWon", 0)),
                is_finished=bool(m.get("IsFinished", False)),
                is_in_progress=bool(m.get("IsInProgress", False)),
            )
        )

    # Parse standings
    standings: list[PoolStanding] = []
    standings_data: list[dict[str, Any]] = data.get("Standings") or []
    for s in standings_data:
        standings.append(
            PoolStanding(
                team_id=int(s.get("TeamId", 0)),
                team_name=str(s.get("TeamName", "Unknown")),
                rank=int(s.get("Rank", 0)),
                wins=int(s.get("Wins", 0)),
                losses=int(s.get("Losses", 0)),
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
