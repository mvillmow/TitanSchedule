"""BracketParser — extracts bracket matches from /brackets/{date} response."""

from __future__ import annotations

from typing import Any

from scraper.models import BracketMatch, Court, SetScore


def _parse_datetime(dt_str: str) -> tuple[str, str]:
    """Extract date and time from ISO datetime like '2026-01-31T08:00:00'."""
    if not dt_str or "T" not in dt_str:
        return "", ""
    date_part, time_part = dt_str.split("T", 1)
    return date_part, time_part[:5]


def parse_brackets(data: list[dict[str, Any]]) -> list[BracketMatch]:
    """Parse the brackets API response into a list of BracketMatch models.

    AES API uses First/Second instead of Home/Away, nested Court objects,
    ISO datetime, and TypeOfOutcome for match status.
    """
    matches: list[BracketMatch] = []

    for m in data:
        # Parse set scores — API uses Sets with FirstTeamScore/SecondTeamScore
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

        # Parse courts
        courts: list[Court] = []
        courts_data: list[dict[str, Any]] = m.get("Courts") or []
        for c in courts_data:
            courts.append(
                Court(
                    id=int(c.get("CourtId") or 0),
                    name=str(c.get("Name") or c.get("CourtName") or ""),
                    video_link=c.get("VideoLink"),
                )
            )

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
        type_of_outcome = m.get("TypeOfOutcome", 0)
        if type_of_outcome == 2:
            is_finished = True
        is_in_progress = type_of_outcome == 1

        matches.append(
            BracketMatch(
                id=int(m.get("MatchId", 0)),
                home_team_id=m.get("FirstTeamId"),
                away_team_id=m.get("SecondTeamId"),
                home_team_name=str(m.get("FirstTeamName", "")),
                away_team_name=str(m.get("SecondTeamName", "")),
                work_team_id=m.get("WorkTeamId"),
                work_team_name=str(m.get("WorkTeamText", "")),
                court=court_name,
                date=date,
                time=time,
                scores=scores,
                home_sets_won=first_sets_won,
                away_sets_won=second_sets_won,
                is_finished=is_finished,
                is_in_progress=is_in_progress,
                home_seed=m.get("FirstTeamSeed") or m.get("HomeSeed"),
                away_seed=m.get("SecondTeamSeed") or m.get("AwaySeed"),
                group_id=m.get("GroupId"),
                group_name=str(m.get("GroupName", "")),
                order=int(m.get("Order", 0)),
                courts=courts,
            )
        )

    return matches
