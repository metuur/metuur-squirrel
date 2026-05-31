# Desktop Theme Architecture — High-Level Design

> **Status:** Draft — pending lock
> **Date:** 2026-05-31
> **Slug:** `desktop-theme-architecture`

## Overview

Reskin the Tauri desktop popup (`apps/desktop`) with the "paper-indigo" visual
language drafted in `.devlocal/javier/new-ui-proposal/code.html`, and at the
same time stand up the structural foundation for future UI restyles. The work
extracts design tokens and component recipes (`.card`, `.btn`, `.chip`,
`.stripe-*`, etc.) into a new shared workspace package
`@squirrel/design-system`, switches the popup to consume it via a
`data-theme="paper-indigo"` attribute, bundles three variable fonts locally,
and rewrites every popup component's `className` strings so all color and type
references resolve through the new tokens.

The component **trees**, the data plane (FastAPI backend, Tauri Rust
commands), and the existing behavior of the popup do not change. This is a
visual + design-system change only.

## Stakeholders & Impact

**Primary user:** Javier (single-user ADHD productivity tool). The current
v0.5 blue/slate web-UI parity look is utilitarian and generic; the warm-paper
palette + editorial type pair (Manrope / JetBrains Mono / Fraunces) is
intended to reduce visual noise and make the morning glance at "Today's
Focus" feel calmer and more deliberate. Tactile button presses and orchestrated
entrance animations replace the flat React-on-Tailwind feel.

**Secondary consumer (out of scope for visible change):** The web SPA at
`apps/backend/app/index.html` currently hand-codes an inline Tailwind theme.
Long-term, both surfaces should share one design language. This change creates
the shared package so the web UI can adopt it later — but the web UI is
explicitly **not refactored** in this change.

**Operators / other systems:** None affected.

## Goals

What must be observable/true when this ships:

1. Opening the Squirrel popup on macOS renders the paper-indigo palette: warm
   paper background with a subtle dot grid, white card surfaces, indigo
   accent, refined cardinal red / amber / emerald for status states.
2. The header, focus card, deadline cards, and footer match the visual
   structure of `.devlocal/javier/new-ui-proposal/code.html` (within
   reasonable tolerance — pixel-perfect is not required).
3. Buttons sink 2 px into the surface on press (70 ms tactile feedback),
   respecting `prefers-reduced-motion`.
4. Manrope is the body font, JetBrains Mono is used for slugs/dates/chips,
   Fraunces is reserved for editorial accents — all loaded from local woff2
   files in `apps/desktop/public/fonts/`, no remote font requests.
5. Design tokens (colors, fonts, shadows) and component recipes (`.card`,
   `.btn`, `.chip`, etc.) live in `packages/design-system/` and are consumed
   by `apps/desktop` via a workspace dependency.
6. Switching themes is a CSS-only change: future themes drop a new file into
   `packages/design-system/themes/` and flip the `<html data-theme>`
   attribute. No component code needs to change.

## Non-Goals

What must NOT change:

- **Component structure.** Every existing React component keeps the same JSX
  tree, props, state, hooks, and behavior. Only `className` strings (and a
  few SVG icon swaps where the new design uses different glyphs) change.
- **Data plane.** FastAPI backend, `/api/home` shape, Tauri Rust commands,
  notifications, deep-linking — all untouched.
- **Web SPA.** `apps/backend/app/index.html` is not modified. It will keep
  its current v0.5 inline theme until a separate change migrates it.
- **CSP.** `tauri.conf.json` security configuration stays as-is. No remote
  font CDNs, no remote scripts. Local fonts only.
- **Dark mode design.** A working dark theme is not delivered here. The
  `.dark` class hook remains and `color-scheme: dark` is preserved so form
  controls don't break under `prefers-color-scheme: dark`, but the visual
  tokens for dark are not redesigned in this change.
- **ESLint enforcement.** No `no-restricted-syntax` rule is added in this
  change to forbid raw color names. The discipline is documented but not
  mechanically enforced yet.
- **Tailwind major version migration.** Stays on v4 via `@tailwindcss/vite`.

## Success Criteria

How we know this is done — observable outcomes only:

1. `pnpm -F @squirrel/desktop dev` launches the popup with the paper-indigo
   look. A side-by-side visual comparison against
   `.devlocal/javier/new-ui-proposal/code.html` reads as the same design.
2. `grep -r "slate-\|bg-background-\|text-slate-\|border-slate-" apps/desktop/src/`
   returns no matches (raw web-UI-parity color names are gone from
   components).
3. The new package `packages/design-system/` exists, is added to
   `pnpm-workspace.yaml`, exports a single CSS entrypoint, and is listed in
   `apps/desktop/package.json` as a workspace dependency.
4. `apps/desktop/public/fonts/` contains three variable woff2 files
   (Manrope, JetBrains Mono, Fraunces) and the browser DevTools Network
   panel shows them loading from same-origin, never from
   `fonts.googleapis.com`.
5. `apps/desktop/index.html` sets `<html data-theme="paper-indigo">` and the
   page renders correctly. Removing the attribute (manually in DevTools)
   leaves the page unstyled by theme tokens (proves the attribute is what
   activates the theme, not a hidden default).
6. `pnpm -F @squirrel/desktop test` passes — the existing
   `DeadlinesWidget.test.tsx` suite still works (a token rename must not
   break component behavior).
7. With macOS "Reduce Motion" enabled (System Settings → Accessibility),
   the `.settle` entrance animation and `.notif-badge` pulse do not run.
