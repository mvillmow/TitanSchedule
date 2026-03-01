import re

from scraper.models import FollowOnEdge
from scraper.parsers.base import BaseParser

# Matches "1 - TeamName..." or "1st - TeamName..." — rank is the leading integer
_RANK_TEXT_RE = re.compile(r"^(\d+)")


class FollowOnParser(BaseParser):
    """
    Parses FutureRoundMatches from poolsheet responses to build DAG edges
    connecting pool finish positions to bracket match entries.

    Real AES FutureRoundMatches shape (discovered from live API):
    [
      {
        "RankText": "1 - Arbuckle 14 KJ (NC) (1)",
        "Match": {"MatchId": -55312, "Court": {...}, ...},
        "WorkMatch": null,
        "Play": {"PlayId": -55121, "CompleteShortName": "...", ...},
        "WorkTeamAssignmentDecided": true,
        "NextPendingReseed": false
      },
      ...
    ]

    Each entry maps one pool finish rank to one target bracket match.
    Match and Play can be null (future rounds not yet scheduled — skip those).
    """

    def __init__(
        self,
        future_matches: list[dict],
        source_play_id: int,
        event_key: str,
        division_id: int,
    ):
        super().__init__(future_matches, event_key, division_id)
        self._source_play_id = source_play_id

    def parse(self) -> list[FollowOnEdge]:
        edges = []
        for item in self._data:
            # Skip entries where the bracket match isn't scheduled yet
            match_obj = item.get("Match")
            if not match_obj:
                continue

            match_id = match_obj.get("MatchId")
            if match_id is None:
                continue

            rank_text = item.get("RankText", "")
            rank = self._extract_rank(rank_text)
            if rank is None:
                continue

            edges.append(
                FollowOnEdge(
                    source_play_id=self._source_play_id,
                    source_rank=rank,
                    source_text=rank_text,
                    target_match_id=match_id,
                    target_text=rank_text,
                )
            )

        return edges

    def _extract_rank(self, rank_text: str) -> int | None:
        """Extract the leading integer rank from RankText like '1 - TeamName...'"""
        m = _RANK_TEXT_RE.match(rank_text.strip())
        if not m:
            return None
        return int(m.group(1))
