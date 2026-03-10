"""Data models for AES API responses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Team:
    """A team in the tournament."""

    id: int
    name: str
    club: str = ""
    seed: int | None = None


@dataclass(slots=True)
class SetScore:
    """Score for a single set."""

    home: int
    away: int


@dataclass(slots=True)
class Court:
    """A court assignment."""

    id: int
    name: str
    video_link: str | None = None


@dataclass(slots=True)
class Match:
    """A pool-play match."""

    id: int
    home_team_id: int | None = None
    away_team_id: int | None = None
    home_team_name: str = ""
    away_team_name: str = ""
    work_team_id: int | None = None
    work_team_name: str = ""
    court: str = ""
    date: str = ""
    time: str = ""
    scores: list[SetScore] = field(default_factory=list)
    home_sets_won: int = 0
    away_sets_won: int = 0
    is_finished: bool = False
    is_in_progress: bool = False


@dataclass(slots=True)
class PoolStanding:
    """A team's standing within a pool."""

    team_id: int
    team_name: str
    rank: int
    wins: int = 0
    losses: int = 0


@dataclass(slots=True)
class Pool:
    """A pool with matches and standings."""

    play_id: int
    name: str
    matches: list[Match] = field(default_factory=list)
    standings: list[PoolStanding] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)


@dataclass(slots=True)
class BracketMatch(Match):
    """A bracket match with additional seed and group info."""

    home_seed: int | None = None
    away_seed: int | None = None
    group_id: int | None = None
    group_name: str = ""
    order: int = 0
    courts: list[Court] = field(default_factory=list)


@dataclass(slots=True)
class Round:
    """A round within a division."""

    id: int
    name: str
    short_name: str = ""
    type: str = "pool"  # "pool" or "bracket"
    group_id: int | None = None
    group_name: str = ""
    play_id: int | None = None
    order: int = 0
    date: str = ""


@dataclass(slots=True)
class FollowOnEdge:
    """Links a pool standing rank to a bracket seed slot."""

    source_round_id: int
    source_rank: int
    target_round_id: int
    target_slot: str


@dataclass(slots=True)
class Division:
    """A tournament division containing rounds, pools, and brackets."""

    id: int
    name: str
    rounds: list[Round] = field(default_factory=list)
    pools: list[Pool] = field(default_factory=list)
    bracket_matches: list[BracketMatch] = field(default_factory=list)
    follow_ons: list[FollowOnEdge] = field(default_factory=list)
    teams: dict[int, Team] = field(default_factory=dict)
    dates: list[str] = field(default_factory=list)
    is_finished: bool = False
    color_hex: str = ""
    code_alias: str = ""
