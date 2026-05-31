# Desktop Theme Architecture — Low-Level Design

> **Status:** Draft — pending lock
> **Date:** 2026-05-31
> **Slug:** `desktop-theme-architecture`
> **Companion docs:** `docs/hld/desktop-theme-architecture.md`, `docs/ears/desktop-theme-architecture.md`

## Architecture

### Package layout

```
squirrel/
├── apps/
│   └── desktop/
│       ├── src/
│       │   ├── index.css                       ← rewritten (thin wrapper)
│       │   ├── App.tsx                         ← className rewrites
│       │   └── components/
│       │       ├── BackendStatusBanner.tsx     ← className rewrites
│       │       ├── CaptureButton.tsx           ← className rewrites
│       │       ├── CaptureModal.tsx            ← className rewrites
│       │       ├── CloseWindowButton.tsx       ← className rewrites
│       │       ├── DeadlinesWidget.tsx         ← className rewrites
│       │       ├── FocusPickerModal.tsx        ← className rewrites
│       │       ├── FocusWidget.tsx             ← className rewrites
│       │       ├── NotificationCenter.tsx      ← className rewrites
│       │       ├── OpenWebUIButton.tsx         ← className rewrites
│       │       ├── ParakeetWidget.tsx          ← className rewrites
│       │       ├── ProjectSelector.tsx         ← className rewrites
│       │       ├── SizeToggle.tsx              ← className rewrites
│       │       └── Toast.tsx                   ← className rewrites
│       ├── index.html                          ← <html data-theme="paper-indigo">
│       └── package.json                        ← add @squirrel/design-system dep
├── packages/                                   ← NEW workspace folder
│   └── design-system/                          ← NEW package
│       ├── package.json                        ← name @squirrel/design-system
│       ├── src/
│       │   ├── index.css                       ← public entry (imports below)
│       │   ├── tokens.css                      ← @theme block — Tailwind v4 tokens
│       │   ├── recipes.css                     ← .panel .card .btn .chip etc.
│       │   ├── primitives.css                  ← @fontsource imports + body, dot grid, accent-line, motion
│       │   └── themes/
│       │       └── paper-indigo.css            ← [data-theme="paper-indigo"] vars
│       ├── package.json                        ← deps: @fontsource-variable/{manrope,jetbrains-mono,fraunces}
│       └── README.md                           ← usage + theme-authoring guide
└── pnpm-workspace.yaml                         ← add "packages/*"
```

### CSS layer order

The shared package uses Tailwind v4's explicit cascade layers. `index.css`
imports everything in this order so theme tokens win over recipe defaults,
and recipes win over utility one-offs:

```
@import "tailwindcss";
@layer theme        { @import "./tokens.css";              }
@layer theme        { @import "./themes/paper-indigo.css"; }
@layer primitives   { @import "./primitives.css";          }
@layer components   { @import "./recipes.css";             }
```

`apps/desktop/src/index.css` becomes a one-liner:

```css
@import "@squirrel/design-system";
```

### Token contract

Tokens in `tokens.css` use Tailwind v4's `@theme { ... }` directive so they
both produce CSS custom properties **and** generate utility classes
(`bg-surface`, `text-ink-3`, `border-hairline`, `text-accent`, etc.).

Themes override the **same CSS custom property names** under a scoped
selector. The utility classes Tailwind generates always resolve through
`var(--color-*)` at runtime, so a `data-theme` swap re-paints utilities
without rebuilding.

```css
/* tokens.css — canonical names + Tailwind utility generation */
@theme {
  --color-bg: #F4F2EE;
  --color-surface: #FFFFFF;
  --color-ink: #0E1116;
  --color-accent: #1F3A8A;
  /* …full set per HLD goal #1 */
}

/* themes/paper-indigo.css — concrete values for this theme */
[data-theme="paper-indigo"] {
  --color-bg: #F4F2EE;
  --color-surface: #FFFFFF;
  --color-ink: #0E1116;
  --color-accent: #1F3A8A;
  /* …same names, theme-specific values */
}
```

The `@theme` block carries the same defaults as `paper-indigo` so that even
if the `data-theme` attribute is removed, the popup still renders with
sensible colors (graceful degradation, not silent breakage).

### Theme activation

`apps/desktop/index.html` sets the attribute statically:

```html
<html lang="en" data-theme="paper-indigo">
```

No JavaScript theme switcher is delivered in this change. A future change
will read a stored preference via `@tauri-apps/plugin-store` and set the
attribute in `main.tsx` before React mounts.

### Font loading

Fonts ship via the `@fontsource-variable/*` npm packages — the de-facto
standard for self-hosting Google Fonts in a build pipeline:

- `@fontsource-variable/manrope`
- `@fontsource-variable/jetbrains-mono`
- `@fontsource-variable/fraunces`

These are declared as dependencies of `@squirrel/design-system` so any app
that imports the design-system gets the fonts transitively. Each package
ships a variable woff2 file plus a small CSS shim that declares the
`@font-face` rule pointing at the file inside the package:

