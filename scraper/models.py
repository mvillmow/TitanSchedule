from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MatchStatus(Enum):
    """Status of a match in the tournament."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"
    FORFEIT = "forfeit"


class PlayType(Enum):
    """Type of play in AES: pool (round-robin) or bracket (elimination)."""

    POOL = 0
    BRACKET = 1


@dataclass(frozen=True)
class SetScore:
    """Score for a single set in a match."""

    home_score: int
    away_score: int
    score_text: str
    is_deciding_set: bool


@dataclass(frozen=True)
class Court:
    """Court assignment for a match."""

    court_id: int
    name: str
    video_link: str | None


@dataclass
class Team:
    """A team participating in the tournament."""

    team_id: int | None
    name: str
    display_text: str
    code: str
    club_name: str | None = None
    club_id: int | None = None
    seed: int | None = None
    aes_url: str | None = None


@dataclass
class TeamStanding:
    """A team's standings within a pool."""

    team: Team
    matches_won: int
    matches_lost: int
    match_percent: float
    sets_won: int
    sets_lost: int
    set_percent: float
    point_ratio: float
    finish_rank: int | None
    finish_rank_text: str | None


@dataclass
class Match:
    """A single match (game) in the tournament."""

    match_id: int
    match_name: str
    match_short_name: str
    home_team: Team | None = None
    away_team: Team | None = None
    home_placeholder: str | None = None
    away_placeholder: str | None = None
    court: Court | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    status: MatchStatus = MatchStatus.SCHEDULED
    set_scores: list[SetScore] = field(default_factory=list)
    has_scores: bool = False
    home_won: bool | None = None
    work_team_text: str | None = None
    work_team_id: int | None = None
    play_id: int | None = None


@dataclass
class Pool:
    """A pool (round-robin group) within a round."""

    play_id: int
    full_name: str
    short_name: str
    complete_name: str
    complete_short_name: str
    round_id: int
    round_name: str
    match_description: str
    teams: list[TeamStanding] = field(default_factory=list)
    matches: list[Match] = field(default_factory=list)
    courts: list[Court] = field(default_factory=list)
    order: int = 0


@dataclass
class BracketMatch:
    """A match node within a bracket, with layout positioning."""

    match: Match
    x: float
    y: float
    key: int
    reversed: bool = False
    double_capped: bool = False


@dataclass
class Bracket:
    """A bracket (elimination tree) within a round."""

    play_id: int
    full_name: str
    short_name: str
    complete_name: str
    complete_short_name: str
    round_id: int
    round_name: str
    group_name: str
    bracket_matches: list[BracketMatch] = field(default_factory=list)
    courts: list[Court] = field(default_factory=list)
    order: int = 0


@dataclass
class FollowOnEdge:
    """An edge connecting a pool finish position to a bracket/match entry."""

    source_play_id: int
    source_rank: int | None
    source_text: str
    target_match_id: int
    target_text: str


@dataclass
class Round:
    """A round in the tournament (e.g., Round 1, Crossover, Gold)."""

    round_id: int
    round_name: str
    pools: list[Pool] = field(default_factory=list)
    brackets: list[Bracket] = field(default_factory=list)


@dataclass
class Division:
    """Complete data for one division of the tournament."""

    division_id: int
    name: str
    event_key: str
    event_name: str
    rounds: list[Round] = field(default_factory=list)
    follow_on_edges: list[FollowOnEdge] = field(default_factory=list)
    all_teams: list[Team] = field(default_factory=list)
    aes_url: str | None = None
    scraped_at: datetime | None = None
