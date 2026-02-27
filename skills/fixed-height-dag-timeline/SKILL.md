# Fixed-Height DAG Timeline Layout for Tournament Sorting Networks

## Overview

| Aspect | Details |
|--------|---------|
| **Date** | 2026-02-27 |
| **Objective** | Replace unconstrained auto-layout (dagre) with a fixed-height timeline layout where Y = team rank row (constant) and X = timeline phase column |
| **Outcome** | Graph renders as a sorting network: N rows (one per team), scrollable-width timeline with pool/bracket columns; day filter and team filter operate without re-layout |
| **Category** | architecture |

## When to Use

Use this skill when:
- You have a tournament/bracket DAG that degenerates to spaghetti with auto-layout
- The graph has a natural fixed Y axis (team seed/rank) that should be constant throughout
- You want a horizontal timeline with discrete phase columns (pool day 1, placements, brackets, etc.)
- You need day filter and team trajectory filter without triggering expensive re-layout
- Node count is large (400+) and dagre layout is slow or visually confusing

### Trigger Conditions

1. Users complain the graph is "too tall" or "hard to follow a team"
2. Auto-layout produces crossing edges that don't reflect the actual game structure
3. Day filtering with dagre causes jarring re-layout animation
4. You need vertical ordering to reflect seeding/ranking (not just connectivity)

---

## Architecture: The Phase/GlobalRow Coordinate System

### Core Insight

A tournament is a **sorting network** — each pool match is a comparator that takes two teams and produces a winner/loser. The Y axis should be fixed to team seed rank; the X axis is the timeline.

```
Seed 1 ──────────────────────────────────────────────────────
         Pool M1   1st P1   Gold M1   1st Gold   ...
Seed 2 ──────────────────────────────────────────────────────
         Pool M1            Gold M1
Seed 3 ──────────────────────────────────────────────────────
         Pool M2   1st P2   Gold M2
...
```

Match nodes sit at the **average row** of their two participants. Placement nodes sit at the **team's actual row** (or estimated row for future rounds).

### Two Coordinate Fields

Every graph node carries:

```python
@dataclass
class GraphNode:
    phase: int       # X column index: 0=seeds, 1=pool matches, 2=placements, 3=brackets, ...
    global_row: float  # Y row: average 0-based seed index of this node's teams
```

### Phase Assignment (Backend)

```python
class GraphBuilder:
    def __init__(self, division):
        self._current_phase = 0  # increments as we process each round
        self._team_row_map = self._build_team_row_map()  # team_id → seed index (0-based)

    def _build_team_row_map(self) -> dict[int, int]:
        teams_sorted = sorted(self._division.all_teams, key=lambda t: t.seed or 999)
        return {t.team_id: i for i, t in enumerate(teams_sorted)}

    def _global_row(self, teams_list: list[dict]) -> float:
        rows = [self._team_row_map.get(t["id"], 0) for t in teams_list if t.get("id")]
        return sum(rows) / len(rows) if rows else 0.0

    def _build_seed_nodes(self):
        # phase=0, global_row=seed index

    def _build_pool_match_nodes(self, rnd):
        self._current_phase += 1   # phase 1 for first pool round
        # each node: phase=self._current_phase, global_row=avg of its teams' rows

    def _build_pool_placement_nodes(self, rnd):
        self._current_phase += 1   # phase 2 for placements after pool round
        # each node: phase=self._current_phase, global_row=team's own row

    def _build_bracket_match_nodes(self, rnd):
        self._current_phase += 1   # phase 3 for first bracket round
        # each node: phase=self._current_phase, global_row=avg of its teams' rows
```

### Phase Metadata Export

The exporter produces a `phases` array in `metadata` so the frontend knows what each column means:

```python
def _build_phase_index(self, nodes_data: list[dict]) -> list[dict]:
    """Build phase descriptors from node data."""
    phase_info = {}
    for n in nodes_data:
        p = n["data"]["phase"]
        if p not in phase_info:
            phase_info[p] = {
                "phase": p, "label": "", "date": None, "type": None
            }
        # Infer type from node type; extract date from scheduled_start
        node_type = n["data"]["type"]
        if node_type == "pool_match":
            phase_info[p]["type"] = "pool"
        elif node_type == "bracket_match":
            phase_info[p]["type"] = "bracket"
        # ... etc.
    return sorted(phase_info.values(), key=lambda x: x["phase"])
```

---

## Verified Frontend Implementation

### Layout Constants

```javascript
const ROW_HEIGHT  = 22;   // px between team rows (vertical density)
const PHASE_WIDTH = 260;  // px between phase columns (horizontal spacing)
const NODE_W      = 70;   // node width in px
const NODE_H      = 18;   // node height in px
```

