# Prompt 01: Agent Infrastructure

Integrate Claude Code agent infrastructure adapted from [ProjectOdyssey](https://github.com/HomericIntelligence/ProjectOdyssey) patterns. This is a **greenfield project** — do not reuse any existing TitanSchedule code.

Study ProjectOdyssey's `.claude/` directory structure for patterns, then adapt them for TitanSchedule. The project is a Python scraper + static HTML/JS/CSS frontend for volleyball tournament schedules.

## What to Create

### `CLAUDE.md`
Project overview and instructions for the Claude Code agent:
- Project description: AES volleyball tournament schedule viewer
- Architecture: 3-layer (scraper → sorting network DAG → team-centric JSON → static HTML)
- Dev commands: `pixi run test`, `pixi run scrape <URL>`, `pixi run serve`, `pixi run lint`, `pixi run typecheck`
- Package manager: **pixi** (not pip/venv). `pixi install` to set up.
- Frontend: CDN-only (Tailwind CSS), no npm, no build tools
- Key conventions: AES negative IDs, round sorting, test with inline fixtures
- PR rules: all tests pass, lint clean, typecheck clean

### `.claude/settings.json`
Bash safety hooks to prevent destructive commands.

### `.claude/shared/`
Shared constraint docs referenced by all agents (adapted from ProjectOdyssey, dropping Mojo-specific ones):

- **`common-constraints.md`** — pixi for env management, Python 3.11+, CDN-only frontend, no Playwright, AES REST JSON API only
- **`pr-workflow.md`** — Branch naming, test/lint/typecheck before PR, commit message format (conventional commits), PR checklist
- **`error-handling.md`** — Retry strategy for AES API (exponential backoff on 429/5xx), defensive parsing for missing/null fields, timeout handling (30s default)
- **`git-commit-policy.md`** — No `--no-verify`, conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`), atomic commits

### `.claude/agents/`
Three agents using ProjectOdyssey's YAML frontmatter format:

#### `scraper-engineer.md`
```yaml
---
name: scraper-engineer
description: "Python async HTTP, AES API client, parsers, graph builder, exporter"
level: 3
phase: Implementation
tools: Read,Write,Edit,Bash,Grep,Glob
model: sonnet
delegates_to: [test-engineer]
receives_from: []
---
```
**Identity**: Specialist in Python async programming, AES tournament API, data parsing, and sorting network graph construction.
**Scope**: `scraper/` directory — client.py, models.py, config.py, url.py, parsers/*, graph/*
**Workflow**: 1. Read research.md for API details 2. Implement/modify scraper code 3. Write tests 4. Run `pixi run test` 5. Run `pixi run lint` and `pixi run typecheck`
**Constraints**: Link to `common-constraints.md`, `error-handling.md`
**Example**: "Implement the PoolParser to extract matches and standings from the poolsheet API response"

#### `frontend-engineer.md`
```yaml
---
name: frontend-engineer
description: "Vanilla JS, Tailwind CSS, static HTML frontend for tournament schedules"
level: 3
phase: Implementation
tools: Read,Write,Edit,Bash,Grep,Glob
model: sonnet
delegates_to: []
receives_from: []
---
```
**Identity**: Specialist in vanilla JavaScript, Tailwind CSS, responsive design, and static site development.
**Scope**: `web/` directory — index.html, js/app.js, css/style.css
**Workflow**: 1. Read research.md for design specs 2. Implement/modify frontend code 3. Test locally with `pixi run serve` 4. Verify responsive design
**Constraints**: Link to `common-constraints.md`. CDN-only (no npm, no build tools). No frameworks (React, Vue, etc.).

#### `test-engineer.md`
```yaml
---
name: test-engineer
description: "pytest suite, inline fixtures, integration tests, fixture capture"
level: 4
phase: Test
tools: Read,Write,Edit,Bash,Grep,Glob
model: haiku
delegates_to: []
receives_from: [scraper-engineer]
---
```
**Identity**: Specialist in pytest, test fixture design, and integration testing.
**Scope**: `tests/` directory, `scripts/capture_fixtures.py`
**Workflow**: 1. Write tests with inline fixtures 2. Run `pixi run test` 3. For integration tests: `pixi run capture-fixtures <URL>` then `pixi run test-all`
**Constraints**: Link to `common-constraints.md`. Inline fixtures for unit tests (no external JSON). Integration tests marked `@pytest.mark.integration`.

### `.claude/commands/`
- **`impl.md`** — Implementation workflow: read research.md, understand context, implement, test, lint, typecheck
- **`review.md`** — Code review checklist: correctness, tests, style, security
- **`test.md`** — Test workflow: run tests, check failures, fix

### `.claude/skills/`
Skills define reusable procedures:

- **`run-tests.md`** — `pixi run test` for unit tests, `pixi run test-all` for integration
- **`scrape-division.md`** — `pixi run scrape <URL>` to scrape an AES division
- **`serve-local.md`** — `pixi run serve` to serve frontend on port 8080
- **`capture-fixtures.md`** — `pixi run capture-fixtures <URL>` to save API responses for integration tests

## Constraints
- No Mojo content — this is Python + HTML/JS/CSS only
- 3 agents only (not 31 like ProjectOdyssey — this is a small project)
- No pre-bash-exec.py hook (keep it simple, use settings.json deny patterns instead)
- No slash commands beyond impl/review/test
- No plugin system
- Adapt patterns from ProjectOdyssey but keep everything concise and proportional to project size
