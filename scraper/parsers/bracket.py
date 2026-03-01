from scraper.models import BracketMatch, Court, Match, MatchStatus, SetScore, Team
from scraper.parsers.base import BaseParser


class BracketParser(BaseParser):
    """
    Parses bracket tree structure from the brackets API endpoint.

    Real AES bracket list shape:
    [
      {
        "PlayId": -55121, "FullName": "Gold A", ...,
        "Roots": [
          {
            "Key": 0, "X": 1.0, "Y": 3.0,
            "Reversed": false, "DoubleCapped": false,
            "Match": { "MatchId": ..., "FirstTeam": {...}, ... },
            "TopSource": { ... recursive node ... },
            "BottomSource": { ... recursive node ... }
          },
          ...
        ]
      },
      ...
    ]

    Each bracket in the list has its own PlayId.
    The tree uses TopSource/BottomSource (not Children) for recursive structure.
    Flattens each bracket tree into a list of BracketMatch objects,
    stamping each match with the bracket's PlayId.
    """

    def parse(self) -> list[BracketMatch]:
        bracket_matches = []
        data = self._data if isinstance(self._data, list) else [self._data]
        for bracket_data in data:
            play_id = bracket_data.get("PlayId")
            for root in bracket_data.get("Roots", []):
                self._flatten_bracket_tree(root, bracket_matches, play_id)
        return bracket_matches

    def _flatten_bracket_tree(
        self, node: dict, result: list[BracketMatch], play_id: int | None
    ):
        """Recursively flatten bracket tree into a list of BracketMatch."""
        match_data = node.get("Match")
        if not match_data:
            return

        match = self._parse_bracket_match(match_data, play_id)
        result.append(
            BracketMatch(
                match=match,
                x=node.get("X", 0.0),
                y=node.get("Y", 0.0),
                key=node.get("Key", 0),
                reversed=node.get("Reversed", False),
                double_capped=node.get("DoubleCapped", False),
            )
        )

        # Recurse into TopSource and BottomSource (real AES tree structure)
        for child_key in ("TopSource", "BottomSource", "Children"):
            child = node.get(child_key)
            if child is None:
                continue
            if isinstance(child, list):
                for c in child:
                    self._flatten_bracket_tree(c, result, play_id)
            elif isinstance(child, dict):
                self._flatten_bracket_tree(child, result, play_id)

    def _parse_bracket_match(self, data: dict, play_id: int | None) -> Match:
        """Parse a bracket match, handling both populated teams and placeholders."""
        home_team = self._extract_team(data, "FirstTeam", "FirstTeamText")
        away_team = self._extract_team(data, "SecondTeam", "SecondTeamText")

        home_placeholder = data.get("FirstTeamText") if home_team is None else None
        away_placeholder = data.get("SecondTeamText") if away_team is None else None

        set_scores = []
        for s in data.get("Sets", []):
            if s.get("FirstTeamScore") is not None and s.get("SecondTeamScore") is not None:
                set_scores.append(
                    SetScore(
                        home_score=s["FirstTeamScore"],
                        away_score=s["SecondTeamScore"],
                        score_text=s.get("ScoreText", ""),
                        is_deciding_set=s.get("IsDecidingSet", False),
                    )
                )

        status = MatchStatus.SCHEDULED
        if data.get("HasScores", False):
            if data.get("FirstTeamWon") is not None:
                status = MatchStatus.FINISHED
            else:
                status = MatchStatus.IN_PROGRESS

        court = None
        if data.get("Court"):
            c = data["Court"]
            court = Court(c["CourtId"], c["Name"], c.get("VideoLink"))

        # Work team
        work_team_text = None
        work_team_id = None
        if data.get("WorkTeam"):
            work_team_text = data.get("WorkTeamText")
            work_team_id = data["WorkTeam"].get("TeamId")

        return Match(
            match_id=data["MatchId"],
            match_name=data.get("FullName", ""),
            match_short_name=data.get("ShortName", ""),
            home_team=home_team,
            away_team=away_team,
            home_placeholder=home_placeholder,
            away_placeholder=away_placeholder,
            court=court,
            scheduled_start=self._parse_datetime(data.get("ScheduledStartDateTime")),
            scheduled_end=self._parse_datetime(data.get("ScheduledEndDateTime")),
            status=status,
            set_scores=set_scores,
            has_scores=data.get("HasScores", False),
            home_won=data.get("FirstTeamWon") if status == MatchStatus.FINISHED else None,
            work_team_text=work_team_text,
            work_team_id=work_team_id,
            play_id=play_id,
        )

    def _extract_team(self, data: dict, team_key: str, text_key: str) -> Team | None:
        """Extract team from bracket data. Returns None if slot is empty/placeholder."""
        team_data = data.get(team_key)
        if not team_data or not team_data.get("TeamId"):
            return None
        return Team(
            team_id=team_data["TeamId"],
            name=team_data.get("Name", ""),
            display_text=data.get(text_key, ""),
            code=team_data.get("Code", team_data.get("TeamCode", "")),
            club_name=(
                team_data.get("Club", {}).get("Name") if team_data.get("Club") else None
            ),
            club_id=(
                team_data.get("Club", {}).get("ClubId") if team_data.get("Club") else None
            ),
        )
