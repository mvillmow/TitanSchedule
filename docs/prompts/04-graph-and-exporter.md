# Prompt 04: Graph Builder and Team Exporter

Implement the transform layer from scratch per `docs/research.md`. **Greenfield.**

## What to Implement

### `scraper/graph/builder.py` — GraphBuilder

Converts a `Division` model into a sorting network DAG.

**Input:** `Division` object from parsers
**Output:** Internal graph structure (nodes + edges)

#### Node Types
- **Ranking nodes** (phase 0 = start seeds, phase N+1 = end standings)
  - Carry: `team_id`, `team_name`, `seed` (start) or `record`/`rank` (end)
- **Match nodes** (phases 1..N)
  - Carry: `match_id`, `round_name`, `court`, `time`, `date`, `status`, `scores`
  - Up to 3 team slots: home, away, work
- **Port nodes** — connection points for team_flow edges on match nodes, one per team slot (home/away/work). They serve as anchor points so edges connect to specific positions on the match node rather than the node center.
  - Inherit `status` from parent match

#### Edge Type
- **team_flow** — carries `team_id`, `team_name`, `role` (home/away/work)

#### Phase Assignment
- Phase 0: start ranking
- Phases 1..N: match phases, grouped by `(round_index, time_slot)`
  - Within a round, matches at the same time share a phase
  - Tiebreaker: `-match_id` (less-negative = earlier)
- Phase N+1: end ranking

#### Phase Assignment Algorithm (Pseudocode)
```
1. Collect all matches from pools + brackets
2. Group by (round_index, time_slot) → each group = one phase
3. Within group, sort by -match_id (less-negative first)
4. Phase 0 = start ranking nodes (one per team, sorted by seed)
5. Phases 1..N = match phases
6. Phase N+1 = end ranking nodes (computed W-L, rank from standings)
```

#### Tournament Format-Specific Handling

**Pool-play-only**: When no brackets exist, end rankings come from pool standings directly. No follow-on edges. Phase N+1 rankings use pool standing ranks.

**Power league**: Multiple rounds across dates, each round gets its own phase group. Tiered groups (Gold/Silver/Bronze) are tracked via `group_name`.

**Mixed rounds**: Same round can contain both pool (Type 0) and bracket (Type 1) plays (Spring Challenge pattern). Both are included as match phases.

#### End Ranking Computation
- Compute W-L record from finished matches (home/away only, not work)
- Determine final rank from bracket results or pool standings

### `scraper/graph/team_exporter.py` — TeamScheduleExporter

Converts the sorting network DAG into team-centric JSON.

**Input:** Graph from GraphBuilder
**Output:** Dict matching this schema:
```json
{
  "division": "14s Power League",
  "dates": ["2025-03-08", "2025-03-09"],
  "teams": {
    "-12345": {
      "name": "Club Titans 14-1",
      "club": "Club Titans",
      "seed": 3,
      "games": [
        {
          "date": "2025-03-08",
          "time": "08:00",
          "opponent": "Some Other Club 14-2",
          "opponent_id": "-12346",
          "opponent_text": null,
          "court": "Court 3",
          "role": "home",
          "round": "Pool A",
          "group": "Gold A",
          "status": "final",
          "scores": [[25, 18], [25, 21]],
          "won": true
        },
        {
          "date": "2025-03-08",
          "time": "14:00",
          "opponent": null,
          "opponent_id": null,
          "opponent_text": "Winner of M3",
          "court": "Court 1",
          "role": "home",
          "round": "Gold Bracket",
          "group": null,
          "status": "conditional",
          "scores": [],
          "won": null
        }
      ],
      "record": "3-1",
      "rank": 5
    }
  }
}
```

**Game `status` values:**
- `"final"` — played, results available
- `"in_progress"` — currently playing
- `"scheduled"` — teams known, time set, not yet played
- `"conditional"` — future game where opponent depends on other results (`opponent` is null, `opponent_text` describes the source)

**Logic:**
- Walk the DAG phase by phase
- For each match node, determine opponent for each team
- For work team matches: include in games list but `won` is null (not applicable)
- **Conditional games**: When walking the DAG, if a match node's team slot references a follow-on edge that hasn't resolved yet (opponent unknown), emit a conditional game with `opponent=null`, `opponent_id=null`, and `opponent_text` derived from the follow-on source description (e.g., FutureRoundMatches RankText like "1st R1P1" or bracket source text like "Winner of M3")
- Sort games by date, then time
- Compute record from won/lost games (exclude work-team matches and conditional games)
- Extract rank from end ranking nodes

### `scraper/cli.py` — CLI Entry Point

Using `click`:
```
pixi run scrape <URL>
```

- Parse URL to get event_key and division_id
- Fetch all data via client
- Parse with DivisionParser, PoolParser, BracketParser, FollowOnParser
- Build graph with GraphBuilder
- Export with TeamScheduleExporter
- Write JSON to `web/data/{slug}/tournament.json`
- Update `web/data/index.json` with division metadata

**Default Test URLs:**
- Power League 14s: `https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199189/overview`
- Power League 18s-15s: `https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199187/overview`
- Spring Challenge 16 Power: `https://results.advancedeventsystems.com/event/PTAwMDAwNDE3NTY90/divisions/198788/overview`
- Jamboree 16s: `https://results.advancedeventsystems.com/event/PTAwMDAwNDE2NzI90/divisions/198273/overview`

### `web/data/index.json` Format
```json
{
  "divisions": [
    {
      "slug": "14s-power-league",
      "name": "14s Power League",
      "event_key": "12345",
      "division_id": -67890,
      "last_updated": "2025-03-08T12:00:00Z",
      "url": "14s-power-league/tournament.json"
    }
  ]
}
```

## Tests

### `tests/test_graph/test_builder.py`
- Phase assignment from simple division
- Port node creation
- Edge wiring (team flow)
- End ranking W-L computation
- Multi-round tournament (pool → bracket)
- Work team handling

### `tests/test_graph/test_team_exporter.py`
- Basic export from simple graph
- Opponent determination (home sees away, away sees home)
- Work team games (won=null)
- Game sorting by date/time
- Record computation
- Rank extraction
- Multi-day tournament dates list
- Empty/scheduled matches (no scores)
- Conditional games (opponent unresolved, opponent_text populated)
- Conditional games excluded from record computation

### `tests/test_cli.py`
- URL parsing integration
- Mock end-to-end scrape (mock HTTP, verify JSON output)

## Constraints
- Graph is internal only — not exposed to frontend
- Exporter output must match the JSON schema exactly
- Port nodes use `parentId` key (not `parent`) in any serialization
- Match IDs are negative integers throughout
