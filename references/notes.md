# Frontend from Data Contract — Raw Notes

## Session: 2026-03-10

### Context
TitanSchedule frontend implementation. Backend exporter (`team_exporter.py`) produces `tournament.json` per division. Frontend reads this JSON and renders mobile-first team cards.

### Key Decision: innerHTML vs DOM manipulation
The initial implementation used `innerHTML` with an `esc()` helper that used `textContent` assignment to escape HTML entities. This is technically safe but was blocked by a project security hook that flags any `innerHTML` usage with dynamic content. The rewrite to pure `createElement`/`textContent` was cleaner anyway and eliminated the need for `esc()` entirely.

### index.json Format Evolution
Originally planned as a flat array: `[{id, name, slug, code_alias, color_hex}]`
Changed to object wrapper: `{event: "...", divisions: [{slug, name}]}`
The `loadDivisions` function handles both via: `Array.isArray(data) ? data : (data.divisions || [])`

### URL Hash Bug
Format: `#division/teamId/date`
When teamId is null (all teams) and only date is present, `updateHash` produced `#division/2025-03-08` — two segments. `parseHash` then assigned `parts[1]` (the date) as `teamId`. Fixed by always emitting three segments with `"all"` as sentinel for no team selection.

### CSS Specificity Issue
Custom `.even-row { background-color: ... }` gets overridden by Tailwind's `bg-green-50/60` etc. because both set `background-color`. Fix: only apply `even-row` class when no status background exists (`!statusCls`).

### Spec Compliance Catches (Second Review)
- Gradient was `indigo-700 → purple-700`, spec says `indigo-600 → purple-600`
- Header showed hardcoded "TitanSchedule" instead of event name from `index.json`
- Role badges were `rounded` (square corners) instead of `rounded-full` (pill shape) per spec
- Conditional games showed "Conditional" text, spec says "TBD"
- Left border color coding was missing on non-conditional status rows
