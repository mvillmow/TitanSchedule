"""DivisionParser — extracts rounds from /division/{id}/plays response."""

from __future__ import annotations

from typing import Any

from scraper.models import Round


def parse_division_plays(data: list[dict[str, Any]]) -> list[Round]:
    """Parse the plays response into a sorted list of Rounds.

    Rounds are sorted by round_id descending (less-negative = earlier round)
    for chronological order.
    """
    rounds: list[Round] = []
    for play in data:
        round_id = int(play.get("RoundId", 0))
        round_type = "bracket" if play.get("Type") == 1 else "pool"
        group_id_raw = play.get("GroupId")
        rounds.append(
            Round(
                id=round_id,
                name=str(play.get("RoundName", "")),
                short_name=str(play.get("CompleteShortName", "")),
                type=round_type,
                group_id=int(group_id_raw) if group_id_raw else None,
                group_name=str(play.get("GroupName", "")),
            )
        )

    # Sort by id descending — less negative = earlier round
    rounds.sort(key=lambda r: r.id, reverse=True)
    return rounds
