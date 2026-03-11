# Frontend from Data Contract

| Field | Value |
|-------|-------|
| Date | 2026-03-10 |
| Objective | Implement vanilla JS/HTML/CSS frontend from a JSON data contract defined in research.md |
| Outcome | Success after 2 review passes catching 10 total issues |

## When to Use

- Building a frontend that consumes a JSON API/file with a predefined contract
- Implementing a spec from an architecture document
- Vanilla JS (no framework) with Tailwind CDN

## Verified Workflow

1. **Read the data contract first** — understand every field, nullable, and status enum before writing any code
2. **Implement files in parallel** — HTML + CSS can be done alongside JS when the contract is known
3. **Use pure DOM manipulation** — avoid `innerHTML` with dynamic data; security hooks will block it and `textContent` + `createElement` is safer
4. **Support flexible data shapes** — if the backend contract may evolve (array vs object wrapper), handle both: `Array.isArray(data) ? data : (data.divisions || [])`
5. **URL hash needs sentinels** — if the hash format is `#a/b/c` and middle segments are optional, use a sentinel like `"all"` instead of omitting, otherwise segments shift and get misinterpreted
6. **Two-pass review against spec** — first pass catches logic bugs, second pass catches visual/style mismatches

## Review Checklist (Frontend vs Spec)

- [ ] Every field in the data contract is consumed or gracefully ignored
- [ ] URL hash round-trips correctly for all states (all teams, specific team, no date)
- [ ] Color values match spec exactly (e.g. `600` vs `700` gradient stops)
- [ ] CSS specificity: custom classes don't get overridden by utility framework classes
- [ ] Dynamic content (event name, division name) is wired to the UI, not hardcoded
- [ ] Dead code removed after refactors (e.g. escape functions after innerHTML removal)
- [ ] Status colors, borders, and badges match the spec table exactly
- [ ] Alternating row backgrounds only apply when no status background is active
- [ ] Conditional/TBD games render with correct label text per spec
- [ ] Print and reduced-motion media queries are present

## Failed Attempts

| Attempt | Why It Failed | Fix |
|---------|--------------|-----|
| `innerHTML` with `esc()` for card rendering | Security hook blocked innerHTML with dynamic content | Rewrote to pure DOM (`createElement` + `textContent`) |
| Omitting team segment from URL hash when "All Teams" | `#division/date` — date parsed as teamId on reload | Added `"all"` sentinel: `#division/all/date` |
| `even-row` CSS class for alternating backgrounds | Overridden by Tailwind status bg classes (`bg-green-50/60` etc.) | Only apply `even-row` when `statusCls` is empty |
| Hardcoded "TitanSchedule" in header | `index.json` changed to `{event, divisions}` format with event name | Read `data.event` and set `#event-title` textContent |

## Results & Parameters

- **Stack**: Vanilla JS + Tailwind CDN + custom CSS (no build tools)
- **File count**: 3 source files (HTML, CSS, JS ~510 lines total)
- **Data format**: `index.json` (object with event + divisions array), `tournament.json` (division/dates/teams)
- **Game statuses**: `final`, `in_progress`, `scheduled`, `conditional`
- **Color mapping**: green=win, red=loss, yellow=in-progress, gray=scheduled, purple/dashed=conditional
- **Hash format**: `#division-slug/team-id-or-all/date`
