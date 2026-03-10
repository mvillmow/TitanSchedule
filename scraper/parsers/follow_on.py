"""FollowOnParser — parses advancement text linking pool results to bracket seeds."""

from __future__ import annotations

import re

from scraper.models import FollowOnEdge


def parse_follow_on(
    text: str, source_round_id: int, target_round_id: int
) -> FollowOnEdge | None:
    """Parse follow-on text like '1st R1P1' into a FollowOnEdge.

    Args:
        text: The FutureRoundMatches rank text (e.g., "1st R1P1", "2nd R1P1").
        source_round_id: The round ID of the source pool.
        target_round_id: The round ID of the target bracket.

    Returns:
        A FollowOnEdge if parseable, None otherwise.
    """
    if not text:
        return None

    # Extract leading rank number with optional ordinal suffix (1st, 2nd, 3rd, 4th)
    rank_match = re.match(r"^(\d+)(?:st|nd|rd|th)?", text)
    if not rank_match:
        return None

    rank = int(rank_match.group(1))

    # The remaining text after the rank is the target slot identifier
    target_slot = text[rank_match.end() :].strip()

    return FollowOnEdge(
        source_round_id=source_round_id,
        source_rank=rank,
        target_round_id=target_round_id,
        target_slot=target_slot,
    )
