# Skill: fullstack-python-spa-plan-impl

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-26 |
| Project | TitanSchedule |
| Objective | Implement a 6-phase plan: async Python REST scraper → domain models → parsers → DAG builder → Cytoscape.js SPA → shell scripts |
| Outcome | ✅ 115/115 tests pass. Full pipeline: URL → API → parsed models → DAG JSON → interactive web viz |
| Test runtime | ~26s (dominated by respx async mock overhead) |
| Lines of code | ~3,000 (Python) + ~800 (JS) |

---

## When to Use

Trigger this skill when:
- Implementing a pre-approved multi-phase architectural plan covering both backend and frontend
- The plan involves: REST API client → domain models → parser layer → graph/DAG construction → JSON export → SPA rendering
- TDD is required with no live network access during test runs
- The frontend must use zero build tooling (CDN-only)
- The codebase starts from scratch (only docs exist)

---

## Verified Workflow

### Phase order that worked cleanly

```
1. Scaffolding (requirements.txt, pyproject.toml, .gitignore, directories)
2. Config + URL parser (pure functions, easiest to TDD first)
3. API client (async httpx + retry logic, mocked with respx)
4. Data models (dataclasses — define vocabulary before parsers)
5. Parsers (one per API response type, all tested against inline fixture dicts)
6. DAG builder + pruner + exporter
7. CLI orchestration (imports all layers, wires them together)
8. Frontend SPA (pure JS files, CDN dependencies only)
9. Shell scripts (chmod +x required)
```

### TDD pattern that worked: inline fixtures in test files

Instead of loading JSON files from disk, embed fixture dicts directly in the test file as module-level constants. This avoids file I/O, makes tests self-contained, and keeps them runnable before `--capture-fixtures` is ever called.

```python
# In test_pool_parser.py — no file I/O needed
POOLSHEET_DATA = {
    "Pool": {"PlayId": -51151, "FullName": "Pool 1", ...},
    "Matches": [...],
    "FutureRoundMatches": [],
}

class TestPoolParser:
    def test_parses_team_standings(self):
        pool = PoolParser(POOLSHEET_DATA, "KEY", 193839).parse()
        assert pool.teams[0].team.name == "GRV 12 Black"
```

### respx mocking pattern for async httpx

```python
import respx, httpx
from scraper.client import AESClient, AESClientError
from scraper.config import AES_API_BASE

class TestAESClient:
    @respx.mock
    async def test_retry_on_500(self):
        route = respx.get(f"{AES_API_BASE}/event/KEY")
        route.side_effect = [
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, json={"Key": "KEY"}),
        ]
        async with AESClient() as client:
            result = await client.get_event("KEY")
        assert route.call_count == 3
```

`pytest-asyncio` with `asyncio_mode = "auto"` in `pyproject.toml` eliminates the need for `@pytest.mark.asyncio` on every test.

### DAG builder pattern that enforces no-cycles

Use Kahn's topological sort algorithm in the test to verify the DAG invariant:

```python
def test_no_cycles(self):
    nodes, edges = GraphBuilder(div).build()
    adj = {n.id: [] for n in nodes}
    for e in edges:
        if e.source in adj and e.target in adj:
            adj[e.source].append(e.target)
    in_degree = {n.id: 0 for n in nodes}
    for src, targets in adj.items():
        for t in targets:
            in_degree[t] += 1
    queue = [n for n in in_degree if in_degree[n] == 0]
    visited = 0
    while queue:
        node = queue.pop(0)
        visited += 1
        for neighbor in adj.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    assert visited == len(nodes)
```

### Cytoscape.js + Dagre CDN setup (no bundler)

```html
<!-- Order matters: dagre before cytoscape-dagre -->
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.28.1/cytoscape.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/dagre/0.8.5/dagre.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.min.js"></script>
```

Left-to-right tournament layout:
```javascript
layout: {
    name: 'dagre',
    rankDir: 'LR',
    nodeSep: 40,
    rankSep: 120,
    ranker: 'longest-path',
    padding: 30,
}
```

### Parallel file creation strategy

Create all files in a phase before running tests. Use parallel Write tool calls for independent files (e.g., all 4 parser files simultaneously), then run pytest once for the batch. This is faster than write-test-fix one file at a time.

---

## Failed Attempts / Bugs Caught During TDD

### 1. AES negative ID sort order (discovered by `test_round_grouping`)

**Problem**: `sorted(rounds_by_id.values(), key=lambda r: r.round_id)` — ascending sort puts `-52479` before `-50094` because `-52479 < -50094`. But in AES, the pool round (id `-50094`) was created first and should appear first.