### Preset Layout (replaces dagre entirely)

```javascript
function computePositions(elements) {
  const positions = {};
  elements.nodes.forEach(n => {
    positions[n.data.id] = {
      x: n.data.phase    * PHASE_WIDTH,
      y: n.data.globalRow * ROW_HEIGHT,
    };
  });
  return positions;
}

function initGraph(jsonData) {
  const positions = computePositions(jsonData.elements);
  cy = cytoscape({
    container: document.getElementById('cy'),
    elements: jsonData.elements,
    layout: {
      name: 'preset',
      positions: node => positions[node.id()] || { x: 0, y: 0 },
      fit: true,
      padding: 40,
    },
    style: [ ... ],
    userZoomingEnabled: true,
    userPanningEnabled: true,
    boxSelectionEnabled: false,
  });
  return cy;
}
```

**Key**: Remove dagre and cytoscape-dagre from CDN scripts — they are no longer needed.

### Canvas Sizing (app.js)

```javascript
const nTeams  = (metadata.teams  || []).length || 48;
const nPhases = (metadata.phases || []).length || 9;
const graphH  = nTeams  * ROW_HEIGHT + 80;
const graphW  = (nPhases + 1) * PHASE_WIDTH + 80;
cyEl.style.width   = graphW + 'px';
cyEl.style.height  = graphH + 'px';
cyEl.style.minWidth = '100%';  // fill viewport if graph is narrower
```

### Scrollable Container (HTML + CSS)

```html
<div id="cy-wrap" class="flex-1 overflow-auto bg-gray-50">
  <div id="cy"></div>   <!-- sized by app.js from data -->
</div>
```

```css
#cy-wrap {
  background: #f8fafc;
  cursor: grab;
  overflow: auto;  /* horizontal AND vertical scrolling */
}
#cy {
  background: #f8fafc;
  display: block;
  /* width/height set by app.js */
}
```

---

## Day Filter Architecture

### Phase Types

Only pool and bracket phases are day-selectable. Seeds and placement columns are always visible or shown contextually.

```javascript
// metadata.phases from JSON:
// [{phase: 1, type: "pool", date: "2026-01-31", label: "Jan 31 Pools"},
//  {phase: 2, type: "placement", ...},
//  {phase: 3, type: "bracket", date: "2026-02-01", label: "Feb 1 Brackets"},
//  ...]

_allDayPhases = phases.filter(p => p.type === 'pool' || p.type === 'bracket');
```

### Visibility Logic

When a day (pool or bracket phase) is selected, also show its adjacent columns:

```javascript
function _applyFilters(cy) {
  const showAllDays = _activeDays.size === 0;
  cy.batch(() => {
    cy.elements().style('display', 'element');  // reset all

    if (!showAllDays) {
      const visiblePhases = new Set([0]);  // seeds always visible

      _activeDays.forEach(phase => {
        visiblePhases.add(phase);      // the selected game phase
        visiblePhases.add(phase - 1);  // preceding placement/seed column
        visiblePhases.add(phase + 1);  // following placement column
      });

      cy.nodes().forEach(n => {
        if (!visiblePhases.has(n.data('phase'))) n.style('display', 'none');
      });
      cy.edges().forEach(e => {
        const src = e.source(), tgt = e.target();
        if (src.style('display') === 'none' || tgt.style('display') === 'none')
          e.style('display', 'none');
      });
    }

    if (_activeTeamId) _applyTeamHighlight(cy, _activeTeamId);
  });
}
```

### Day Filter Buttons

```javascript
_allDayPhases.forEach(p => {
  const btn = document.createElement('button');
  btn.className = 'day-filter';
  btn.textContent = _dayLabel(p);  // "Jan 31 Pools", "Feb 1 Brackets"
  btn.dataset.phase = p.phase;
  btn.addEventListener('click', () => {
    if (_activeDays.has(p.phase)) {
      _activeDays.delete(p.phase);
      btn.classList.remove('active');
    } else {
      _activeDays.add(p.phase);
      btn.classList.add('active');
    }
    const allSelected = _activeDays.size === 0;
    allBtn.classList.toggle('active', allSelected);
    _applyFilters(cy);
  });
});
```

---

## Edge Style for Timeline Layout

With preset layout and straight-line edges, use `curve-style: 'straight'` for same-row connections and `bezier` for cross-row connections:

```javascript
// Pool sequence edges (same team, consecutive matches): straight
{ selector: 'edge[type="pool_sequence"]',
  style: { 'curve-style': 'straight', 'line-color': '#94a3b8', width: 1 }},

// Seed to pool: taxi (right-angle) to reduce crossing
{ selector: 'edge[type="seed_to_pool"]',
  style: { 'curve-style': 'taxi', 'line-color': '#94a3b8', opacity: 0.4 }},

// Follow-on (pool placement → bracket): bezier for spanning long distances
{ selector: 'edge[type="pool_to_bracket"]',
  style: { 'curve-style': 'bezier', 'line-color': '#8b5cf6', width: 2 }},
```

