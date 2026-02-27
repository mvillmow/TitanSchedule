# TitanSchedule Architecture Design Document

## 1. Problem Statement

AES (Advanced Event Systems) hosts volleyball tournaments where schedules, pool play results,
bracket matchups, and final standings are scattered across dozens of web pages. A parent or
coach attending a two-day tournament must click through multiple AES pages to answer simple
questions: "When does my kid play next?", "What court?", "What's their record?"

**TitanSchedule** solves this by scraping the AES public REST API, building an internal
sorting-network model of the tournament, then exporting a compact per-team schedule view.
The result is a static website showing day tabs with team cards — one glance tells you
everything about your team's tournament day.

### Goals
- One compact view per day per team: time, court, opponent, role, result
- Automatic updates via GitHub Actions cron
- Zero-friction access: static site on GitHub Pages, works on phones
- No AES account or authentication required

### Non-Goals
- Real-time live scoring (AES updates are delayed anyway)
- Full bracket visualization (the old Cytoscape approach — dropped for UX simplicity)
- Supporting non-AES tournament platforms

---

## 2. Architecture Overview

Three-layer pipeline:

```
Data Layer              Transform Layer           Presentation Layer
─────────────          ───────────────           ──────────────────
AES REST API  ──→  Python Scraper  ──→  Sorting Network DAG  ──→  Team JSON  ──→  Static HTML
(httpx)            (parsers)            (GraphBuilder)            (Exporter)       (Tailwind)
```

- **Data Layer**: Python async HTTP client hitting AES public JSON endpoints
- **Transform Layer**: Parsers → internal DAG model → team-centric JSON export
- **Presentation Layer**: Static HTML/JS/CSS reading exported JSON, CDN-only

All orchestrated by **pixi** for environment management and task running.

---

## 3. Data Layer — AES REST API

### API Basics
- Base URL: `https://results.advancedeventsystems.com/api`
- Auth: None. Just set `Accept: application/json` header.
- No Playwright, no Selenium, no HTML scraping — pure REST JSON.

### Key Endpoints

| Endpoint | Returns |
|----------|---------|
| `/event/{key}` | Tournament metadata (name, dates, divisions) |
| `/event/{key}/division/{id}/plays` | Rounds within a division (pools, brackets) |
| `/event/{key}/poolsheet/{playId}` | Pool play matches and standings |
| `/event/{key}/division/{id}/brackets/{date}` | Bracket matches for a date |

### AES ID Conventions
- **EventId and DivisionId are positive integers**
- **RoundId, GroupId, PlayId, CourtId, MatchId are negative integers** (e.g., PlayId: -51151, MatchId: -51190)
- **Round ordering**: Less negative = earlier round. Sort `reverse=True` for chronological order.
- **Match timeline**: Use `-match_id` as tiebreaker so less-negative sorts first.

### Additional API Fields
- `GroupId` / `GroupName` — tier sub-divisions within a round (e.g., "Gold A", "Silver B")
- `Type` — round type: 0 = pool, 1 = bracket/crossover
- `Order` — sort order field on plays (controls display ordering)
- `Courts` — array of court objects; each may include a `VideoLink`
- `IsFinished` — boolean on divisions indicating completion
- `ColorHex` / `CodeAlias` — division color and short code for display
- `CompleteShortName` — concatenated round + group + short name (e.g., "R1P1")

### Rate Limiting
- Polite delays between requests (0.5s default)
- Retry with exponential backoff on 429/5xx
- Concurrent requests capped per host

### Parser Architecture

Four parsers, each handling one AES data shape:

- **DivisionParser**: Extracts rounds from `/division/{id}/plays`. Sorts by round_id descending.
- **PoolParser**: Extracts matches, teams, standings from `/poolsheet/{playId}`.
- **BracketParser**: Extracts bracket matches from `/division/{id}/brackets/{date}`.
- **FollowOnParser**: Parses advancement text (e.g., "1st R1P1") linking pool results to bracket seeds. Uses regex `^(\d+)` to extract rank from RankText.

### Test URLs

