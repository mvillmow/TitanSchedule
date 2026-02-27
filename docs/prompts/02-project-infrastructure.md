# Prompt 02: Project Infrastructure

Set up the greenfield project infrastructure. **Do not reuse existing code.** Read `docs/research.md` for the full architecture.

## What to Create

### `pyproject.toml`
- Project name: `titanschedule`
- Python 3.11+ requirement
- Dependencies: `httpx[http2]`, `click` (CLI)
- Dev dependencies: `pytest`, `pytest-asyncio`, `respx`, `ruff`, `mypy`
- pixi configuration with tasks:
  - `test` — run pytest (exclude integration tests marked `@pytest.mark.integration`)
  - `test-all` — run pytest including integration tests
  - `scrape` — run `python -m scraper.cli scrape` with args
  - `serve` — `python -m http.server 8080 -d web`
  - `capture-fixtures` — run fixture capture script
  - `lint` — `ruff check scraper/ tests/`
  - `typecheck` — `mypy scraper/`
- ruff config: line-length 100, select E/F/W/I/UP
- mypy config: strict mode

### Project Skeleton
```
scraper/
  __init__.py
  models.py       # Empty data classes file with TODO
  config.py       # API base URL, default headers, rate limit settings
  parsers/
    __init__.py
  graph/
    __init__.py
web/
  index.html      # Minimal placeholder
  js/
    app.js        # Minimal placeholder
  css/
    style.css     # Empty
  data/
    .gitkeep
tests/
  __init__.py
  conftest.py     # Shared fixtures, pytest config
scripts/
  .gitkeep
docs/             # Already exists
```

### `scraper/config.py`
```python
API_BASE = "https://results.advancedeventsystems.com/api"
DEFAULT_HEADERS = {"Accept": "application/json"}
RATE_LIMIT_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 3
```

### `scraper/models.py`
Stub with a comment indicating models will be defined in prompt 03.

### `tests/conftest.py`
Basic conftest with pytest-asyncio mode set to "auto".

### `.gitignore`
Update to include: `__pycache__/`, `.pixi/`, `*.egg-info/`, `web/data/*/`, `.mypy_cache/`, `.ruff_cache/`

## Verification
After creating everything:
1. Run `pixi install` — should succeed
2. Run `pixi run test` — should pass (no tests yet, 0 collected)
3. Run `pixi run lint` — should pass (no code to lint yet)
