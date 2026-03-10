# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

TitanSchedule is a tournament sorting network visualization tool for SportsEngine AES volleyball
tournaments. It consumes the AES public REST JSON API (no auth required) to build a DAG of
tournament matches and renders them with Cytoscape.js.

**Stack**: Python (scraper) + vanilla JS/HTML/Tailwind CSS (frontend) + pixi (environment)

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
```

## Tech Stack

- **Python** (`scraper/`): API client, parsers, graph builder, exporter, CLI
- **Vanilla JS/HTML** (`web/`): Cytoscape.js 3.28, Tailwind CSS, jsPDF — all CDN, no build tools
- **pixi**: Environment and dependency management (uses uv internally)
- **pytest**: Test framework with inline fixtures

## Project Structure

```text
TitanSchedule/
├── scraper/          # Python package (client, parsers, graph, exporter, CLI)
├── web/              # Frontend SPA (CDN-only, no build tools)
│   └── js/           # Cytoscape.js graph, controls, trajectory, export
├── tests/            # pytest suite with inline fixtures
├── scripts/          # Shell automation (scrape.sh, serve.sh, etc.)
├── docs/             # Documentation and research
├── .claude/          # Agent system
│   ├── agents/       # 6 agent definitions
│   ├── commands/     # 4 slash commands
│   ├── skills/       # 8 skill directories
│   └── shared/       # 4 shared constraint/policy files
└── CLAUDE.md         # This file
```

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
fix(web): correct highlight opacity on hidden nodes
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
| `frontend-engineer` | haiku | Vanilla JS, Cytoscape.js, Tailwind |

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

## Common Pitfalls

- `[] or DEFAULT` evaluates to DEFAULT in Python — use `X if X is None else DEFAULT`
- AES match IDs are negative — timeline tiebreaker uses `-match_id`
- Port nodes use `data.parentId` (not `data.parent`) — Cytoscape reserves `data.parent`
- HTML overlay exports (PNG/SVG/PDF) do NOT capture `.match-card`/`.ranking-card` overlays