---

## Future Pools (Unscheduled Rounds)

Pools with teams assigned but no matches yet (future tournament days) need placeholder nodes to enable trajectory BFS traversal:

```python
# builder.py
if pool.matches:
    # Normal case: create one node per match
    ...
elif pool.teams:
    # Unscheduled pool: create one pending node for all teams
    node_id = f"pool_pending_{pool.play_id}"
    all_teams = [{"id": s.team.team_id, "name": s.team.name} for s in pool.teams]
    self._add_node(GraphNode(
        id=node_id, node_type="pool_match", label=pool.short_name,
        sublabel=f"{pool.complete_short_name} (TBD)", status="scheduled",
        teams=all_teams, phase=phase,
        global_row=self._global_row(all_teams), ...
    ))
```

Then in `_connect_seeds_to_first_pool_matches`, check for pending nodes:

```python
pending_id = f"pool_pending_{pool.play_id}"
if pending_id in self._node_ids:
    for standing in pool.teams:
        if standing.team.team_id is None:
            continue
        seed_id = f"seed_{standing.team.team_id}"
        if seed_id in self._node_ids:
            self._add_edge(GraphEdge(
                id=f"seed_{standing.team.team_id}_to_{pending_id}",
                source=seed_id, target=pending_id,
                edge_type="seed_to_pool", ...
            ))
```

---

## Validation Checklist

After implementing the timeline layout:

| Check | How to Verify |
|-------|--------------|
| All nodes positioned (no (0,0) cluster) | Inspect cy.nodes() positions in browser console |
| Seeds at x=0, leftmost column | `cy.nodes('[type="seed"]').map(n => n.position().x)` all ≈ 0 |
| Pool matches at consistent x | All pool_match nodes for same round have same x |
| Match nodes between their teams' y-rows | y of match ≈ average of its teams' seed rows × ROW_HEIGHT |
| Canvas tall enough | No nodes clipped at bottom |
| Canvas wide enough | No nodes clipped at right; horizontal scroll works |
| Day filter shows/hides correct phases | Toggle "Jan 31 Pools" → only that phase + ±1 visible |
| Team filter works on filtered view | Select team after day filter → trajectory within visible phase |
| No dagre CDN loaded | Network tab shows no dagre-related requests |

---

## Failed Approaches

### Failed: dagre auto-layout
- **What**: Used cytoscape-dagre with `rankDir: 'LR'` for horizontal flow
- **Why it failed**:
  - Large node count (400+) caused slow layout and visual spaghetti
  - Y axis varied between renders (no stable team ordering)
  - Day filter required re-layout, causing jarring animation
  - Could not enforce "seeds at top stay at top" invariant

### Failed: Layer-based Y with dagre hints
- **What**: Tried using dagre's `order` hints to enforce consistent Y positions
- **Why it failed**: dagre does not expose direct Y-position control; `rankerConfig` is not reliable cross-version

### Failed: Tippy.js tooltips
- **What**: Used Tippy.js + Popper.js + `cytoscape-popper` extension for rich tooltips
- **Why it failed**: `cytoscape-popper` adds `.popperRef()` method to Cytoscape node objects; without loading it, calling `.popperRef()` throws. The extension was not listed in CDN but was assumed to be bundled.
- **Fix**: Replaced with plain `div#cy-tooltip` following mouse cursor via `mousemove` event. Use `document.createElement`/`textContent` instead of `innerHTML` for security.

### Failed: Fixed dagre CDN with cytoscape-popper extension
- **What**: Tried adding cytoscape-popper via CDN
- **Why it failed**: The CDN URL for `cytoscape-popper` requires a specific version that conflicts with Tippy v6 API
- **Fix**: Abandon Tippy entirely; DOM-based tooltips have zero dependencies and are simpler

---

## Key Pitfalls

1. **Remove dagre CDN scripts** when switching to preset layout — they add unnecessary load and can conflict
2. **Canvas must be sized BEFORE Cytoscape init** — set `#cy` width/height in px before calling `cytoscape({...})`, otherwise the canvas is 0×0
3. **`cy.fit()` in preset layout** — call `cy.fit(40)` after init to show the full graph; preset layout with `fit: true` may not honor padding correctly on first render
4. **globalRow for multi-team nodes** — use average of team rows (float), not integer. This places match nodes visually between their two participants
5. **Day filter uses phase index, not date strings** — store `phase` integer on both nodes and in `metadata.phases`; never filter by date string comparison