```css
/* From @fontsource-variable/manrope/index.css (illustrative) */
@font-face {
  font-family: "Manrope Variable";
  font-style: normal;
  font-display: swap;
  font-weight: 200 800;
  src: url("./files/manrope-latin-wght-normal.woff2") format("woff2-variations");
}
```

`primitives.css` imports these CSS shims, and our own `@font-face` block
adds `local()` fallbacks against the `--font-sans/-mono/-serif` token
stacks so any system-installed copy is preferred over the network read.

Vite resolves the `url("./files/*.woff2")` references at build time and
emits the files into `dist/assets/<hash>.woff2`. At runtime the Tauri
webview serves them from the same origin, so the existing CSP
(`default-src 'self'`) covers font loads without any additional
`font-src` directive.

**Why npm packages instead of committing files to `public/fonts/`:**
versioning is pinned via package.json, no binary blobs in git, Vite
handles cache-busting hashes, and upgrades are a single `pnpm up` away.
The trade-off is one layer of indirection over which exact font bytes
ship — acceptable for a single-user app.

### Component rewrite mapping

A small, mechanical remap table is the contract every component edit follows.
Engineers apply this table — no creative decisions during the rewrite:

| Old (slate / generic Tailwind)          | New (semantic, theme-aware)                                |
|-----------------------------------------|------------------------------------------------------------|
| `bg-background-light`                   | (delete — body already paints `--color-bg`)                |
| `bg-white` / `bg-surface-light`         | `bg-surface`                                               |
| `bg-slate-50` / `bg-slate-50/60`        | `bg-surface-2`                                             |
| `text-slate-900` / `text-slate-100`     | `text-ink`                                                 |
| `text-slate-700` / `text-slate-600`     | `text-ink-2`                                               |
| `text-slate-500` / `text-slate-400`     | `text-ink-3`                                               |
| `text-slate-400` (faintest)             | `text-ink-4`                                               |
| `border-slate-200` / `border-slate-700` | `border-hairline`                                          |
| `bg-amber-400` (badge)                  | (keep as inline style — accent yellow, theme-independent)  |
| `text-blue-600` / `bg-blue-500`         | `text-accent` / `bg-accent`                                |
| `text-red-*` (overdue)                  | wrap in `chip chip-critical` (component class)             |
| `text-amber-*` / `text-orange-*`        | wrap in `chip chip-warning`                                |
| `text-emerald-*` / `text-green-*`       | wrap in `chip chip-ok` or `stripe-ok`                      |
| `dark:` variants                        | **Remove entirely** — dark mode is out of scope; leaving   |
|                                         | them would render incorrectly under `prefers-color-scheme` |

For groups of related elements (a deadline card with stripe + slug + title +
chip + action buttons), prefer the **named recipe class** (`<article
className="card stripe stripe-critical">`) over reassembling utilities every
time. Raw Tailwind utilities remain available for layout (`flex`, `gap-2`,
`px-4`, `justify-between`).

## Constraints

1. **Tauri CSP** — `default-src 'self'; script-src 'self'; style-src 'self'
   'unsafe-inline'; img-src 'self' data:`. No remote scripts, no remote
   styles, no remote fonts. Tailwind CDN script and Google Fonts `<link>`
   from the original `code.html` are explicitly forbidden.
2. **Tailwind v4** is already installed via `@tailwindcss/vite`. The
   `@theme` directive is the only supported way to generate utility classes
   from custom tokens. Variables declared in plain `:root {}` blocks do
   **not** generate utilities.
3. **`@layer` ordering matters.** Tailwind's own utility layer must load
   first (`@import "tailwindcss"` at the top); theme tokens must load before
   recipes; recipes must load before any utility one-off so utilities win
   on tie-breaks.
4. **No font CDN.** All three fonts ship via `@fontsource-variable/*` npm
   packages declared as dependencies of `@squirrel/design-system`. Vite
   resolves their CSS shims and emits the variable woff2 files into
   `dist/assets/<hash>.woff2` — same-origin at runtime, so the existing
   CSP covers them without a `font-src` directive. Approximate budget:
   ~200 KB total across the three weights.
5. **Single-platform first.** macOS is the only target this change is
   verified against. Windows / Linux Tauri builds may render fonts and
   shadows differently — acceptable for now.
6. **No behavioral change.** Existing tests (`DeadlinesWidget.test.tsx`)
   must continue to pass without modification. If a test depends on a
   color class name, that's the test that needs fixing — not a sign that
   the rewrite changed behavior.
7. **Workspace topology.** `pnpm-workspace.yaml` currently lists
   `apps/desktop` and `apps/backend/app` explicitly. Switching to
   `packages/*` plus `apps/*` is a minor edit but must be done atomically
   with the package's creation.

## Key Decisions

### D1 — Shared package is named `@squirrel/design-system`, not `@squirrel/design-tokens`

**Decision:** The new package is called `@squirrel/design-system`.