- **Power League 14s**: `https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199189/overview`
- **Power League 18s-15s**: `https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199187/overview`
- **Spring Challenge 16 Power**: `https://results.advancedeventsystems.com/event/PTAwMDAwNDE3NTY90/divisions/198788/overview`
- **Jamboree 16s**: `https://results.advancedeventsystems.com/event/PTAwMDAwNDE2NzI90/divisions/198273/overview`

---

## 3.5 Tournament Format Variants

Three distinct tournament formats exist in AES:

### Power League
- 4–6 league dates spread across a season, with tiered groups (Gold, Silver, Bronze)
- Teams are re-seeded between rounds based on cumulative results
- Groups have sub-divisions like "Gold A", "Gold B"
- Example: event `PTAwMDAwNDE4Mjk90`, divisions 199189 (14s), 199187 (18s-15s)

### Single-Weekend Tournament
- Day 1: pool play to establish seeding
- Day 2: mixed brackets and pools organized by tier (Gold bracket, Silver bracket, etc.)
- Follow-on edges link pool standings to bracket seeds
- Example: event `PTAwMDAwNDE3NTY90`, division 198788

### Pool-Play-Only
- Just pools, no brackets, no follow-on edges
- Final standings come directly from pool records
- Example: event `PTAwMDAwNDE2NzI90`, division 198273

---

## 3.6 Error Handling — Partial and Unexpected Data

AES may return partial or unexpected data. The scraper handles these cases:

- **Empty pools**: A play endpoint returns a pool with zero matches. The parser skips it and logs a warning; no nodes are created for empty pools.
- **Missing teams**: A match may reference a team ID that doesn't appear in any pool or bracket roster. The parser uses whatever fields are available and marks unknown teams with placeholder names.
- **Unexpected structure**: If a required field is missing from the API response (e.g., no `Matches` array in a poolsheet), the parser raises a clear error with the endpoint URL for debugging.
- **Partial results**: Some matches may be finished while others in the same round are still scheduled. The exporter handles mixed-status rounds correctly — each match carries its own status independently.
- **Network errors**: The client retries on 429/5xx with exponential backoff. Persistent failures raise an exception with the failing endpoint, allowing partial scrapes of other divisions to complete.

---

## 4. Internal Model — Sorting Network DAG

The tournament is modeled as a **sorting network**: teams are "wires" flowing left to right
through "comparator" nodes (matches). This is the canonical internal representation.

### Why a Sorting Network?
A tournament *is* a sorting network. Teams enter with initial seeds, flow through matches
(comparators), and exit with final rankings. Pool play and bracket play are both just
different arrangements of comparators. This model:
- Unifies pool and bracket play into one structure
- Makes team flow through the tournament explicit
- Correctly handles follow-on edges (pool rank → bracket seed)
- Enables future visualizations if desired

### Node Types
- **Ranking nodes**: Start column (seeds) and end column (final standings with W-L records)
- **Match nodes**: Unified for both pool and bracket play. Carry home/away/work team roles.

### Edge Type
- **team_flow**: Carries `team_id`, `team_name`, `role` (home/away/work)

### Phases
- Phase 0 = start ranking (initial seeds)
- Phases 1..N = match phases grouped by (round_index, time_slot)
- Phase N+1 = end ranking (final standings with computed W-L records)

### Port Nodes
Match nodes have port sub-nodes for incoming/outgoing team connections.
Port nodes inherit `status` from their parent match node.

### Pool-Play-Only Divisions
For divisions with no brackets (pool-play-only format), there are no follow-on edges.
Phase N+1 rankings come directly from pool standings rather than bracket results.

---

## 5. Transform/Export Layer

### TeamScheduleExporter

Converts the sorting network DAG into a flat, team-centric JSON structure optimized for
the frontend. This is the bridge between the graph model and the presentation layer.

