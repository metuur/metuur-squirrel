# Desktop Theme Architecture — Tasks

Source specs: `docs/hld/desktop-theme-architecture.md`, `docs/lld/desktop-theme-architecture.md`, `docs/ears/desktop-theme-architecture.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Dependency layers:
```
1.1 (package skeleton)
 │
 ├─ 1.2 (index.css cascade-layer wiring)
 │   │
 │   ├─ 2.1 (tokens.css @theme block)            ──┐
 │   │       │                                     │
 │   │       └─ 3.1 (paper-indigo theme file)      │
 │   │            │                                │
 │   │            └─ 3.2 (html data-theme attr)    │
 │   │                                             │
 │   ├─ 4.1 (bundle woff2 fonts)                   │
 │   │       │                                     │
 │   │       └─ 5.1 (primitives.css incl. @font-face)
 │   │                                             │
 │   ├─ 6.1 (recipes: surfaces)                    │  all CSS
 │   ├─ 6.2 (recipes: stripe)                      ├─ must land
 │   ├─ 6.3 (recipes: btn family)                  │  before
 │   ├─ 6.4 (recipes: chip family)                 │  any 8.x
 │   ├─ 6.5 (recipes: typography + helpers)        │
 │   │                                             │
 │   └─ 7.1 (motion + a11y guards)                 │
 │                                                 │
 └─ 8.1 (App.tsx shell rewrite) ◄──────────────────┘
        │
        ├─ 8.2 (FocusWidget)
        ├─ 8.3 (DeadlinesWidget + stripe-level map)
        ├─ 8.4 (small components batch)
        └─ 8.5 (modals + overlays batch)
              │
              └─ 9.1 (regression sweep)
                  │
                  └─ 9.2 (visual diff + reduced-motion + CSP check)
