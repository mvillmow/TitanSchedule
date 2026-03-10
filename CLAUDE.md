# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

TitanSchedule is a tournament schedule viewer for SportsEngine AES volleyball tournaments.
It scrapes the AES public REST JSON API (no auth required), builds an internal sorting-network
DAG, exports team-centric JSON, and renders a static team card UI optimized for parents
checking schedules on their phones at tournaments.

**Stack**: Python (scraper) + vanilla JS/HTML/Tailwind CSS (frontend) + pixi (environment)

**Canonical architecture**: See `docs/research.md` for the full design document.

## CRITICAL RULES

### Never Push Directly to Main

**ALL changes MUST go through a pull request.**

```bash
# CORRECT workflow
git checkout -b <issue-number>-description
# make changes, commit
git push -u origin <branch-name>
gh pr create --title "Brief description" --body "Closes #<issue-number>"
```

### Never Use `--no-verify`

See [Git Commit Policy](.claude/shared/git-commit-policy.md) for details.

## Quick Links

- [Architecture Design (research.md)](docs/research.md)
- [Common Constraints](.claude/shared/common-constraints.md)
- [PR Workflow](.claude/shared/pr-workflow.md)
- [Git Commit Policy](.claude/shared/git-commit-policy.md)
- [Error Handling](.claude/shared/error-handling.md)

## Common Commands

```bash
pixi install              # Set up environment
pixi run test             # Run pytest (excludes integration tests)
pixi run test-all         # Run all tests including integration
pixi run scrape <URL>     # Full scrape pipeline
pixi run serve            # http.server on port 8080
pixi run capture-fixtures <URL>  # Save API JSON to tests/fixtures/
pixi run lint             # ruff check scraper/ tests/
pixi run typecheck        # mypy scraper/
```

## Tech Stack

- **Python** (`scraper/`): Async HTTP client (httpx), parsers, graph builder, team exporter, CLI (click)
- **Vanilla JS/HTML** (`web/`): Tailwind CSS (CDN), no frameworks, no build tools
- **pixi**: Environment and dependency management (uses uv internally)
- **pytest**: Test framework with inline fixtures

## Project Structure

```text
TitanSchedule/
├── pyproject.toml         # pixi config, deps, tool settings
├── CLAUDE.md              # This file
├── docs/
│   ├── research.md        # Canonical architecture document
│   └── prompts/           # Sequential implementation prompts
├── scraper/
│   ├── __init__.py
│   ├── client.py          # Async HTTP client (httpx)
│   ├── config.py          # API config, constants
│   ├── models.py          # Data classes
│   ├── url.py             # AES URL parser
│   ├── cli.py             # CLI entry point (click)
│   ├── parsers/
│   │   ├── division.py
│   │   ├── pool.py
│   │   ├── bracket.py
│   │   └── follow_on.py
│   └── graph/
│       ├── builder.py     # Sorting network DAG builder
│       └── team_exporter.py  # DAG → team-centric JSON
├── web/
│   ├── index.html
│   ├── js/
│   │   └── app.js         # Frontend logic
│   ├── css/
│   │   └── style.css
│   └── data/              # Generated JSON (gitignored)
│       └── index.json     # Division index
├── tests/
│   ├── conftest.py
│   ├── test_client.py
│   ├── test_parsers/
│   ├── test_graph/
│   └── fixtures/          # Captured API responses
├── scripts/
│   ├── scrape.sh
│   └── serve.sh
└── .github/
    └── workflows/
        ├── ci.yml         # lint → typecheck → test
        └── scrape.yml     # Cron scrape + deploy to GitHub Pages
```

## Pipeline

```text
AES REST API → httpx client → parsers → sorting network DAG → TeamScheduleExporter → JSON → static HTML
```

### TeamScheduleExporter Output

The exporter converts the DAG into team-centric JSON at `web/data/{slug}/tournament.json`:

- **Game status values**: `"final"`, `"in_progress"`, `"scheduled"`, `"conditional"`
- **Conditional games**: `opponent` is null, `opponent_text` describes source (e.g., "Winner of M3", "1st Pool A")
- Each team has: name, club, seed, games array, record, rank

### Tournament Format Variants

- **Power League**: Multi-date season with tiered groups (Gold/Silver/Bronze), re-seeding between rounds
- **Single-Weekend**: Day 1 pools → Day 2 brackets, follow-on edges link pool standings to bracket seeds
- **Pool-Play-Only**: Just pools, no brackets, rankings come from pool standings directly

