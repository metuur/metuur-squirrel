# Desktop Theme Architecture — EARS Specifications

> **Status:** Draft — pending lock
> **Date:** 2026-05-31
> **Slug:** `desktop-theme-architecture`
> **Companion docs:** `docs/hld/desktop-theme-architecture.md`, `docs/lld/desktop-theme-architecture.md`

Behavioral requirements for the paper-indigo reskin and the
`@squirrel/design-system` shared package. Each unit groups requirements
that can be implemented and verified independently.

---

## Unit 1: Shared design-system package

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL include a workspace package at `packages/design-system/` whose `package.json` declares the name `@squirrel/design-system`, type `module`, and a `main`/`exports` field pointing to `src/index.css`. |
| R-1.2 | THE SYSTEM SHALL list `packages/*` in `pnpm-workspace.yaml` alongside the existing `apps/desktop` and `apps/backend/app` entries. |
| R-1.3 | THE SYSTEM SHALL declare `@squirrel/design-system` as a `workspace:*` dependency in `apps/desktop/package.json`. |
| R-1.4 | THE SYSTEM SHALL expose a single public CSS entry (`packages/design-system/src/index.css`) which imports `tailwindcss`, `./tokens.css`, the active theme file, `./primitives.css`, and `./recipes.css` in that order. |
| R-1.5 | THE SYSTEM SHALL organize CSS imports inside Tailwind v4 cascade layers `theme`, `primitives`, and `components` such that theme tokens win over recipe defaults and recipes win over later utility one-offs. |
| R-1.6 | IF the design-system package is imported but no `data-theme` attribute is set on `<html>`, THE SYSTEM SHALL still render readable defaults sourced from the canonical `@theme` block in `tokens.css`. |
| R-1.7 | WHEN `pnpm install` runs at the repo root, THE SYSTEM SHALL resolve `@squirrel/design-system` from the workspace (no remote registry fetch). |

## Unit 2: Token contract

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL define color tokens with the names `--color-bg`, `--color-surface`, `--color-surface-2`, `--color-focus-tint`, `--color-focus-edge`, `--color-ink`, `--color-ink-2`, `--color-ink-3`, `--color-ink-4`, `--color-hairline`, `--color-hairline-2`, `--color-accent`, `--color-critical`, `--color-critical-bg`, `--color-warning`, `--color-warning-bg`, and `--color-ok`. |
| R-2.2 | THE SYSTEM SHALL define type tokens `--font-sans`, `--font-mono`, and `--font-serif` resolving to Manrope, JetBrains Mono, and Fraunces respectively, each with appropriate system-font fallbacks. |
| R-2.3 | THE SYSTEM SHALL define shadow tokens `--shadow-1` (panel) and `--shadow-card` (card) as multi-layer rgba composites at the `:root` level. |
| R-2.4 | WHERE Tailwind v4's `@theme` directive is used to declare color and font tokens, THE SYSTEM SHALL generate corresponding utility classes (e.g. `bg-surface`, `text-ink-3`, `border-hairline`, `font-mono`) for use in component `className` strings. |
| R-2.5 | THE SYSTEM SHALL NOT introduce any token names with raw color words (`blue`, `red`, `slate`, etc.). All color tokens use semantic names. |

## Unit 3: Theme `paper-indigo`

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL ship a theme file at `packages/design-system/src/themes/paper-indigo.css`. |
| R-3.2 | WHEN the `<html>` element has attribute `data-theme="paper-indigo"`, THE SYSTEM SHALL apply the paper-indigo color values to all `--color-*` tokens by overriding them under the `[data-theme="paper-indigo"]` selector. |
| R-3.3 | THE SYSTEM SHALL set `--color-bg` to `#F4F2EE`, `--color-surface` to `#FFFFFF`, `--color-ink` to `#0E1116`, `--color-accent` to `#1F3A8A`, `--color-critical` to `#C8362A`, `--color-warning` to `#C56A14`, and `--color-ok` to `#2F6B4F` under the `paper-indigo` theme (full palette per `code.html` lines 18-46). |
| R-3.4 | THE SYSTEM SHALL declare `paper-indigo` as the default theme by setting `data-theme="paper-indigo"` on the `<html>` element in `apps/desktop/index.html`. |
| R-3.5 | THE SYSTEM SHALL NOT ship any second theme file (`v05-blue`, `paper-indigo-dark`, etc.) in this change. |