```

---

## Unit 1: Shared design-system package

- [x] **1.1** Scaffold `packages/design-system/` workspace package (est: ~25m)
  - acceptance:
    - R-1.1 — `packages/design-system/package.json` declares `name: "@squirrel/design-system"`, `type: "module"`, `version: "0.1.0"`, and `exports: { ".": "./src/index.css" }`.
    - R-1.2 — `pnpm-workspace.yaml` includes `packages/*` alongside existing `apps/*` entries.
    - R-1.3 — `apps/desktop/package.json` adds `"@squirrel/design-system": "workspace:*"` to `dependencies`.
    - R-1.7 — `pnpm install` at repo root resolves the package from the workspace.
  - verify:
    - Run `pnpm install` at repo root; confirm `apps/desktop/node_modules/@squirrel/design-system` is a symlink (or pnpm equivalent) into `packages/design-system/`.
    - Run `pnpm list -F @squirrel/desktop @squirrel/design-system` and confirm the workspace link is shown.
    - Create empty skeleton files: `src/index.css`, `src/tokens.css`, `src/primitives.css`, `src/recipes.css`, `src/themes/paper-indigo.css`, `README.md`. Each contains only a header comment for now.

- [x] **1.2** Wire `src/index.css` cascade-layer import order (deps: 1.1, est: ~15m)
  - acceptance:
    - R-1.4 — `packages/design-system/src/index.css` imports in this exact order: `tailwindcss`, then `./tokens.css`, then `./themes/paper-indigo.css`, then `./primitives.css`, then `./recipes.css`.
    - R-1.5 — Each import (except `tailwindcss`) is wrapped in the appropriate `@layer` directive (`theme`, `primitives`, `components`).
    - R-1.6 — Update `apps/desktop/src/index.css` to a single-line `@import "@squirrel/design-system";` (replacing the current v0.5 parity content).
  - verify:
    - Run `pnpm -F @squirrel/desktop build`. Build succeeds with no CSS resolution errors.
    - Inspect the built CSS bundle; confirm token vars and Tailwind utilities both appear in the output.

## Unit 2: Token contract

- [x] **2.1** Write `packages/design-system/src/tokens.css` `@theme` block (deps: 1.2, est: ~20m)
  - acceptance:
    - R-2.1 — All 17 `--color-*` token names declared: `bg, surface, surface-2, focus-tint, focus-edge, ink, ink-2, ink-3, ink-4, hairline, hairline-2, accent, critical, critical-bg, warning, warning-bg, ok`.
    - R-2.2 — `--font-sans` (Manrope stack), `--font-mono` (JetBrains Mono stack), `--font-serif` (Fraunces stack) declared with system-font fallbacks.
    - R-2.3 — `--shadow-1` and `--shadow-card` declared at `:root` (outside `@theme` — they're not utility-generating).
    - R-2.4 — Token values inside `@theme` mirror the paper-indigo defaults so the popup renders sanely even without the `data-theme` attribute.
    - R-2.5 — No raw color words in token names.
  - verify:
    - In a dev session, temporarily remove `data-theme` from `<html>`. Page still renders with paper-indigo defaults (proves R-2.4 / R-1.6 graceful degradation).
    - Inspect built CSS: classes like `.bg-surface`, `.text-ink-3`, `.border-hairline`, `.text-accent` exist and reference `var(--color-*)`.

## Unit 3: paper-indigo theme

- [x] **3.1** Write `packages/design-system/src/themes/paper-indigo.css` (deps: 2.1, est: ~15m)
  - acceptance:
    - R-3.1, R-3.2 — File exists; all overrides live under `[data-theme="paper-indigo"] { ... }`.
    - R-3.3 — Exact hex values match `code.html` lines 18-46: `--color-bg: #F4F2EE`, `--color-surface: #FFFFFF`, `--color-ink: #0E1116`, `--color-accent: #1F3A8A`, `--color-critical: #C8362A`, `--color-warning: #C56A14`, `--color-ok: #2F6B4F` (plus full set).
    - R-3.5 — No second theme file is created in this change.
  - verify:
    - `grep -c "^[[:space:]]*--color-" packages/design-system/src/themes/paper-indigo.css` returns 17.
    - DevTools → Elements → `<html>` → computed styles shows `--color-bg: #F4F2EE` when `data-theme="paper-indigo"`.

- [x] **3.2** Set `data-theme="paper-indigo"` on `<html>` in `apps/desktop/index.html` (deps: 3.1, est: ~5m)
  - acceptance:
    - R-3.4 — `<html lang="en" data-theme="paper-indigo">` in `apps/desktop/index.html`.
  - verify:
    - Open popup; DevTools shows the attribute on `<html>`. Remove it manually; tokens fall back to defaults from R-2.4 (page still readable, proves swap mechanism).

## Unit 4: Font bundling

- [x] **4.1** Install `@fontsource-variable/*` packages as design-system deps (est: ~15m)
  - acceptance:
    - R-4.1 — `packages/design-system/package.json` declares dependencies on `@fontsource-variable/manrope`, `@fontsource-variable/jetbrains-mono`, `@fontsource-variable/fraunces` (latest stable).
    - R-4.5 — Each package resolves into `node_modules` after `pnpm install` and contains at least one `.woff2` file under `files/`.
  - verify:
    - `pnpm -F @squirrel/design-system list` lists the three fontsource deps.
    - `ls packages/design-system/node_modules/@fontsource-variable/*/files/*.woff2` finds variable woff2 files for all three fonts.
    - Note: actual `@import` of the CSS shims happens in story 5.1 (primitives.css).

## Unit 5: Primitives (body chrome + @font-face)

- [x] **5.1** Write `packages/design-system/src/primitives.css` (deps: 2.1, 4.1, est: ~25m)
  - acceptance:
    - R-4.2 — `primitives.css` imports the three `@fontsource-variable/*` CSS shims (one each for Manrope, JetBrains Mono, Fraunces). Each shim ships its own `@font-face` rule with `font-display: swap` and a relative `url()` to the woff2 inside the package. Our `--font-sans/-mono/-serif` token stacks include the fontsource family name first, then `local()`-compatible system fallbacks.
    - R-4.3 — System-font fallback chain in `--font-sans` / `--font-mono` / `--font-serif` ensures rendering when the font assets fail to load.
    - R-5.1 — `body` rule paints the dot-grid: `background-image: radial-gradient(rgba(14,17,22,0.045) 1px, transparent 1.2px)`, `background-size: 18px 18px`, `background-position: 0 0`.
    - R-5.2 — `html, body, #root` set `font-family: var(--font-sans)`, `height: 100%`, `margin: 0`, `background: var(--color-bg)`, `color: var(--color-ink)`.
    - R-5.3 — `font-feature-settings: "ss01", "ss02", "cv11"` applied to body.
    - R-5.4 — `.accent-line` class produces the 2 px indigo gradient strip (transparent → accent 18-22% → transparent).
  - verify:
    - Open popup; DevTools Network panel shows the variable woff2 requests to same-origin `/assets/*.woff2`, status 200.
    - Visual: body shows the subtle dot grid and warm-paper background.
    - Zero network requests to `fonts.googleapis.com` or any remote origin.

## Unit 6: Component recipes

- [x] **6.1** Write surfaces: `.panel`, `.card`, `.card-focus` (deps: 2.1, est: ~20m)
  - acceptance:
    - R-6.1 — `.panel`: `border-radius: 14px`, 1 px `var(--color-hairline)` border, `box-shadow: var(--shadow-1)`, `overflow: hidden`, `background: var(--color-surface)`.
    - R-6.2 — `.card`: `border-radius: 10px`, 1 px `var(--color-hairline)` border, `box-shadow: var(--shadow-card)`.
    - R-6.3 — `.card-focus`: linear-gradient indigo tint background, `border: 1px solid var(--color-focus-edge)`, `border-radius: 12px`, indigo-tinted shadow.
  - verify:
    - Inline test HTML in a `.devlocal/javier/desktop-theme-architecture-6.1/preview.html` renders the three surfaces; visually matches `code.html` lines 60-85.

- [x] **6.2** Write stripe modifier classes (deps: 6.1, est: ~10m)
  - acceptance:
    - R-6.4 — `.stripe { position: relative }` + `.stripe::before` renders a 3 px rail at `left: 0; top: 8px; bottom: 8px` with `border-radius: 0 3px 3px 0`.
    - `.stripe-critical::before { background: var(--color-critical) }`, `.stripe-warning::before { background: var(--color-warning) }`, `.stripe-ok::before { background: var(--color-ok) }`.
  - verify:
    - Manually combine `.card.stripe.stripe-critical` on a test card; visual matches `code.html` task cards (lines 495-530).

- [x] **6.3** Write button family: `.btn`, `.btn-primary`, `.btn-ghost` (deps: 2.1, est: ~25m)
  - acceptance:
    - R-6.5 — `.btn`: `2 px 2 px 0 var(--btn-shadow)` offset shadow at rest; `:active` applies `transform: translate(2px, 2px)` and collapses shadow to `0 0 0 0`. Transitions clamped to 70 ms for `transform` + `box-shadow`, 120 ms for `background`.
    - R-6.6 — `.btn-primary`: indigo border + indigo text on surface bg (NOT a solid black block). `.btn-ghost`: transparent, no shadow, ink-3 text, hover lightens.
    - R-6.7 — `:focus-visible` ring: `0 0 0 3px rgba(31, 58, 138, 0.35)` composited with the offset shadow at rest, and replacing it on `:active`.
  - verify:
    - Tab into a `.btn` in the popup; indigo ring visible. Press space; button visibly sinks 2 px and ring reappears at the pressed position.
    - `.devlocal/javier/desktop-theme-architecture-6.3/preview.html` shows all three variants with hover + focus + active states.

- [x] **6.4** Write chip family: `.chip`, `.chip-am`, `.chip-critical`, `.chip-warning`, `.chip-count` (deps: 2.1, est: ~15m)
  - acceptance:
    - R-6.8 — Base `.chip` uses `var(--font-mono)`, 10 px, 600 weight, `font-variant-numeric: tabular-nums`, `padding: 3px 8px 3px 7px`, `border-radius: 6px`.
    - Each variant sets background + border + color to the matching `--color-*-bg` / `--color-*` token pair.
  - verify:
    - Render all four chips side-by-side in the preview file; visual matches `code.html` lines 222-256.

- [x] **6.5** Write typography helpers + `.quick-action` + `.icon-btn` + `.notif-badge` (deps: 2.1, est: ~30m)
  - acceptance:
    - R-6.9 — `.eyebrow` (mono, 9.5 px, uppercase, 0.16em tracking), `.slug` (mono, 10.5 px), `.title` (sans, 700, -0.012em), `.label` (sans, 600, -0.005em), `.tabular` (tabular-nums), `.date-numeral` (Fraunces, 16 px, opsz 72).
    - R-6.10 — `.icon-btn`: 30 × 30 px, `border-radius: 8px`, transparent at rest, hairline border + ink-2 color on hover. `.notif-badge`: positioned absolute, amber background with dark amber text, 14 px high, font-mono 8.5 px.
    - R-6.11 — `.quick-action`: pill, sans 11.5 px 600, indigo hover background. `.quick-action .dot`: 6 px circle with 3 px shadow halo, defaults to accent color (overridable inline).
  - verify:
    - Header bell + size toggle in the popup match `code.html` (lines 415-430). Preview file shows all typography helpers next to a ruler for size verification.

## Unit 7: Motion + accessibility

- [x] **7.1** Add `.settle` entrance, `pulse-soft` badge, and a11y guards (deps: 6.5, est: ~15m)
  - acceptance:
    - R-7.1 — `@keyframes settle` (0 → 1 opacity + translateY(6px)/scale(0.995) → none) running 420 ms `cubic-bezier(.22,.7,.28,1)` both. Stagger helpers `.d1`-`.d5` with delays 40 / 110 / 180 / 240 / 300 ms.
    - R-7.2 — `@keyframes pulse-soft` matches `code.html` lines 355-358; applied to `.notif-badge` via `animation: pulse-soft 2.4s ease-in-out infinite`.
    - R-7.3 — `@media (prefers-reduced-motion: reduce)` block disables `.settle`, `.notif-badge` animation, and removes `.btn` transitions.
    - R-7.4 — `.dark { color-scheme: dark }` preserved.
  - verify:
    - Open popup with macOS "Reduce Motion" off → see settle reveal + badge pulse + tactile press. Turn "Reduce Motion" on, reload → no entrance animation, no pulse, no button press shift.
    - Toggle macOS dark mode; form controls inside the popup pick up the dark scheme (proves R-7.4).

## Unit 8: Component className rewrites

- [x] **8.1** Rewrite `App.tsx` shell (header, scrollable body shell, footer) (deps: 7.1, est: ~45m)
  - acceptance:
    - R-8.1 — `<main>` drops `bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100` (paint comes from `body`). Header uses `.panel`-style chrome (or inline equivalent) with `.icon-btn` for the bell + size toggle, `.notif-badge` for the unread count. Footer uses `.btn-primary` for the capture button and `.btn` for "Open Web UI" / "Close".
    - R-8.5 — All `dark:*` variants removed from `App.tsx`.
    - R-8.6 — JSX tree, hooks, props, state, effects unchanged.
  - verify:
    - `git diff apps/desktop/src/App.tsx` shows only className/inline-style edits and the SVG bell + size-toggle icon swaps (if needed). No imports added, no hooks added.
    - `pnpm -F @squirrel/desktop test` passes.
    - Open popup; header + footer visually match `code.html` lines 395-431 and 640-668.

- [x] **8.2** Rewrite `FocusWidget.tsx` (deps: 8.1, est: ~30m)
  - acceptance:
    - R-8.2 — Active focus card uses `.card-focus`; AM/PM chip uses `.chip chip-am` (PM gets a violet inline override per `code.html` line 472 pattern); project slug uses `.slug`; task title uses `.title`; quick-action row uses `.quick-action` with colored `.dot` per state.
    - R-8.5 / R-8.6 — Same rules as 8.1.
  - verify:
    - Compare to `code.html` lines 438-480 visually.
    - Click "Add afternoon focus" still opens the PM focus modal (behavior unchanged).

- [x] **8.3** Rewrite `DeadlinesWidget.tsx` with stripe-level mapping (deps: 8.1, est: ~50m)
  - acceptance:
    - R-8.3 — Each deadline card: `<article className="card stripe stripe-<level>">`. Mapping: `critical` → `stripe-critical`; `urgent`, `soon` → `stripe-warning`; `upcoming`, `eventual`, `lurking` → `stripe-ok`. Slug uses `.slug`, title uses `.title`, overdue badge uses `.chip chip-critical` or `.chip chip-warning`. Per-card action buttons use `.btn` with tight padding (`5px 10px`, 11 px font).
    - The section header uses `.eyebrow` + `.chip chip-count` for the count.
    - R-8.5 / R-8.6 — Same.
    - R-8.7 — `DeadlinesWidget.test.tsx` continues to pass without modification.
  - verify:
    - `pnpm -F @squirrel/desktop test` — `DeadlinesWidget.test.tsx` green.
    - Visual: pressing-section + 3 task cards match `code.html` lines 482-608.
    - Mapping table sanity check: render fixture with one card per level; stripe colors correctly distributed across the 3-color reduction.

- [x] **8.4** Rewrite small components batch: `BackendStatusBanner`, `CaptureButton`, `CloseWindowButton`, `OpenWebUIButton`, `SizeToggle`, `ParakeetWidget` (deps: 8.1, est: ~40m)
  - acceptance:
    - R-8.4 — Each file's color references resolve through semantic tokens or recipe classes. No `slate-*`, `background-*`, `bg-blue-*`, `text-red-*`, `bg-amber-400`, or raw hex (outside of recipe internals).
    - R-8.5 / R-8.6 — Same rules.
  - verify:
    - `grep -rn "slate-\|bg-background-\|text-red-\|text-blue-\|dark:" apps/desktop/src/components/{BackendStatusBanner,CaptureButton,CloseWindowButton,OpenWebUIButton,SizeToggle,ParakeetWidget}.tsx` returns nothing.

- [x] **8.5** Rewrite modals + overlays batch: `CaptureModal`, `FocusPickerModal`, `NotificationCenter`, `ProjectSelector`, `Toast` (deps: 8.1, est: ~60m)
  - acceptance:
    - R-8.4 — Same rule: semantic tokens or recipe classes only.
    - R-8.5 / R-8.6 — Same.
    - Modal backdrops use a token-aware overlay (e.g. `rgba(14,17,22,0.45)` referencing `--color-ink` numerically, or a new `--color-overlay` token added in 2.1 if it's needed — decide during the work).
  - verify:
    - Open each modal; visually inspect for consistency with the paper-indigo language (no jarring v0.5-blue artifacts).
    - `grep -rn "slate-\|bg-background-\|text-red-\|text-blue-\|dark:" apps/desktop/src/components/{CaptureModal,FocusPickerModal,NotificationCenter,ProjectSelector,Toast}.tsx` returns nothing.

## Unit 9: Regression sweep + final verification

- [ ] **9.1** Codebase sweep + automated checks (deps: 8.5, est: ~20m)
  - acceptance:
    - R-9.4 — Backend, Tauri Rust side, CLI untouched. `git diff --stat origin/main -- apps/backend apps/cli apps/desktop/src-tauri` shows no changes.
    - R-9.3 — `apps/backend/app/index.html` untouched. `git diff -- apps/backend/app/index.html` empty.
    - R-9.1 — `tauri.conf.json` security block unchanged.
    - R-9.5 — No ESLint rule added.
    - Cross-file grep: `grep -rn "slate-\|bg-background-\|text-red-\|text-blue-\|dark:" apps/desktop/src/` returns nothing.
  - verify:
    - Run all four commands above; confirm clean output.
    - `pnpm -F @squirrel/desktop test` — full suite passes.
    - `pnpm -F @squirrel/desktop build` — succeeds.

- [ ] **9.2** Visual diff + accessibility + CSP verification (deps: 9.1, est: ~30m)
  - acceptance:
    - HLD Success Criteria #1 met: popup side-by-side with `.devlocal/javier/new-ui-proposal/code.html` reads as the same design (subjective check — Javier's call).
    - R-4.4 — DevTools Network panel shows font requests only to same-origin `/fonts/*.woff2`. No `fonts.googleapis.com` requests.
    - R-7.3 — With macOS Reduce Motion enabled, `.settle` does not animate, `.notif-badge` does not pulse, `.btn` does not transition.
    - R-9.1 — Active Tauri CSP at runtime (DevTools → Application → Frames → main → Headers) matches the pre-change value byte-for-byte.
  - verify:
    - Take a screenshot of the popup; paste alongside `code.html` render in `.devlocal/javier/desktop-theme-architecture-9.2/side-by-side.png`. Approve or list visual deltas.
    - Network tab clean: zero remote font/style requests.
    - Reduce Motion toggle test passes both ways.
    - CSP byte-for-byte check passes.

---

**Total estimated effort:** ~8-10 hours of focused work. Most of it is mechanical className rewrites (Unit 8). Foundation (Units 1-7) is ~3.5 hours.

**Critical path:** 1.1 → 1.2 → 2.1 → 6.x → 8.1 → 8.3 → 9.1 → 9.2. Units 3, 4, 5, 7 can interleave with 6.x.

**Out-of-scope confirmed (do not touch in this change):** `apps/backend/`, `apps/cli/`, `apps/desktop/src-tauri/`, `apps/backend/app/index.html`, ESLint config, dark theme tokens, second theme files, theme switcher UI.
