# Live API Validation Cycle for Scrapers

## Overview

| Aspect | Details |
|--------|---------|
| **Date** | 2026-02-27 |
| **Objective** | Validate a Python scraper against a live REST API after unit tests pass, catch shape mismatches between assumed and real API responses |
| **Outcome** | Found and fixed 4 bugs (FollowOnParser full rewrite, BracketParser full rewrite, bracket overwrite bug, seed_None orphan) that unit tests never caught |
| **Category** | debugging |

## When to Use

Use this skill when:
- You have a scraper built against **assumed** or **partially documented** API shapes
- Unit tests pass against synthetic fixtures but you haven't validated against the **live API**
- You've added new parser logic and need to confirm the real JSON matches your model
- The output graph/data structure has suspicious node counts (e.g., 0 bracket nodes, orphan nodes)

### Trigger Conditions

1. Unit tests all pass but `pixi run scrape <URL>` crashes or produces wrong counts
2. Output JSON has 0 nodes of an expected type
3. Output has orphan nodes (nodes with no edges)
4. Node count is unexpectedly low compared to known tournament structure

---

## Verified Workflow

### Step 1: Capture real fixtures first

```bash
pixi run capture-fixtures "<AES_URL>"
# Saves API responses to tests/fixtures/
```

This lets you inspect the **real** JSON shape before writing any code. Always do this before implementing parsers.

### Step 2: Run unit tests against synthetic fixtures

```bash
pixi run test
```

Unit tests should pass first. They catch logic errors but NOT shape mismatches.

### Step 3: Run full scrape and capture output stats

```bash
pixi run scrape "<AES_URL>"
# Should print: "Exported N nodes, M edges"
```

Then validate the output programmatically:

```python
import json
from collections import Counter

with open('web/data/tournament.json') as f:
    data = json.load(f)

nodes = data['elements']['nodes']
edges = data['elements']['edges']

# Check node type counts against expected structure
node_types = Counter(n['data']['type'] for n in nodes)
print('Node types:', dict(node_types))

# Check for orphan nodes (no outgoing edges)
source_ids = {e['data']['source'] for e in edges}
orphans = [n for n in nodes if n['data']['id'] not in source_ids
           and n['data']['type'] not in ('pool_placement', 'bracket_match')]
print(f'Orphan nodes: {len(orphans)}')
for n in orphans:
    print(f'  {n["data"]["id"]} label={n["data"]["label"]}')

# Check for broken edges (referencing missing nodes)
node_ids = {n['data']['id'] for n in nodes}
broken = [e for e in edges if e['data']['source'] not in node_ids
          or e['data']['target'] not in node_ids]
print(f'Broken edges: {len(broken)}')
```

### Step 4: Diagnose discrepancies

For each suspicious count (e.g., 0 bracket nodes), inspect the fixture:

```python
import json, glob

# Find the relevant fixture
files = glob.glob('tests/fixtures/brackets_*.json')
with open(files[0]) as f:
    data = json.load(f)

# Print the top-level structure
print(type(data), len(data) if isinstance(data, list) else list(data.keys()))
if isinstance(data, list):
    print('First item keys:', list(data[0].keys()))
```

Then compare against what your parser expects. The discrepancy is the bug.

---

## Bugs Found and Fixed in This Session

### Bug 1: FollowOnParser — wrong assumed shape

**Assumed shape** (from plan):
```json
{"MatchId": -55312, "FirstTeamText": "1st R1P1", "SecondTeamText": "2nd R1P2"}
```

**Real shape** (from live API):
```json
{
  "RankText": "1 - Arbuckle 14 KJ (NC) (1)",
  "Match": {"MatchId": -55312, "Court": {...}},
  "Play": {"PlayId": -55121, "CompleteShortName": "..."},
  "WorkTeamAssignmentDecided": true,
  "NextPendingReseed": false
}
```

**Key differences**:
- Each entry = one rank → one bracket match (not one match → two slot texts)
- `Match` and `Play` can both be `null` (future rounds not yet scheduled — must skip)
- Rank extracted from `RankText` leading integer ("1 - TeamName" → rank=1)

**Fix**: Full rewrite. Guard `if not match_obj: continue` at the top.

### Bug 2: BracketParser — wrong tree traversal key

