"""FollowOnParser — parses advancement text linking pool results to bracket seeds."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class FollowOnRef:
    """Parsed follow-on reference from FutureRoundMatches text.

    Attributes:
        rank: The placement rank (e.g., 1 for "1st").
        source_short_name: The CompleteShortName of the source play (e.g., "R1P1").
    """

    rank: int
    source_short_name: str


def parse_follow_on(text: str) -> FollowOnRef | None:
    """Parse follow-on text like '1st R1P1' into a FollowOnRef.

    The text format is "{rank}{ordinal} {CompleteShortName}" where:
    - rank is a leading integer (1, 2, 3, ...)
    - ordinal suffix is optional (st, nd, rd, th)
    - CompleteShortName identifies the source pool (e.g., "R1P1")

    Args:
        text: The FutureRoundMatches rank text (e.g., "1st R1P1", "2nd R1P1").

    Returns:
        A FollowOnRef if parseable, None otherwise.
    """
    if not text:
        return None

    # Extract leading rank number with optional ordinal suffix (1st, 2nd, 3rd, 4th)
    rank_match = re.match(r"^(\d+)(?:st|nd|rd|th)?", text)
    if not rank_match:
        return None

    rank = int(rank_match.group(1))
    source_short_name = text[rank_match.end() :].strip()

    return FollowOnRef(rank=rank, source_short_name=source_short_name)
