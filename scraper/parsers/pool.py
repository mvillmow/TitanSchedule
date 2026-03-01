import re

from scraper.models import Court, Match, MatchStatus, Pool, SetScore, Team, TeamStanding
from scraper.parsers.base import BaseParser

_SEED_RE = re.compile(r"\((\d+)\)")


class PoolParser(BaseParser):
    """
    Parses a single poolsheet API response into a Pool with matches and standings.

    Input JSON shape: {"Pool": {..., "Teams": [...]}, "Matches": [...], "FutureRoundMatches": [...]}
    """

    def parse(self) -> Pool:
        pool_data = self._data.get("Pool") or {}
        full_name = pool_data.get("FullName", "")
        short_name = pool_data.get("ShortName", "")
        pool = Pool(
            play_id=pool_data.get("PlayId", 0),
            full_name=full_name,
            short_name=short_name,
            complete_name=pool_data.get("CompleteFullName", full_name),
            complete_short_name=pool_data.get("CompleteShortName", short_name),
            round_id=0,
            round_name="",
            match_description=pool_data.get("MatchDescription", ""),
            courts=[
                Court(c["CourtId"], c["Name"], c.get("VideoLink"))
                for c in pool_data.get("Courts", [])
                if c.get("CourtId") is not None and c.get("Name") is not None
            ],
        )

        for t in pool_data.get("Teams", []):
            if t.get("TeamId") is None:
                continue  # Skip placeholder/unassigned team slots
            team = self._parse_team(t)
            pool.teams.append(
                TeamStanding(
                    team=team,
                    matches_won=t.get("MatchesWon", 0),
                    matches_lost=t.get("MatchesLost", 0),
                    match_percent=t.get("MatchPercent", 0.0),
                    sets_won=t.get("SetsWon", 0),
                    sets_lost=t.get("SetsLost", 0),
                    set_percent=t.get("SetPercent", 0.0),
                    point_ratio=t.get("PointRatio", 0.0),
                    finish_rank=t.get("FinishRank"),
                    finish_rank_text=t.get("FinishRankText"),
                )
            )

        for m in self._data.get("Matches", []):
            pool.matches.append(self._parse_match(m, pool.play_id))

        return pool

    def _parse_team(self, data: dict) -> Team:
        return Team(
            team_id=data["TeamId"],
            name=data["TeamName"],
            display_text=data.get("TeamText", data["TeamName"]),
            code=data.get("TeamCode", ""),
            club_name=data.get("Club", {}).get("Name") if data.get("Club") else None,
            club_id=data.get("Club", {}).get("ClubId") if data.get("Club") else None,
            seed=self._extract_seed(data.get("TeamText", "")),
            aes_url=self._build_aes_url(f"divisions/{self._division_id}/teams"),
        )

    def _parse_match(self, data: dict, play_id: int) -> Match:
        status = self._determine_status(data)

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

        court = None
        if data.get("Court"):
            c = data["Court"]
            court = Court(c["CourtId"], c["Name"], c.get("VideoLink"))

        home_won = None
        if status == MatchStatus.FINISHED:
            home_won = data.get("FirstTeamWon")

        return Match(
            match_id=data["MatchId"],
            match_name=data.get("MatchFullName", ""),
            match_short_name=data.get("MatchShortName", ""),
            home_team=(
                self._parse_team_minimal(data, "First")
                if data.get("FirstTeamId") is not None
                else None
            ),
            away_team=(
                self._parse_team_minimal(data, "Second")
                if data.get("SecondTeamId") is not None
                else None
            ),
            home_placeholder=(
                data.get("FirstTeamText") if not data.get("FirstTeamId") else None
            ),
            away_placeholder=(
                data.get("SecondTeamText") if not data.get("SecondTeamId") else None
            ),
            court=court,
            scheduled_start=self._parse_datetime(data.get("ScheduledStartDateTime")),
            scheduled_end=self._parse_datetime(data.get("ScheduledEndDateTime")),
            status=status,
            set_scores=set_scores,
            has_scores=data.get("HasScores", False),
            home_won=home_won,
            work_team_text=data.get("WorkTeamText"),
            work_team_id=data.get("WorkTeamId"),
            play_id=play_id,
        )

    def _determine_status(self, data: dict) -> MatchStatus:
        """
        Determine match status from API fields.
        - HasScores=True + FirstTeamWon set → FINISHED
        - HasScores=True + no Won flag → IN_PROGRESS
        - HasScores=False → SCHEDULED
        """
        if not data.get("HasScores", False):
            return MatchStatus.SCHEDULED
        if data.get("FirstTeamWon") is not None:
            return MatchStatus.FINISHED
        return MatchStatus.IN_PROGRESS

    def _extract_seed(self, text: str) -> int | None:
        """
        Extract seed from AES TeamText format: 'Team Name (REGION) (SEED)'
        The last parenthetical containing a number is the seed.
        """
        matches = _SEED_RE.findall(text)
        return int(matches[-1]) if matches else None

    def _parse_team_minimal(self, data: dict, prefix: str) -> Team:
        """Extract minimal Team from a match object using 'First' or 'Second' prefix."""
        return Team(
            team_id=data[f"{prefix}TeamId"],
            name=data.get(f"{prefix}TeamName", ""),
            display_text=data.get(f"{prefix}TeamText", ""),
            code="",
        )