**Output format:**
```json
{
  "division": "14s Power League",
  "dates": ["2025-03-08", "2025-03-09"],
  "teams": {
    "12345": {
      "name": "Club Titans 14-1",
      "club": "Club Titans",
      "seed": 3,
      "games": [
        {
          "date": "2025-03-08",
          "time": "08:00",
          "opponent": "Some Other Club 14-2",
          "opponent_id": "12346",
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
- `"conditional"` — future game where opponent depends on other results (`opponent` is null, `opponent_text` describes the source like "Winner of M3" or "1st Pool A")

### CLI Pipeline
```
pixi run scrape <URL>
  → client fetches AES API
  → parsers build Division model
  → GraphBuilder creates DAG
  → TeamScheduleExporter writes JSON
  → Output: web/data/{slug}/tournament.json
  → Updates: web/data/index.json
```

---

## 6. Presentation Layer

### Design Philosophy
Parents checking their kid's schedule on a phone at a tournament gym. Optimize for:
- Glanceability (info density without clutter)
- Mobile-first (most access will be phone)
- Speed (static files, no JS framework overhead)
- **Polished, modern feel** — should look like a quality sports app, not a bare data dump

### Visual Design
- **Header**: Bold gradient banner (indigo-600 → purple-600) with white text, tournament name prominent. Gives the site identity and a professional first impression.
- **Cards**: White with subtle shadow (`shadow-md`), rounded corners (`rounded-xl`), generous padding. Hover: lift with `shadow-lg` transition. Cards should feel tactile and elevated.
- **Typography**: Use Tailwind's `font-semibold` for team names, `text-sm text-gray-500` for secondary info (club, seed). Clear visual hierarchy between team name, club, and game details.
- **Game rows**: Alternating subtle backgrounds (`even:bg-gray-50`) for readability. Left color border (4px) for status. Compact but not cramped — `py-2 px-3` minimum.
- **Status badges**: Small rounded pills (`rounded-full px-2 py-0.5 text-xs font-medium`) for role (H/A/W) and match status. Use solid background colors, not just text.
- **Team selector**: Styled input with search icon, rounded, focus ring (`focus:ring-2 focus:ring-indigo-500`). Should feel like a modern search bar, not a raw `<select>`.
- **Day tabs**: Rounded pill-style tabs (`rounded-full`) with active state in indigo, inactive in gray. Smooth transition on switch.
- **Empty states**: When no games for a date or no team selected, show a friendly message with muted text and an icon — not a blank page.
- **Loading state**: Skeleton shimmer or spinner while fetching JSON — never show a blank/broken page during load.
- **Transitions**: Fade/slide cards in on tab switch (`transition-opacity duration-200`). Smooth, not jarring.
- **Score display**: Won scores in bold green, lost in red. Sets should be comma-separated and easy to scan: "25-18, 25-21".

### Layout
- **Division selector**: Dropdown at top, populated from `index.json`
- **Team selector** (primary control): Dropdown + search box, "All Teams" default. This is the top-level navigation — selecting a team persists across date tab switches.
- **Day tabs** (secondary control): Horizontal tabs below team selector, one per tournament date. Switching dates preserves the current team selection.
- **URL hash**: `#division-slug/team-id/date` — team before date reflects navigation hierarchy
- **Team cards**: Within each day tab, one card per team showing:
  - Header: Team name, club, seed, W-L record
  - Game rows: Time | Court | Opponent | Role badge | Status/Scores
  - Color coding: green=win, red=loss, gray=scheduled, yellow=in-progress, purple/dashed=conditional
  - Group/tier badge: For power leagues, game rows display the group name (e.g., "Gold A") as a small badge next to the round name, helping parents identify which tier their team is competing in

### Tech Stack
- **Tailwind CSS** via CDN — utility-first styling, no build step
- **Vanilla JS** — no framework, just DOM manipulation
- **No build tools** — no npm, no webpack, no bundler
- **GitHub Pages compatible** — pure static files

### Color Coding
| Status | Color | Meaning |
|--------|-------|---------|
| Final (won) | Green | Team won this match |
| Final (lost) | Red | Team lost this match |
| Scheduled | Gray | Upcoming match, teams known |
| In Progress | Yellow/Amber | Currently playing |
| Conditional | Purple/dashed | Future possible game, opponent TBD |

**Conditional game row rendering:**
- Show time, court, round name as normal
- Opponent column shows descriptive text from `opponent_text`: "Winner of M3" or "1st Pool A"
- Dashed border, purple/indigo tint (`bg-purple-50 border-l-purple-500 border-dashed`)
- Score column shows "TBD" or dash (no scores available)

