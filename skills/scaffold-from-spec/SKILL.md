# Scaffold From Spec

| Field | Value |
|-------|-------|
| Date | 2026-03-10 |
| Objective | Scaffold a greenfield project matching an architecture spec (research.md) |
| Outcome | Success after review pass caught 12 missing files |

## When to Use

- Greenfield project setup from an architecture/design document
- Any time a plan specifies files to create and there's a separate spec listing the full file tree
- Pixi-based Python/JS projects with pyproject.toml

## Verified Workflow

1. **Read the spec's file structure section first** — identify every file/directory mentioned
2. **Cross-reference the plan against the spec** — plans often list a subset; the spec's file tree is the source of truth
3. **Create all files in parallel** using Write tool (fast, no dependencies between files)
4. **Verify immediately**: `pixi install`, `pixi run test`, `pixi run lint`
5. **Review against spec** before committing — diff the file tree against the spec's Section 10 (or equivalent)

## Failed Attempts

| What | Why It Failed |
|------|---------------|
| Trusting the plan's file list as complete | Plan listed 13 files; spec's file tree had 25+. Missing: cli.py, url.py, client.py, capture_fixtures.py, 4 parser modules, 2 graph modules, tests/integration/, tests/fixtures/, docs/prompts/ |
| Dead import in conftest.py | `import pytest  # noqa: F401` adds nothing. Better to include a useful fixture like `FIXTURES_DIR` |

## Results & Parameters

### pyproject.toml Gotchas (pixi)
- `license = "BSD-3-Clause"` — SPDX string, NOT table syntax `{text = "..."}`
- `[tool.pixi.workspace]` — NOT `[tool.pixi.project]` (deprecated)
- Must include `[tool.setuptools.packages.find]` with `include = ["scraper*"]` when multiple top-level dirs exist
- `pytest-asyncio` mode goes in `[tool.pytest.ini_options]` as `asyncio_mode = "auto"`

### Verification Commands
```bash
pixi install          # environment setup
pixi run test         # exit code 5 = no tests collected (OK for skeleton)
pixi run lint         # ruff check
pixi run typecheck    # mypy strict
```

### Key Principle
> Always diff the implementation against the spec's file tree section before committing. Plans drift from specs — the spec is the source of truth.
