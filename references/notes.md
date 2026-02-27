# TitanSchedule — Session Notes (2026-02-27)

## Session Summary

Two major skill areas were captured from the TitanSchedule implementation session:

1. **Live API Validation Cycle** (`skills/live-api-validation-cycle/SKILL.md`)
2. **Fixed-Height DAG Timeline Layout** (`skills/fixed-height-dag-timeline/SKILL.md`)

---

## Raw Notes: Live API Validation Session

### What triggered the need

Unit tests passed (115/115) but `pixi run scrape <URL>` produced wrong counts:
- Expected: ~72 bracket_match nodes across two tournament dates
- Got: 24 bracket_match nodes (only Feb 22 XO)
- Expected: 0 orphan nodes
- Got: 1 orphan — `seed_None` with `label=None`

### Debugging sequence

1. Inspected `tests/fixtures/brackets_2026-02-01.json` — confirmed file exists and has data
2. Traced code path: `cli.py` per-date loop used `bracket.bracket_matches = [...]` (overwrite)
3. Feb 1 and Feb 22 both processed; Feb 22 overwrote Feb 1 results with empty lists
4. Fix: accumulate `dict[play_id → list]` across all dates, assign once after loop

For `seed_None`:
1. Inspected `tests/fixtures/poolsheet_-XXXXX.json` for Apr 4 future pool
2. Found teams array contained `{"TeamId": null, "TeamName": null, ...}` placeholders
3. These were added to `all_teams` dict as `all_teams[None]` → created `seed_None` node
4. Fix: skip in `pool.py` (`if not t.get("TeamId"): continue`) and guard in `cli.py`

### Bugs found and fixed

| Bug | Root Cause | Fix Location |
|-----|-----------|--------------|
| 24 bracket_match nodes instead of 72 | `=` overwrite in per-date bracket loop | `cli.py` |
| `seed_None` orphan node | `TeamId: null` from future pool added to `all_teams[None]` | `pool.py` + `cli.py` |
| `node.popperRef is not a function` | `cytoscape-popper` extension not loaded | `tooltips.js` (full rewrite) |
| Future pools invisible | Pools with teams but no matches had no graph nodes | `builder.py` (pending nodes) |

---

## Raw Notes: Fixed-Height Timeline Layout Session

### What the user wanted

> "I want the graph to be more constrained. I want the height of the graph to be constant. After each day, there is a known ordering, and I want this ordering to be specified. The graph should be more wide, so in timeline style."
> "I also want to be able to limit display to individual days and also to teams and re-render with that information"

### Key design decisions

1. **Phase = X column integer** — each "round type" (seed, pool, placement, bracket) gets its own X column. Increments with `_current_phase` counter in GraphBuilder.

2. **GlobalRow = Y row float** — average of the 0-based seed index of all teams in a node. For a match between seed 1 and seed 4, globalRow = (0 + 3) / 2 = 1.5. For placement nodes, it's the team's own row.

3. **Preset layout** — Cytoscape `preset` layout places nodes at `(phase × PHASE_WIDTH, globalRow × ROW_HEIGHT)`. No dagre. Deterministic, instant, no re-layout needed.

4. **Canvas sizing from data** — `app.js` computes canvas size from `nTeams` and `nPhases` from metadata, sets `#cy` div dimensions explicitly. `#cy-wrap` is scrollable.

5. **Day filter by phase index** — `metadata.phases` array in JSON maps each phase integer to a label and date. Day buttons toggle phase indices into `_activeDays` Set. `_applyFilters` shows/hides nodes by phase.

### What was removed

- dagre + cytoscape-dagre CDN scripts (not needed with preset layout)
- Tippy.js + Popper.js CDN scripts (replaced with DOM-based tooltip)
- `cytoscape-dagre` layout option from `graph.js`

### Files changed

| File | Change |
|------|--------|
| `scraper/graph/builder.py` | Added `phase`, `global_row` fields; `_current_phase` counter; `_build_team_row_map()`; pending pool nodes |
| `scraper/graph/exporter.py` | Added `phase`/`globalRow` to node JSON; `phases` array in metadata |
| `web/js/graph.js` | Full rewrite: preset layout, computePositions(), straight/taxi/bezier edges |
| `web/js/controls.js` | Full rewrite: `_initDayFilter()`, `_applyFilters()` combined |
| `web/js/tooltips.js` | Full rewrite: DOM-based, no Tippy/Popper |
| `web/js/app.js` | Canvas sizing from metadata |
| `web/index.html` | Day-filter row, removed CDN scripts, scrollable cy-wrap |
| `web/css/styles.css` | cy-wrap, cy, day-filter styles |
| `tests/test_exporter.py` | `make_node()` + `phase=0, global_row=0.0` |
| `tests/test_pruner.py` | `make_node()` + `phase=0, global_row=0.0` |

### Final output stats (live scrape)

- 444 nodes, 864 edges
- 60 pending pool nodes (unscheduled Mar 14, Apr 4)
- 48 scheduled placement nodes (for unscheduled pools)
- 72 bracket_match nodes (48 Feb 1 + 24 Feb 22 XO)
- 0 orphan nodes
- 0 broken edges

---

## AES API Gotchas (persistent)

- **IDs are negative integers** — PlayId, MatchId, RoundId, CourtId are all negative
- **Less-negative = earlier round** — sort `reverse=True` on RoundId to get chronological order
- **Future pools** — `Teams` may have `TeamId: null` placeholders; `Matches` is empty
- **FutureRoundMatches** — `Match` and `Play` can be `null` for unscheduled future rounds (skip them)
- **Bracket tree** — children are `TopSource`/`BottomSource`, NOT `Children`
- **Bracket PlayId** — at the list-item level, not on individual match nodes
- **pixi** — project uses pixi (not pip/venv): `pixi run test`, `pixi run scrape <URL>`
