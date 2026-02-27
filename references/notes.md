# Session Notes — TitanSchedule Implementation

## Session Date
2026-02-26

## What was implemented
Full 6-phase implementation of TitanSchedule from scratch:
- Phase 1: Python project scaffolding, AES API client (async httpx), URL parser
- Phase 2: Domain dataclasses (models.py)
- Phase 3: Four parsers (division, pool, bracket, follow-on)
- Phase 4: DAG builder, path pruner, Cytoscape.js exporter, CLI orchestration
- Phase 5: Vanilla JS SPA (Cytoscape.js, Dagre, Tippy.js — CDN only)
- Phase 6: Shell scripts (scrape, serve, snapshot, deploy)

## Test counts per phase
- test_url.py: 6 tests
- test_client.py: 8 tests
- test_models.py: 11 tests
- test_division_parser.py: 11 tests
- test_pool_parser.py: 16 tests
- test_bracket_parser.py: 13 tests
- test_followon_parser.py: 11 tests
- test_graph_builder.py: 14 tests
- test_pruner.py: 7 tests
- test_exporter.py: 13 tests
Total: 110 unit tests + 5 integration tests (skipped without fixtures) = 115

## Two bugs caught by TDD
1. DivisionParser sort direction — AES negative IDs sort reverse=True for chronological order
2. `[] or DEFAULT` pattern — empty list is falsy, must use `x if x is None else default`

## Key AES API discovery from research.md
The AES Angular SPA calls a public REST JSON API — no Playwright/headless browser needed.
All IDs in the API are negative integers.

## Run commands
```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Tests
pytest tests/ --ignore=tests/test_integration.py

# Capture live fixtures
python -m scraper.cli --capture-fixtures "https://results.advancedeventsystems.com/event/PTAwMDAwNDE4MzE90/divisions/199194/overview"

# Full scrape
./scripts/scrape.sh "https://results.advancedeventsystems.com/event/PTAwMDAwNDE4MzE90/divisions/199194/overview"

# Serve
./scripts/serve.sh  # → http://localhost:8080
```