## Unit 4: Local font bundling (via `@fontsource-variable/*` npm packages)

> **Implementation note:** R-4.1, R-4.2, and R-4.5 were updated during
> story 4.1 to reflect the npm-package bundling approach (LLD D6). See
> commit history for the prior `public/fonts/` formulation.

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL declare three font dependencies on `@squirrel/design-system`: `@fontsource-variable/manrope`, `@fontsource-variable/jetbrains-mono`, `@fontsource-variable/fraunces`. |
| R-4.2 | THE SYSTEM SHALL import each package's CSS shim from `packages/design-system/src/primitives.css` so the `@font-face` rules they ship are included in the bundle. The design-system's own `@font-face` block (if any) SHALL list `local(...)` before any URL source so installed copies on the user's machine are preferred. |
| R-4.3 | IF the npm font packages are absent (broken install) or the bundled woff2 files fail to load at runtime, THE SYSTEM SHALL still render the popup using the system-font fallback chain declared in `--font-sans`, `--font-mono`, `--font-serif`. |
| R-4.4 | THE SYSTEM SHALL NOT request any font from a remote origin. WHEN the popup loads, the browser DevTools Network panel SHALL show font requests only to the app's own origin (Vite emits them under `dist/assets/<hash>.woff2`). |
| R-4.5 | WHERE the Tauri build packages the app for distribution, THE SYSTEM SHALL include the variable woff2 files in the final bundle. Vite resolves the `url(...)` references inside each `@fontsource-variable/*` CSS shim and emits the woff2 into `dist/assets/`. |

## Unit 5: Body chrome and primitives

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL paint `<body>` with the dot-grid background: `radial-gradient(rgba(14,17,22,0.045) 1px, transparent 1.2px)` at `background-size: 18px 18px`. |
| R-5.2 | THE SYSTEM SHALL apply `var(--font-sans)` as the inherited font-family on `<html>`, `<body>`, and `#root`. |
| R-5.3 | THE SYSTEM SHALL apply font-feature-settings `"ss01", "ss02", "cv11"` to body text. |
| R-5.4 | THE SYSTEM SHALL provide a `.accent-line` class that renders a 2 px horizontal gradient strip (indigo accent at 18-22% of width, transparent elsewhere). |

## Unit 6: Component recipe classes

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE SYSTEM SHALL provide a `.panel` class with `border-radius: 14px`, 1 px hairline border, and `var(--shadow-1)`. |
| R-6.2 | THE SYSTEM SHALL provide a `.card` class with `border-radius: 10px`, 1 px hairline border, and `var(--shadow-card)`. |
| R-6.3 | THE SYSTEM SHALL provide a `.card-focus` class with the indigo-tint linear gradient background and `var(--color-focus-edge)` border. |
| R-6.4 | THE SYSTEM SHALL provide `.stripe`, `.stripe-critical`, `.stripe-warning`, and `.stripe-ok` modifier classes that render a 3 px-wide vertical rail on the card's left edge via a `::before` pseudo-element, colored by `--color-critical`, `--color-warning`, or `--color-ok` respectively. |
| R-6.5 | THE SYSTEM SHALL provide a `.btn` class with the tactile-press behavior: 2 px offset shadow at rest, `transform: translate(2px, 2px)` with collapsed shadow on `:active`, transitions clamped to 70 ms. |
| R-6.6 | THE SYSTEM SHALL provide a `.btn-primary` variant (indigo accent outlined) and a `.btn-ghost` variant (transparent, no shadow). |
| R-6.7 | WHEN a `.btn` receives keyboard focus, THE SYSTEM SHALL render a 3 px indigo focus ring without removing the offset shadow. |
| R-6.8 | THE SYSTEM SHALL provide a `.chip` class plus `.chip-am`, `.chip-critical`, `.chip-warning`, `.chip-count` variants using `var(--font-mono)`, 10 px font size, and `font-variant-numeric: tabular-nums`. |
| R-6.9 | THE SYSTEM SHALL provide `.eyebrow`, `.slug`, `.title`, `.label`, `.tabular`, and `.date-numeral` typography helpers as documented in the proposal. |
| R-6.10 | THE SYSTEM SHALL provide `.icon-btn` and `.notif-badge` recipes for the header bell button + count badge. |
| R-6.11 | THE SYSTEM SHALL provide a `.quick-action` pill recipe used by the focus card's "Today (AM): Change · Clear" action row. |