## Frontend

Mobile-first team card layout for parents at tournaments:

- **Division selector**: Dropdown populated from `web/data/index.json`
- **Team selector**: Dropdown + search, "All Teams" default
- **Day tabs**: One per tournament date, preserves team selection on switch
- **Team cards**: Header (name, club, seed, W-L) + game rows (time, court, opponent, role, status/scores)
- **URL hash**: `#division-slug/team-id/date`
- **Color coding**: Green=win, Red=loss, Gray=scheduled, Yellow=in-progress, Purple/dashed=conditional
- **CDN-only**: Tailwind CSS, no npm, no build tools, no frameworks

## Key Development Principles

1. KISS - *K*eep *I*t *S*imple *S*tupid -> Don't add complexity when a simpler solution works
1. YAGNI - *Y*ou *A*in't *G*onna *N*eed *I*t -> Don't add things until they are required
1. TDD - *T*est *D*riven *D*evelopment -> Write tests to drive the implementation
1. DRY - *D*on't *R*epeat *Y*ourself -> Don't duplicate functionality, data structures, or algorithms
1. SOLID - *S**O**L**I**D* ->
  . Single Responsibility
  . Open-Closed
  . Liskov Substitution
  . Interface Segregation
  . Dependency Inversion
1. Modularity - Develop independent modules through well defined interfaces
1. POLA - *P*rinciple *O*f *L*east *A*stonishment - Create intuitive and predictable interfaces to not surprise users

Relevant links:

- [Core Principles of Software Development](<https://softjourn.com/insights/core-principles-of-software-development>)
- [7 Common Programming Principles](<https://www.geeksforgeeks.org/blogs/7-common-programming-principles-that-every-developer-must-follow/>)
- [Software Development Principles](<https://coderower.com/blogs/software-development-principles-software-engineering>)
- [Clean Coding Principles](<https://www.pullchecklist.com/posts/clean-coding-principles>)

## Commit Message Format

Follow conventional commits:

```text
feat(scraper): add bracket parser for elimination rounds
fix(web): correct day tab switching on team selection
docs(readme): update API endpoint documentation
refactor(graph): simplify phase grouping logic
test(parsers): add edge case for negative match IDs
```

## Agent System

This project uses a flat agent system for Claude Code automation.

### Agents (`.claude/agents/`)

| Agent | Model | Purpose |
|-------|-------|---------|
| `implementation-engineer` | haiku | Python/JS implementation |
| `test-engineer` | haiku | pytest test suites |
| `code-review-orchestrator` | sonnet | Coordinates 3 review dimensions |
| `ci-failure-analyzer` | sonnet | CI log analysis and diagnosis |
| `documentation-engineer` | haiku | Docstrings, README, examples |
| `frontend-engineer` | haiku | Vanilla JS, Tailwind CSS, team cards |

### Commands (`.claude/commands/`)

- `/impl <issue>` — Implement a GitHub issue
- `/test [path]` — Run tests (auto-detect or specific path)
- `/fix-ci <pr>` — Diagnose and fix CI failures
- `/review <pr>` — Comprehensive PR review

### Skills (`.claude/skills/`)

- **GitHub**: `gh-create-pr-linked`, `verify-pr-ready`, `gh-check-ci-status`, `gh-fix-pr-feedback`
- **CI/CD**: `fix-ci-failures`, `run-precommit`
- **Quality**: `quality-run-linters`
- **Review**: `review-pr-changes`

### Skill Delegation Patterns

Agents delegate to skills using these patterns:

- **Direct**: Invoke skill for a specific action (e.g., `gh-create-pr-linked` after implementation)
- **Conditional**: Decide based on context (e.g., run linters only if Python files changed)
- **Multi-Skill Workflow**: Chain skills (e.g., lint -> test -> create PR)

## AES API Notes

- Base URL: `https://results.advancedeventsystems.com/api`
- Header: `Accept: application/json` (no auth)
- AES IDs are **negative integers** (e.g., PlayId: -51151, MatchId: -51190)
- Round sort: less negative = earlier round; sort `reverse=True` for chronological order
- Match timeline tiebreaker: `-match_id` so less-negative sorts first

## Common Pitfalls

- `[] or DEFAULT` evaluates to DEFAULT in Python — use `X if X is None else DEFAULT`
- AES match IDs are negative — timeline tiebreaker uses `-match_id`
- FutureRoundMatches text format: "1st R1P1" where R1P1 = CompleteShortName
