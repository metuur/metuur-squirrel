# Web UI Guide Page — Low-Level Design

> _Backfilled from the as-built `apps/backend/app/src/pages/GuidePage.tsx`._

## Architecture

A single self-contained React page. All content is declared as in-module constant
data; rendering is a set of section blocks gated by a shared `hit()` predicate so a
live search filters every section through one code path. No data fetching, no
backend dependency.

```
GuidePage.tsx
  data (module constants)
    CONCEPTS, CONCEPT_MAP_HAYSTACK, LIFECYCLES/LIFECYCLE_HAYSTACK,
    CONFIG_HAYSTACK, DAY_STEPS, AGENT_GROUPS, CLI_COMMANDS,
    POPUP_FEATURES, TRAY_FEATURES, WEBUI_FEATURES,
    BOARD_COLUMNS/DASHBOARD_HAYSTACK, FAQ_ENTRIES, NAV
  state
    query  → q = trimmed/lowercased; searching = q.length > 0
    active → selected section id (NAV[0] default)
  predicates
    hit(...fields) = !searching || fields.some(f => f.includes(q))
    show(id, hasMatch) = searching ? hasMatch : active === id
  layout
    sub-sidebar (NAV chips)  +  sticky search  +  section blocks
```

## Content model

- **Commands** are `CommandEntry { cmd, summary, what, example }`. Agent commands
  are grouped (`AGENT_GROUPS`: setup, daily flow, staying on track, work↔personal);
  CLI commands are a flat `CLI_COMMANDS` list. Both render via `CommandRow`
  (native `<details>`; `forceOpen` while searching so matches are readable).
- **Surface features** (`POPUP_FEATURES`, `TRAY_FEATURES`, `WEBUI_FEATURES`) are
  `[icon, term, def]` tuples rendered by `FeatureList`.
- **Concepts** (`CONCEPTS`) render as a card grid; two decorative illustrations —
  `ConceptMapIllustration` (vault anatomy: projects under the WIP cap, Inbox,
  Scratch Pad) and `LifecycleIllustration` (per-piece steppers) — are matched in
  search via prebuilt haystack strings (`CONCEPT_MAP_HAYSTACK`,
  `LIFECYCLE_HAYSTACK`) since their JSX has no searchable text fields.
- **Dashboard** explainer (`BOARD_COLUMNS`) mirrors the board legend
  (`BOARD_HELP_ROWS` in HomePage's BoardView); searched via `DASHBOARD_HAYSTACK`.
- **FAQ** (`FAQ_ENTRIES`) is `{ q, haystack, body }`; `haystack` (question + answer
  text) is what search matches; `body` is ReactNode.

## Search & navigation

- `hit(...fields)` returns true when not searching, else true if any field contains
  the query. Each section computes a filtered view (e.g.
  `concepts = CONCEPTS.filter(c => hit(c.term, c.def))`) and a boolean for
  illustration/haystack sections.
- `matchCount` sums all filtered lengths + illustration booleans; rendered in the
  search bar and driving the empty state.
- `show(id, hasMatch)`: while searching, a section renders iff it has a match;
  otherwise only the `active` section renders. Selecting a `NAV` chip sets `active`,
  clears the query, and scrolls `main` to top.
- Command rows and FAQ rows force-open while searching so the matched body is
  visible without a click.

## Static-content discipline

- Command/FAQ copy mirrors `agent-pack/commands/` and `apps/cli/squirrel`; it is
  authored data, not generated, and must be updated when those commands change.
- `Cmd` renders a copy-able monospace chip (`select-all`).

## Constraints

- No backend calls — the page must render fully offline / before any vault is
  configured.
- Search is purely client-side over in-module data; haystack strings are the
  search surface for non-text (illustration) sections.
- Accessibility: native `<details>` for collapsibles; `aria-current` on the active
  nav chip; labeled search input.

## Key Decisions

- **Static page data over a fetched/markdown doc** — the guide must work with no
  vault and no server state, and ships deterministically with the build.
- **One `hit()` predicate for all sections** — a single search semantics across
  heterogeneous content (commands, concepts, FAQ, illustrations) via per-section
  haystacks.
- **Section-at-a-time when idle, all-sections when searching** — keeps the page
  scannable normally but makes search exhaustive.

## Out of Scope

- URL-routed subsections, localization, server-driven or editable content.
