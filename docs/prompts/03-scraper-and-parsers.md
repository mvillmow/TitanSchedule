# Prompt 03: Scraper and Parsers

Implement the data layer from scratch per `docs/research.md`. **Greenfield — write all code new.**

## What to Implement

### `scraper/models.py` — Complete Data Models

Dataclasses (or attrs) for the full domain model:

- `Team(id: int, name: str, club: str | None)`
- `SetScore(home: int, away: int)`
- `Match(id: int, home_team_id: int, away_team_id: int, work_team_id: int | None, court: str | None, time: str | None, date: str | None, status: str, scores: list[SetScore], round_id: int, round_name: str, play_id: int | None)`
- `PoolStanding(team_id: int, rank: int, wins: int, losses: int)`
- `Court(court_id: int, name: str, video_link: str | None)`
- `Pool(id: int, name: str, matches: list[Match], standings: list[PoolStanding], group_id: int | None, group_name: str | None, order: int | None, courts: list[Court])`
- `BracketMatch` — extends Match with bracket-specific fields: `home_seed: int | None`, `away_seed: int | None`, `group_id: int | None`, `group_name: str | None`, `order: int | None`, `courts: list[Court]`
- `Round(id: int, name: str, short_name: str, type: str, group_id: int | None, group_name: str | None)` — type is "pool" or "bracket"
- `FollowOnEdge(source_round_id: int, source_rank: int, target_round_id: int, target_slot: str)`
- `Division(id: int, name: str, rounds: list[Round], pools: list[Pool], bracket_matches: list[Match], follow_ons: list[FollowOnEdge], teams: dict[int, Team], is_finished: bool, color_hex: str | None, code_alias: str | None)`

All IDs are negative integers (AES convention).

### `scraper/client.py` — Async HTTP Client

- Uses `httpx.AsyncClient`
- Configurable base URL, headers from `config.py`, default timeout 30s
- Methods: `get_event(key)`, `get_division_plays(key, div_id)`, `get_pool_sheet(key, play_id)`, `get_brackets(key, div_id, date)`, `get_pools(key, div_id, date)`
- Rate limiting: configurable delay between requests
- Retry with exponential backoff on 429/5xx
- Returns parsed JSON (dict), raises on errors

### `scraper/url.py` — AES URL Parser

- Parse AES URLs like `https://results.advancedeventsystems.com/event/12345/division/-67890/schedule`
- Extract: event_key, division_id
- Handle various URL formats AES uses

### `scraper/parsers/division.py` — DivisionParser

- Input: JSON from `/event/{key}/division/{id}/plays`
- Output: list of `Round` objects
- Sort rounds by `round_id` descending (less-negative = earlier = first)
- Handle mixed Type 0 (pool) + Type 1 (bracket/crossover) plays within the same round

### `scraper/parsers/pool.py` — PoolParser

- Input: JSON from `/event/{key}/poolsheet/{playId}`
- Output: `Pool` object with matches and standings
- Extract teams, match details, set scores, standings with ranks

### `scraper/parsers/bracket.py` — BracketParser

- Input: JSON from `/event/{key}/division/{id}/brackets/{date}`
- Output: list of `Match` objects for bracket play
- Handle bracket-specific fields (seeds, advancement)

### `scraper/parsers/follow_on.py` — FollowOnParser

- Input: FutureRoundMatches text from AES (e.g., "1st R1P1")
- Output: `FollowOnEdge` linking pool rank to bracket slot
- Regex `^(\d+)` to extract leading integer rank from RankText
- Parse CompleteShortName references — concatenated format of round+group+shortname (e.g., "R1P1" = Round 1 Pool 1). Used in FutureRoundMatches text like "1st R1P1" meaning "1st place from Round 1 Pool 1"

### `scraper/parsers/__init__.py`
Re-export all parsers for convenience.

### Defensive Parsing
- Never crash on missing/null fields — use sensible defaults
- Log warnings for unexpected structure but continue processing
- Empty pools (no matches) should produce a Pool with empty lists
- Missing team names → use "Unknown Team (ID: {id})"
- Missing scores on finished matches → empty scores list with warning

### Tournament Format Handling

**Power League** (multi-date, tiered groups):
- Multiple rounds across 4-6 dates with tiered groups (Gold/Silver/Bronze)
- `group_id`/`group_name` fields track tier sub-divisions
- Re-seeding between rounds — teams may move between tiers

**Single-Weekend Tournament** (pool → bracket, mixed types):
- Same round can contain both Type 0 (pool) and Type 1 (bracket/crossover) plays
- DivisionParser must handle mixed types within a single round

**Pool-Play-Only Divisions** (Jamboree format):
- Some divisions have zero bracket rounds and zero follow-on edges
- DivisionParser must handle this gracefully — `bracket_matches` and `follow_ons` will be empty lists
- All team rankings come from pool standings only

## Tests

Comprehensive tests with **inline fixtures** (no live API calls):

### `tests/test_models.py`
- Model construction and field access
- Negative ID handling

### `tests/test_client.py`
- Mock httpx responses
- Test retry behavior
- Test rate limiting
- Test error handling (404, 500, timeout)

### `tests/test_url.py`
- Various AES URL formats
- Edge cases (missing division, query params)

### `tests/test_parsers/test_division.py`
- Round sorting (negative IDs, chronological order)
- Round type detection (pool vs bracket)

### `tests/test_parsers/test_pool.py`
- Match extraction with scores
- Team extraction
- Standings with ranks
- Handling of incomplete/scheduled matches

### `tests/test_parsers/test_bracket.py`
- Bracket match extraction
- Seed information
- Multi-date brackets

### `tests/test_parsers/test_follow_on.py`
- Rank extraction from various text formats
- CompleteShortName parsing
- Edge cases (missing text, malformed)

### Integration Test Support
- `scripts/capture_fixtures.py` — CLI script that fetches real API responses and saves them to `tests/fixtures/`
- Integration tests marked with `@pytest.mark.integration` that use captured fixtures
- Auto-skip if fixture files are missing

## Constraints
- All AES API conventions: negative IDs, round sorting rules
- No HTML parsing, no Playwright — JSON API only
- httpx for HTTP (not requests, not aiohttp)
- Inline test fixtures (dicts in test files), not external JSON files for unit tests
