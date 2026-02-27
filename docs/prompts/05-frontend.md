# Prompt 05: Frontend

Implement the presentation layer from scratch per `docs/research.md`. **Greenfield.**

## What to Implement

### `web/index.html` — Main Page

Single HTML file serving as both landing page and tournament view.

**Structure:**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TitanSchedule</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="css/style.css">
</head>
<body class="bg-gray-100 min-h-screen">
  <!-- Header: title + division selector -->
  <!-- Controls: day tabs + team filter/search -->
  <!-- Content: team cards grid -->
  <script src="js/app.js"></script>
</body>
</html>
```

### `web/js/app.js` — Application Logic

**Initialization:**
1. Fetch `data/index.json` to get available divisions
2. Populate division selector dropdown
3. On division select: fetch `data/{slug}/tournament.json`
4. Render day tabs and team cards

**Division Selector:**
- Dropdown at top of page
- Shows division names from `index.json`
- Auto-selects first division on load

**Team Selector (primary control):**
- Dropdown listing all teams (sorted alphabetically) — positioned prominently as the top-level navigation control
- "All Teams" default option
- Search/filter input to narrow the dropdown
- When a team is selected: only show that team's card
- **Team selection persists across date tab switches** — changing the date does not reset the team filter
- URL hash format: `#division-slug/team-id/date` (team before date reflects navigation hierarchy)

**Day Tabs (secondary control):**
- Horizontal tab bar from `data.dates[]`, below team selector
- Format dates nicely: "Sat Mar 8" instead of "2025-03-08"
- Active tab highlighted
- Show all days, default to first day (or today if applicable)
- Switching tabs preserves current team selection

**Team Cards:**
- One card per team per day
- Only show cards for teams that have games on the selected day
- Cards arranged in a responsive grid (1 col mobile, 2 col tablet, 3 col desktop)

**Group/Tier Display (Power Leagues):**
- For tournaments with tiered groups, show tier info on cards: "Gold A - Pool 1"
- Display `game.group` value when non-null, prepended to round name

**Tournament Format Considerations:**
- **Power League** (4-6 dates): Scrollable date tabs, tier/group info on cards
- **Single-weekend tournament** (pool → bracket): Conditional game rows for bracket matches with unresolved opponents
- **Pool-play-only** (no brackets): Only pool games shown, rankings from pool standings, no conditional rows

**Card Layout:**
```
┌─────────────────────────────────┐
│ Club Titans 14-1        Seed: 3 │
│ Club Titans            W: 3 L: 1│
├─────────────────────────────────┤
│ 8:00a │ Ct 3 │ vs Other Club │H │ W 25-18, 25-21 │
│ 9:30a │ Ct 5 │ vs Another    │A │ L 20-25, 18-25 │
│ 11:00 │ Ct 1 │ vs Team Three │H │ Scheduled       │
└─────────────────────────────────┘
```

**Game Row Details:**
- Time: formatted short (8:00a, 11:30a, 1:00p)
- Court: abbreviated
- Opponent: team name
- Role badge: H (home) / A (away) / W (work) — small colored badge
- Result: "W 25-18, 25-21" or "L 20-25" or "Scheduled" or "In Progress"

**Color Coding (per game row):**
- Won: green background/border (`bg-green-50 border-l-green-500`)
- Lost: red background/border (`bg-red-50 border-l-red-500`)
- Scheduled: gray background (`bg-gray-50`)
- In Progress: yellow/amber background (`bg-yellow-50 border-l-yellow-500`)
- Conditional: purple/dashed border (`bg-purple-50 border-l-purple-500 border-dashed`)
- Work duty: blue-gray, dimmed

**Conditional Game Row Rendering:**
- Show time, court, round name as normal
- Opponent column shows `opponent_text` value: "Winner of M3" or "1st Pool A"
- Dashed border, purple/indigo tint to visually distinguish from scheduled games
- Score column shows "TBD" or dash (no scores available)

### Visual Design Requirements

The site should look like a polished sports app, not a bare data table. Key details:

