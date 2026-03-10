# Scaffold Session Notes — 2026-03-10

## What happened

Implemented "Prompt 02: Project Infrastructure Setup" for TitanSchedule.

### Round 1: Plan execution
- Created pyproject.toml, .gitignore, and 13 skeleton files per the plan
- pixi install succeeded, lint passed, test passed (0 collected)
- Caught and fixed `[tool.pixi.project]` → `[tool.pixi.workspace]` deprecation

### Round 2: Review against research.md
- Compared implementation against `docs/research.md` Section 10 (File Structure)
- Found 12 missing files that the plan didn't include but the spec required:
  - scraper/cli.py, capture_fixtures.py, url.py, client.py
  - scraper/graph/builder.py, team_exporter.py
  - scraper/parsers/division.py, pool.py, bracket.py, follow_on.py
  - tests/integration/__init__.py, tests/fixtures/.gitkeep
  - docs/prompts/.gitkeep
- Also improved conftest.py from dead import to useful FIXTURES_DIR constant

### Round 3: Added missing files, re-verified, committed

## Lesson
The implementation plan was a subset of the architecture spec. Always use the spec's file tree as the checklist, not the plan's file list.
