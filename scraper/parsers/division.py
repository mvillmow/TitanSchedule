"""DivisionParser — extracts rounds from /division/{id}/plays response."""

from __future__ import annotations

from typing import Any

from scraper.models import Round


def parse_division_plays(data: list[dict[str, Any]] | dict[str, Any]) -> list[Round]:
    """Parse the plays response into a sorted list of Rounds.

    Accepts either a raw list of plays or the wrapped {"Division": ..., "Plays": [...]} format.
    Rounds are sorted by round_id descending (less-negative = earlier round)
    for chronological order.
    """
    # Unwrap if API returned {"Division": ..., "Plays": [...]}
    plays: list[dict[str, Any]] = (
        data.get("Plays", data) if isinstance(data, dict) else data
    )

    rounds: list[Round] = []
    for play in plays:
        round_id = int(play.get("RoundId", 0))
        round_type = "bracket" if play.get("Type") == 1 else "pool"
        group_id_raw = play.get("GroupId")
        play_id_raw = play.get("PlayId")
        rounds.append(
            Round(
                id=round_id,
                name=str(play.get("RoundName", "")),
                short_name=str(play.get("CompleteShortName", "")),
                type=round_type,
                group_id=int(group_id_raw) if group_id_raw else None,
                group_name=str(play.get("GroupName", "")),
                play_id=int(play_id_raw) if play_id_raw is not None else None,
                order=int(play.get("Order", 0)),
                date=str(play.get("Date", "")),
            )
        )

    # Sort by id descending — less negative = earlier round
    rounds.sort(key=lambda r: r.id, reverse=True)
    return rounds