## Unit 7: Motion + accessibility

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL provide a `.settle` entrance animation (420 ms cubic-bezier(.22,.7,.28,1)) with stagger helpers `.d1` through `.d5` (40 / 110 / 180 / 240 / 300 ms delays). |
| R-7.2 | THE SYSTEM SHALL provide a `pulse-soft` keyframe used by `.notif-badge` (2.4 s ease-in-out infinite). |
| R-7.3 | WHEN the user has `prefers-reduced-motion: reduce`, THE SYSTEM SHALL disable the `.settle` animation, the `.notif-badge` pulse, and all `.btn` transitions. |
| R-7.4 | WHEN the user has `prefers-color-scheme: dark`, THE SYSTEM SHALL preserve the `.dark { color-scheme: dark }` declaration so native form controls render dark, even though no dark-theme tokens are delivered in this change. |

## Unit 8: Component className rewrites

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | THE SYSTEM SHALL rewrite `App.tsx` so the root `<main>` uses `bg-bg text-ink` (or no color classes, since `body` paints `--color-bg`), the header uses `.panel`-derived structure with `.icon-btn` for the bell + size toggle, and the footer uses `.btn-primary` for the capture button + `.btn` for "Open Web UI" / "Close". |
| R-8.2 | THE SYSTEM SHALL rewrite `FocusWidget.tsx` so the active focus card uses the `.card-focus` recipe with an `.chip chip-am` chip and `.slug` + `.title` typography for project + task text. |
| R-8.3 | THE SYSTEM SHALL rewrite `DeadlinesWidget.tsx` so each deadline card uses `.card .stripe .stripe-<level>` where `<level>` maps `critical` → `stripe-critical`, `urgent` and `soon` → `stripe-warning`, and `upcoming`/`eventual`/`lurking` → `stripe-ok`. The card body uses `.slug` + `.title` typography and `chip chip-critical` / `chip chip-warning` for the overdue badge. |
| R-8.4 | THE SYSTEM SHALL rewrite `ParakeetWidget.tsx`, `BackendStatusBanner.tsx`, `CaptureButton.tsx`, `CaptureModal.tsx`, `CloseWindowButton.tsx`, `FocusPickerModal.tsx`, `NotificationCenter.tsx`, `OpenWebUIButton.tsx`, `ProjectSelector.tsx`, `SizeToggle.tsx`, and `Toast.tsx` so every color reference resolves to a semantic token (no `slate-*`, no `background-*`, no `bg-blue-*`, no `text-red-*`). |
| R-8.5 | IF a component currently uses a `dark:` Tailwind variant, THE SYSTEM SHALL remove that variant in this change (dark theme is out of scope; leaving stale variants would mis-render under `prefers-color-scheme: dark`). |
| R-8.6 | THE SYSTEM SHALL NOT change the React component tree shape, props, hook usage, state machines, or event handlers of any rewritten component. |
| R-8.7 | WHEN `pnpm -F @squirrel/desktop test` runs, THE SYSTEM SHALL pass the existing `DeadlinesWidget.test.tsx` suite without modification to test code. |

## Unit 9: Non-regression

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | THE SYSTEM SHALL preserve the existing Tauri Content-Security-Policy verbatim. THE SYSTEM SHALL NOT add `font-src`, `style-src` remote allowances, or any `unsafe-eval` directives. |
| R-9.2 | THE SYSTEM SHALL NOT modify `apps/backend/`, `apps/desktop/src-tauri/`, or `apps/cli/`. |
| R-9.3 | THE SYSTEM SHALL NOT modify `apps/backend/app/index.html` or any file under `apps/backend/app/` other than possibly removing dead references to design-system imports — but in this change, no such imports are added. |
| R-9.4 | WHEN the popup opens after this change ships, THE SYSTEM SHALL render the same data, deep-links, notifications, focus picks, deadlines, and capture flows as before — only the visual presentation changes. |
| R-9.5 | THE SYSTEM SHALL NOT add an ESLint rule forbidding raw color names in this change. |