---

## 7. Deployment

### GitHub Actions Workflows

**CI (on PR):**
```
pixi install → pixi run lint → pixi run typecheck → pixi run test
```

**Scrape + Deploy (cron):**
```
pixi install → pixi run scrape <configured-URLs> → deploy web/ to GitHub Pages
```

### Environment Management
**pixi** handles everything:
- Python interpreter (3.11+ from conda-forge)
- All Python dependencies (httpx, pytest, ruff, mypy)
- Task definitions (test, scrape, serve, lint, typecheck)
- CI/CD environment setup (single `pixi install` command)

No pip, no venv, no requirements.txt, no setup.py ceremony.

---

## 8. Design Decisions

### Why Drop Cytoscape.js?
The sorting network graph visualization was technically impressive but wrong for the audience.
Parents don't want to interpret a DAG — they want "when does my kid play and did they win?"
A simple card layout answers this in 2 seconds vs 20+ seconds of graph navigation.

### Why Keep the Sorting Network Internally?
The sorting network is the *correct* model for tournament team flow. It:
- Makes the pool→bracket transition explicit via follow-on edges
- Handles complex multi-day tournaments with proper phase ordering
- Could power alternative views in the future (bracket viz, Sankey diagram)
- Is well-tested and mathematically sound

The key insight: use the right internal model, but present it in the simplest possible way.

### Why CDN-Only Frontend?
- Zero build complexity — no node_modules, no webpack config, no npm audit
- Instant deploys — just copy files to GitHub Pages
- Any developer can modify — open HTML in browser, edit, refresh
- Tailwind CDN is fast enough for a small site

### Why pixi?
- Single tool for Python version + deps + tasks
- Reproducible across dev machines and CI
- No virtualenv activation dance
- Lockfile ensures identical environments

---

## 9. Development Principles

### KISS (Keep It Simple, Stupid)
Every component should be as simple as possible. No abstractions until they're needed twice.
No feature flags. No plugin architecture. No configuration beyond what's necessary.

### YAGNI (You Aren't Gonna Need It)
Don't build for hypothetical future requirements. If we need it later, we'll add it later.
Three similar lines of code is better than a premature abstraction.

### Test-Driven Development
- Unit tests with inline fixtures (no live API calls in CI)
- Integration tests with captured API fixtures (`pixi run capture-fixtures`)
- Tests run fast: `pixi run test` should complete in seconds

### Modularity
- Scraper knows nothing about the frontend
- Parsers are independent of each other
- GraphBuilder takes parsed data, returns a graph
- Exporter takes a graph, returns JSON
- Frontend takes JSON, renders HTML

Each layer can be tested and developed independently.

---

## 10. File Structure

```
TitanSchedule/
├── pyproject.toml          # pixi config, deps, tool settings
├── CLAUDE.md               # Agent instructions
├── docs/
│   ├── research.md         # This document
│   └── prompts/            # Sequential implementation prompts
├── scraper/
│   ├── __init__.py
│   ├── client.py           # Async HTTP client
│   ├── config.py           # API config, constants
│   ├── models.py           # Data classes
│   ├── url.py              # AES URL parser
│   ├── cli.py              # CLI entry point
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── division.py
│   │   ├── pool.py
│   │   ├── bracket.py
│   │   └── follow_on.py
│   └── graph/
│       ├── __init__.py
│       ├── builder.py      # Sorting network DAG builder
│       └── team_exporter.py # DAG → team-centric JSON
├── web/
│   ├── index.html
│   ├── js/
│   │   └── app.js
│   ├── css/
│   │   └── style.css
│   └── data/               # Generated JSON (gitignored)
│       └── index.json
├── tests/
│   ├── conftest.py
│   ├── test_client.py
│   ├── test_parsers/
│   ├── test_graph/
│   └── fixtures/           # Captured API responses
├── scripts/
│   ├── scrape.sh
│   └── serve.sh
└── .github/
    └── workflows/
        ├── ci.yml
        └── scrape.yml
```