**Assumed**: Tree children stored in `"Children"` key
**Real**: Tree children stored in `"TopSource"` / `"BottomSource"` keys

**Also wrong**:
- `PlayId` is at the bracket list item level (not on root nodes)
- Match name fields are `FullName`/`ShortName` (not `MatchFullName`/`MatchShortName`)
- Team code field is `Code` (not `TeamCode`)

**Fix**: Traverse `TopSource`, `BottomSource`, then fall back to `Children`. Extract `PlayId` from bracket list item and stamp onto each match.

### Bug 3: Bracket assignment overwrite bug (cli.py)

**Symptom**: Only the *last* date's brackets appeared (24 nodes instead of 72).

**Root cause**: The bracket assignment loop ran inside the per-date loop with `=` (overwrite):
```python
for day in playdays:
    if day.get("HasBrackets"):
        bracket_matches = BracketParser(...).parse()
        for rnd in rounds:
            for bracket in rnd.brackets:
                bracket.bracket_matches = [...]  # OVERWRITES on each date!
```

**Fix**: Accumulate all bracket matches into `dict[play_id → list]` across all dates, then assign once:
```python
all_bracket_matches_by_play_id: dict[int, list] = {}
for day in playdays:
    if day.get("HasBrackets"):
        for bm in BracketParser(...).parse():
            all_bracket_matches_by_play_id.setdefault(bm.match.play_id, []).append(bm)

for rnd in rounds:
    for bracket in rnd.brackets:
        bracket.bracket_matches = all_bracket_matches_by_play_id.get(bracket.play_id, [])
```

### Bug 4: seed_None orphan node

**Symptom**: 1 orphan seed node `seed_None` with `label=None`.

**Root cause**: Future pools (not yet scheduled) have placeholder team slots with `TeamId=null` in the API. These were added to `all_teams` as `all_teams[None]`.

**Fix** (two guards):
1. `PoolParser`: `if not t.get("TeamId"): continue` when iterating teams
2. `cli.py`: `if standing.team.team_id is not None:` before inserting into `all_teams`

---

## Key AES API Shape Notes

### FutureRoundMatches (poolsheet endpoint)

```json
[
  {
    "RankText": "1 - Team Name (REGION) (SEED)",
    "Match": {"MatchId": -55312, "Court": {...}, "ScheduledStartDateTime": "..."},
    "WorkMatch": null,
    "Play": {"PlayId": -55121, "CompleteShortName": "LgQFeb1BAll 1s-2sGold A"},
    "WorkTeamAssignmentDecided": true,
    "NextPendingReseed": false
  }
]
```

- `Match` and `Play` can be `null` — skip those entries
- Rank = leading integer in `RankText`
- `source_play_id` comes from the pool being parsed, NOT from `Play.PlayId`

### Bracket list item structure

```json
[
  {
    "PlayId": -55121,
    "FullName": "Gold A",
    "Roots": [
      {
        "Key": 0, "X": 1.0, "Y": 3.0,
        "Reversed": false, "DoubleCapped": false,
        "Match": {"MatchId": ..., "FullName": "...", "ShortName": "...", ...},
        "TopSource": { /* recursive node */ },
        "BottomSource": { /* recursive node */ }
      }
    ]
  }
]
```

- `PlayId` is at the **list item** level — stamp it onto every match in that bracket
- Tree is `TopSource`/`BottomSource`, NOT `Children`
- Match name fields: `FullName` / `ShortName` (not `MatchFullName`/`MatchShortName`)
- Team code field: `Code` (not `TeamCode`)

### Future pools (not yet scheduled)

Pools for future league days (e.g., Mar 14, Apr 4) appear in `plays.json` and their poolsheets are fetchable, but:
- `Teams` array may contain entries with `TeamId: null` — skip them
- `Matches` array is empty — create a placeholder node instead of skipping the pool

---

## Validation Checklist

After every scrape, verify:

| Check | Expected |
|-------|----------|
| `bracket_match` count | Matches sum of all brackets × matches per bracket |
| `pool_match` count | Matches sum of all pool matches across all days |
| `pool_placement` count | Sum of (teams per pool) across all pools |
| `seed` count | = total teams in division |
| Orphan seeds | 0 |
| Broken edges | 0 |
| Follow-on edges | = number of pool placements that feed into brackets |