**Fix**: `sorted(..., reverse=True)` — for AES negative IDs, less-negative = earlier round = should come first, so sort descending.

```python
# Wrong:
return sorted(rounds_by_id.values(), key=lambda r: r.round_id)

# Correct:
return sorted(rounds_by_id.values(), key=lambda r: r.round_id, reverse=True)
```

**Lesson**: When working with AES data, negative IDs encode creation order inversely — always verify sort direction against real data shapes.

### 2. Falsy empty list in default parameter pattern (discovered by `test_empty_future_matches`)

**Problem**: Helper method `_parser(self, future_matches=None, ...)` used `future_matches or FUTURE_MATCHES` inside the body. When called as `_parser([])`, the empty list is falsy, so `[] or FUTURE_MATCHES` evaluates to `FUTURE_MATCHES`.

**Fix**: Use explicit `None` check:

```python
# Wrong:
FollowOnParser(future_matches or FUTURE_MATCHES, ...)

# Correct:
FollowOnParser(FUTURE_MATCHES if future_matches is None else future_matches, ...)
```

**Lesson**: Never use `x or default` for values that can legitimately be empty collections. Always use `x if x is None else default`.

### 3. Seed-to-pool edge deduplication needed

**Problem**: `_connect_seeds_to_first_pool_matches` iterates all matches and adds seed→match edges. A team in multiple matches would generate duplicate edges from the same seed node.

**Fix**: Check for duplicate edge IDs before adding:
```python
edge_id = f"seed_{team_id}_to_{match_id}"
if not any(e.id == edge_id for e in self._edges):
    self._add_edge(...)
```

**Lesson**: When building graph edges from denormalized data, always guard against duplicates.

---

## Results & Parameters

### pyproject.toml (pytest config)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### requirements.txt
```
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
respx>=0.21.0
```

### AES API facts
- Base URL: `https://results.advancedeventsystems.com/api`
- Required header: `Accept: application/json`
- No authentication
- All IDs are negative integers (PlayId, MatchId, CourtId, RoundId, etc.)
- `FutureRoundMatches` text format: `"1st R1P1"` where `R1P1` = `CompleteShortName`
- Pool play = `Type: 0`, Bracket play = `Type: 1`

### Node type → Cytoscape shape mapping
```
seed          → round-tag
pool_match    → roundrectangle
bracket_match → diamond
pool_placement → ellipse
classification → star
```

### Status → color mapping
```
scheduled   → #94a3b8 (gray)
in_progress → #3b82f6 (blue)
finished    → #f1f5f9 (light gray)
pool_placement → #ddd6fe (purple)
```

### Graph layer numbering
```
Layer 0: seed nodes
Layer 1: pool match nodes
Layer 2: pool placement nodes
Layer 3: bracket match nodes
Layer 4: classification nodes (terminal)
```

### Integration test skip pattern
```python
@pytest.mark.skipif(
    not _has_fixture("plays.json"),
    reason="Fixture files not captured. Run: python -m scraper.cli --capture-fixtures <URL>",
)
class TestWithFixtures: ...
```

---

## File Structure Produced

```
scraper/
├── __init__.py
├── url.py          # URL parser (regex)
├── config.py       # Constants
├── client.py       # AESClient (async httpx + retry)
├── models.py       # All dataclasses
├── cli.py          # CLI + orchestration
├── parsers/
│   ├── base.py     # Abstract BaseParser
│   ├── division.py # DivisionParser
│   ├── pool.py     # PoolParser
│   ├── bracket.py  # BracketParser
│   └── followon.py # FollowOnParser
└── graph/
    ├── builder.py  # GraphBuilder (DAG)
    ├── pruner.py   # PathPruner
    └── exporter.py # CytoscapeExporter

web/
├── index.html      # CDN-only SPA shell
├── css/styles.css
└── js/
    ├── app.js       # Entry point
    ├── graph.js     # Cytoscape init + styles
    ├── trajectory.js # BFS team highlighting
    ├── controls.js  # UI controls
    ├── tooltips.js  # Tippy.js tooltips
    └── export.js    # PNG/SVG/PDF export

tests/
├── conftest.py
├── fixtures/        # Populated by --capture-fixtures
├── test_url.py
├── test_client.py
├── test_models.py
├── test_division_parser.py
├── test_pool_parser.py
├── test_bracket_parser.py
├── test_followon_parser.py
├── test_graph_builder.py
├── test_pruner.py
├── test_exporter.py
└── test_integration.py  # Skips if no fixtures
```
