# Prompt 06: Validation and CI/CD

Validate the complete system end-to-end. Ensure everything fits together. Fix any issues.

## Validation Steps

### 1. Unit Tests
```bash
pixi run test
```
- All tests must pass
- Fix any failures discovered

### 2. Lint and Typecheck
```bash
pixi run lint
pixi run typecheck
```
- Must be clean (no errors)
- Fix any issues

### 3. Integration Tests
```bash
pixi run test-all
```
- If fixture files exist, integration tests should pass
- If not, capture them first: `pixi run capture-fixtures https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199189/overview`

### 4. End-to-End Scrape
```bash
pixi run scrape https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199189/overview
```
Use a real AES tournament URL. Verify:
- JSON output written to `web/data/{slug}/tournament.json`
- `web/data/index.json` updated
- JSON structure matches expected schema
- All team games present, scores correct, dates correct

### 5. Frontend Rendering
```bash
pixi run serve
```
Open in browser and verify:
- Division selector shows available divisions
- Day tabs appear and switch content
- Team cards display correctly with all fields
- Color coding works (win=green, loss=red, scheduled=gray)
- Team filter/search narrows displayed cards
- Mobile responsive (resize browser)
- No console errors

### 6. Cross-Component Integration
Verify these data flows work end-to-end:
- AES URL → client → parsers → Division model (correct teams, matches, rounds)
- Division → GraphBuilder → DAG (correct phases, edges, rankings)
- DAG → TeamScheduleExporter → JSON (correct games, records, ranks)
- JSON → frontend → rendered cards (correct display)

## CI/CD Setup

### `.github/workflows/ci.yml`
Triggered on: push to main, pull requests

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.8.1
        with:
          cache: true
      - run: pixi run lint
      - run: pixi run typecheck
      - run: pixi run test
```

### `.github/workflows/scrape.yml`
Triggered on: manual dispatch, cron schedule

```yaml
name: Scrape and Deploy
on:
  workflow_dispatch:
    inputs:
      url:
        description: 'AES tournament URL'
        required: true
  schedule:
    - cron: '0 */4 * * *'  # Every 4 hours during tournaments

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: prefix-dev/setup-pixi@v0.8.1
        with:
          cache: true
      - run: pixi run scrape ${{ github.event.inputs.url || env.DEFAULT_URL }}
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v4
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./web
```

**Configuration Notes:**
- Set `DEFAULT_URL` as a GitHub Actions repository variable for cron-triggered scrapes
- Enable GitHub Pages in repository settings: Source = Deploy from a branch, Branch = `gh-pages`

### 7. Format-Specific Validation
Test all 3 tournament formats to ensure the pipeline handles each correctly:

**Power League** (multi-date, tiered groups):
```bash
pixi run scrape https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199189/overview
pixi run scrape https://results.advancedeventsystems.com/event/PTAwMDAwNDE4Mjk90/divisions/199187/overview
```
- Verify multiple dates in output JSON
- Verify `group` field populated on games (e.g., "Gold A", "Silver B")
- Test both 14s (199189) and 18s-15s (199187) divisions

**Single-weekend tournament** (pool → bracket):
```bash
pixi run scrape https://results.advancedeventsystems.com/event/PTAwMDAwNDE3NTY90/divisions/198788/overview
```
- Verify both pool and bracket games present
- Verify follow-on/conditional games have `opponent_text`

**Pool-play-only** (no brackets):
```bash
pixi run scrape https://results.advancedeventsystems.com/event/PTAwMDAwNDE2NzI90/divisions/198273/overview
```
- Verify no bracket games in output
- Verify rankings come from pool standings
- Verify no errors from empty bracket/follow-on lists

## Bug Fixes
After running all validation steps, fix any issues discovered:
- Parser output mismatches
- Missing fields in exported JSON
- Frontend rendering bugs
- Type errors caught by mypy
- Lint violations

## Final Memory Update
After everything passes, update `/home/mvillmow/.claude/projects/-home-mvillmow-TitanSchedule/memory/MEMORY.md` with:
- Updated project overview (greenfield rewrite complete)
- Final file structure
- Any new patterns or conventions established
- Remove outdated information about the old Cytoscape implementation
