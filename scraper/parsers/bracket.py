"""BracketParser — extracts bracket matches from /brackets/{date} response."""

from __future__ import annotations

from typing import Any

from scraper.models import BracketMatch, Court, SetScore


def parse_brackets(data: list[dict[str, Any]]) -> list[BracketMatch]:
    """Parse the brackets API response into a list of BracketMatch models."""
    matches: list[BracketMatch] = []

    for m in data:
        scores: list[SetScore] = []
        set_scores: list[dict[str, Any]] = m.get("SetScores") or []
        for s in set_scores:
            scores.append(
                SetScore(
                    home=int(s.get("HomeScore", 0)),
                    away=int(s.get("AwayScore", 0)),
                )
            )

        courts: list[Court] = []
        courts_data: list[dict[str, Any]] = m.get("Courts") or []
        for c in courts_data:
            courts.append(
                Court(
                    id=int(c.get("CourtId", 0)),
                    name=str(c.get("CourtName", "")),
                    video_link=c.get("VideoLink"),
                )
            )

        matches.append(
            BracketMatch(
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
                home_seed=m.get("HomeSeed"),
                away_seed=m.get("AwaySeed"),
                group_id=m.get("GroupId"),
                group_name=str(m.get("GroupName", "")),
                order=int(m.get("Order", 0)),
                courts=courts,
            )
        )

    return matches