- **Header**: Gradient banner (`bg-gradient-to-r from-indigo-600 to-purple-600`) with white text. Tournament name large and bold. Division selector styled as a white pill dropdown within the header.
- **Cards**: White, `rounded-xl shadow-md`, hover → `shadow-lg` with smooth transition (`transition-shadow duration-200`). Generous padding (`p-4`). Card header has team name (`text-lg font-semibold`), club name below in `text-sm text-gray-500`, seed and record as badges on the right.
- **Game rows**: Left border (4px) colored by status. Alternating row backgrounds (`even:bg-gray-50/odd:bg-white`). Minimum `py-2 px-3` padding. Score text uses `font-mono` for alignment.
- **Role badges**: Tiny rounded pills (`rounded-full px-2 py-0.5 text-xs font-medium`). Home = blue (`bg-blue-100 text-blue-700`), Away = orange (`bg-orange-100 text-orange-700`), Work = gray (`bg-gray-200 text-gray-600`).
- **Team selector**: Styled like a modern search bar — rounded input with magnifying glass icon, `focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500`. Not a raw `<select>` element — use a custom searchable dropdown or combobox pattern.
- **Day tabs**: Pill-style (`rounded-full px-4 py-2`). Active = `bg-indigo-600 text-white`, inactive = `bg-gray-200 text-gray-700 hover:bg-gray-300`. Smooth transition.
- **Empty states**: Centered message with muted icon (calendar or clipboard) and text like "No games on this day" in `text-gray-400`. Never show a blank area.
- **Loading state**: Show skeleton placeholders (animated gray bars mimicking card layout) or a centered spinner while fetching data. Page should never appear broken during load.
- **Transitions**: Cards fade in on tab/team switch (`transition-opacity duration-200`). Avoid layout jumps — set min-heights on containers.
- **Scores**: Won → bold green text. Lost → red text. Sets comma-separated in `font-mono`: "25-18, 25-21". Scheduled → `text-gray-400 italic`. Conditional → `text-purple-500 italic` "TBD".
- **Overall palette**: Indigo/purple accents on white/gray-50 backgrounds. Consistent spacing using Tailwind's 4px grid. Clean, modern, trustworthy feel.

### `web/css/style.css` — Custom Styles

Minimal custom CSS beyond Tailwind:
- Skeleton loading animation (`@keyframes shimmer`)
- Print styles (hide controls, show all teams)
- Transition animations for tab switching and card entrance
- Custom scrollbar styling for team selector dropdown
- Any Tailwind-impossible styles

## Responsive Design

**Mobile (< 640px):**
- Single column cards
- Stacked game row layout (time+court on one line, opponent on next)
- Full-width day tabs (scrollable if many days)

**Tablet (640-1024px):**
- Two column card grid
- Standard game row layout

**Desktop (> 1024px):**
- Three column card grid
- Spacious layout

## Accessibility

- ARIA labels on interactive elements: day tabs (`role="tablist"`/`role="tab"`), team dropdown (`role="combobox"`), cards (`role="article"`)
- Keyboard navigation: Tab through cards, Enter to select team from dropdown
- `aria-live="polite"` on the cards container for dynamic content updates
- Sufficient color contrast — don't rely on color alone for win/loss status (also use text: "W"/"L")
- `prefers-reduced-motion` media query: disable card transitions and tab animations
- No dark mode — explicitly out of scope to keep things simple

**Power League Date Tabs:**
- Handle 4-6 dates gracefully with horizontally scrollable tab bar (`overflow-x-auto`)
- Show scroll indicators when tabs overflow

## Constraints
- CDN-only: Tailwind via `<script src="https://cdn.tailwindcss.com">`, no npm
- No Cytoscape.js, no D3, no charting libraries
- No build tools — plain JS, works by opening index.html
- GitHub Pages compatible (all paths relative)
- Vanilla JS only — no React, Vue, Svelte, etc.
- Works offline once JSON is loaded (no further API calls from frontend)