**Rationale:** It contains more than tokens — it ships component recipes
(`.card`, `.btn`, `.chip`, `.stripe-*`), font faces, motion keyframes, and
primitives (body grid, accent line). Calling it `design-tokens` would
misrepresent its scope and force a rename when recipes inevitably grow.

**Rejected:** `@squirrel/design-tokens` (too narrow), `@squirrel/ui`
(implies React components, which this package does not ship — it's CSS only
for now).

### D2 — Themes live inside the shared package, not in the consuming app

**Decision:** `packages/design-system/src/themes/paper-indigo.css` — not
`apps/desktop/src/themes/`.

**Rationale:** Themes are part of the design language, and the design
language is the package's reason to exist. Putting themes in the app would
force every consumer (current Tauri, future web SPA, future mobile) to
re-package them.

### D3 — Only one theme ships on day 1 (paper-indigo)

**Decision:** `paper-indigo` is the only theme delivered. The `data-theme`
attribute mechanism is built even though there's only one valid value.

**Rationale:** User explicitly chose 4A. Shipping a second theme as a "proof"
would double the design work without delivering user value (Javier is the
only user, and he wants paper-indigo). The attribute switch is cheap to
build and pays back the first time we add a second theme.

**Rejected:** Shipping `v05-blue` as a fallback (4B). Extra surface to
maintain for no user benefit.

### D4 — Foundation + apply, no ESLint guardrail (3B, not 3C)

**Decision:** Components are rewritten now to use the new tokens and
recipes. No `no-restricted-syntax` ESLint rule is added to forbid raw
color names.

**Rationale:** User chose 3B. Adding the lint rule has real cost
(false positives on third-party code, friction during prototyping) and the
codebase is small + single-author, so social discipline is enough for now.
If the project grows or drifts, the rule can be added as a separate change.

### D5 — Web SPA is not modified

**Decision:** The shared package is created so `apps/backend/app/index.html`
**could** consume it in the future, but this change does not touch it.

**Rationale:** User chose 2B with the explicit "do not change the WEB-ui"
qualifier. The migration of the web SPA is its own change with its own
risks (the SPA is server-rendered with a different bundling setup and
would need a build-step change to import from the workspace).

### D6 — Fonts are bundled day 1 via `@fontsource-variable/*` npm packages (5A)

**Decision:** Manrope, JetBrains Mono, Fraunces ship from day 1 via the
`@fontsource-variable/*` npm packages declared as dependencies of
`@squirrel/design-system`. Vite bundles the variable woff2 files into
`dist/assets/<hash>.woff2` at build time; runtime serves them from the
app's own origin.

**Rationale:** User chose 5A (bundle now). The editorial type pair is
core to the proposal's identity; shipping with system-font fallback would
deliver an incomplete version of the design. Bundle cost (~200 KB) is
acceptable for a desktop app where the bundle is fetched once at install.

The npm-package path was chosen over committing files to
`apps/desktop/public/fonts/` (the original draft) because: pnpm pins the
version, no binary blobs in git, Vite handles cache-busting hashes, and
upgrades are a single `pnpm up` away. Discovered during implementation
of story 4.1; LLD updated and user explicitly confirmed.

**Rejected:** Committing raw woff2 files to `apps/desktop/public/fonts/`.
Higher maintenance, requires git-tracked binaries, manual upgrade cadence.

### D7 — Dark mode is stubbed only, not designed

**Decision:** The `.dark { color-scheme: dark }` selector is preserved.
No `[data-theme="paper-indigo-dark"]` is delivered.

**Rationale:** A real dark theme is more than inverting lightness — the
warm-paper palette has no obvious dark counterpart, and choosing one is a
design decision that deserves its own LID/EARS pass. The stub prevents
broken form controls under macOS dark mode while leaving the design space
open.

### D8 — No theme switcher UI / no persistence

**Decision:** `<html data-theme="paper-indigo">` is hardcoded in
`index.html`. No setting, no menu item, no `@tauri-apps/plugin-store`
integration.

**Rationale:** Only one theme exists. A switcher would be UI for a single
option. The hardcoded attribute proves the mechanism works; the switcher
is built when (a) a second theme exists and (b) Javier actually wants to
swap.

## Out of Scope

Items explicitly deferred to future changes — each becomes its own LID/EARS
pass if/when prioritized:

1. **Web SPA migration** to consume `@squirrel/design-system`.
2. **Dark theme design** (`paper-indigo-dark` or similar).
3. **Theme switcher UI** + persisted preference via Tauri Store.
4. **ESLint `no-restricted-syntax` rule** enforcing semantic token usage.
5. **Windows / Linux visual verification.** macOS only for this change.
6. **A second theme** (`v05-blue`, `forest`, `mono`, …) — purely additive
   once D2/D3 ship.
7. **Component primitive React library.** This change ships CSS recipes,
   not React components. Wrapping `.btn`, `.chip`, etc. as `<Button>`,
   `<Chip>` React components is a separate refactor.
8. **Storybook / visual regression testing** for the design system.
9. **Backend / Tauri Rust** changes of any kind.
