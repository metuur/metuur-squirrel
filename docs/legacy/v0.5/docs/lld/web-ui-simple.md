# Web UI (Simple) — Low-Level Design

## Architecture

### Stack choice — server-rendered HTML + sprinkles of vanilla JS

The target audience (non-technical adults, ~60-year-olds) and the small surface (≈8 pages, ≈12 endpoints) make a heavy SPA stack actively wrong. The chosen stack is the simplest thing that works:

- **Server:** vanilla Python `http.server` (stdlib), same module pattern as the existing `lib/dashboard_generator.py`.
- **Templates:** Python f-strings or a tiny stdlib template helper (no Jinja, no dependencies).
- **CSS:** one hand-written stylesheet served as a static file. Mobile-first, big fonts, high contrast, dark-mode toggle via CSS variables.
- **JavaScript:** small vanilla JS (≤ 300 LoC total) inlined or served as one static file. Used for: opening the capture modal, submitting forms via fetch, toggling dark mode, swapping the vault dropdown.
- **No build step.** No `npm`, no `vite`, no `dist/`, no `package.json`.
- **No frameworks.** No React, no Vue, no htmx (htmx would be reasonable but adds a dependency that has to be vendored and learned).

### Why not React + Vite (as in the original spec)?

- Adds Node.js as a build-time dep — not the user's problem, but the maintainer's.
- Adds a `dist/` bundle in git that goes stale.
- Adds an entire dependency tree to audit and update.
- Provides exactly zero value at this surface area (12 endpoints, 8 pages, simple forms).
- Makes the codebase less approachable for the project author to maintain.

### Why not htmx?

- Reasonable choice, would simplify the JS. But: adds a third-party dependency that has to be vendored and kept current. For this size, plain JS `fetch()` calls are ≤ 50 lines.

### Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (iPad / desktop)                                            │
│  ─ HTML pages from server, plain CSS, ≈300 LoC vanilla JS            │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ HTTP, JSON for forms
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  companions/web-ui/server.py    (stdlib only, ≈800 LoC)              │
│  ─ route table                                                       │
│  ─ tiny template helper (f-strings)                                  │
│  ─ static file serving for CSS / JS / favicon                        │
│  ─ vocabulary translator (PARA → "Project lists", "intent" → "note") │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  lib/  (unchanged — already vault-aware)                             │
│  status_aggregator / deadline_scanner / intent_parser /              │
│  capture-writer (new tiny helper) / config_loader                    │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Vault (Markdown files in PARA folders, same as today)               │
└──────────────────────────────────────────────────────────────────────┘
```

The web UI is a thin presentation layer on top of `lib/`. It introduces one new helper (`lib/capture_writer.py`) for the capture endpoint and one new helper (`lib/vocabulary.py`) for translating internal terms to user-facing strings.

## Components

### New files

| Path | Purpose | Approx LoC |
|---|---|---|
| `companions/web-ui/server.py` | HTTP server, route table, request handling | 800 |
| `companions/web-ui/templates/` | One `.html` file per page (home, project, deadlines, history, note-edit, project-edit) | 8 files, ~250 LoC total |
| `companions/web-ui/static/style.css` | Single stylesheet with dark mode, mobile-first | 400 |
| `companions/web-ui/static/app.js` | Vanilla JS for modal, fetch, dark mode | 250 |
| `companions/web-ui/static/icons/` | SVG icons (no font-icon CDN) | static |
| `companions/web-ui/README.md` | How to start/stop, what's installed | 100 |
| `companions/web-ui/launchd/install.sh` | Optional macOS auto-start (mirrors `macos-reminders/`) | 60 |
| `companions/web-ui/launchd/plist.template` | LaunchAgent plist | 30 |
| `lib/vocabulary.py` | Translates internal terms to user-facing names | 80 |
| `lib/capture_writer.py` | Writes a capture file from a free-text note | 120 |
| `scripts/install-web-ui.sh` | Symlinks `squirrel web` into PATH, optionally enables launchd | 80 |
| `tests/test_vocabulary.py` | Vocabulary translation tests | 60 |
| `tests/test_capture_writer.py` | Capture write tests | 100 |
| `tests/test_web_ui_server.py` | Endpoint integration tests | 250 |

### Files touched

| Path | Change |
|---|---|
| `squirrel` CLI | Add `web` subcommand group: `start`, `stop`, `status`, `open`, `uninstall` |
| `install.sh` (TUI) | Add an optional "Web UI" step (default skip), gated by config |
| `docs/guides/getting-started.md` | New section: "Using Squirrel in a browser" |

### Files unchanged

Every `lib/*.py` except the two new helpers. Every existing slash command. Every existing skill. The vault structure.

## Pages and routes

### Pages (8)

| URL | Page | Purpose |
|---|---|---|
| `/` | Home | Today's focus, deadlines today/tomorrow, big "Add a note" button, projects list |
| `/projects/{slug}` | Project view | Project description, recent notes, deadlines for this project, edit button |
| `/projects/{slug}/edit` | Project edit | Plain textarea for the project page content |
| `/notes/{id}` | Note view | The note's text, edit button, "back to project" |
| `/notes/{id}/edit` | Note edit | Plain textarea for the note content |
| `/deadlines` | All deadlines | Grouped simply: "Today" / "This week" / "Later". No 6-level urgency taxonomy. |
| `/history` | Recent activity | Last 30 things touched, newest first |
| `/settings` | Settings (minimal) | Dark mode toggle, vault picker (if >1), about |

### JSON endpoints (8)

| Method | URL | Used by |
|---|---|---|
| `POST` | `/api/note` | Capture modal (add note) |
| `POST` | `/api/note/{id}` | Edit a note (replace body) |
| `POST` | `/api/project/{slug}` | Edit a project page (replace body) |
| `GET` | `/api/search?q=...` | Live search box |
| `GET` | `/api/parakeet` | Header "what's pressing" message |
| `POST` | `/api/vault` | Switch active vault (sets a cookie) |
| `POST` | `/api/ai/brief` | (Milestone D-AI only, gated on key) |
| `POST` | `/api/ai/decide` | (Milestone D-AI only, gated on key) |

All write endpoints accept JSON `{body, mtime}` and use the mtime concurrency check from the underlying file. On conflict the user gets a simple modal: "Someone else edited this. Show their version / Keep mine / Discard mine".

### Static routes

| URL | Serves |
|---|---|
| `/static/style.css` | The stylesheet |
| `/static/app.js` | The JS |
| `/static/icons/*.svg` | Icon assets |
| `/favicon.ico` | Favicon |

## Vocabulary translation (`lib/vocabulary.py`)

A single module that holds the mapping from internal terms to user-facing strings. Used by templates to render labels.

| Internal | User-facing |
|---|---|
| `01-Proyectos-Activos/` | "My projects" |
| `02-Areas/` | "Areas" (only used in admin) |
| `03-Recursos/` | "Reference" (only used in admin) |
| `04-Archivo/` | "Archive" (only used in admin) |
| `02-Parking-Lot/` | "On hold" |
| intent | note |
| capture | note |
| decision | "important note" or "decision" (decisions visible, but not labelled as ADRs) |
| shutdown note | "session summary" |
| frontmatter | (never shown) |
| tag (e.g., `tags: [foo]`) | "topic" (only shown as a list on project page) |
| vault | (never shown when one vault) / "workspace" (when multiple) |
| `.md` extension | (never shown) |
| project tag (e.g., `PROYECTO-A`) | the human name from the project page's title |
| urgency: `critical` | "Today" / "Overdue" |
| urgency: `urgent` | "Today" / "Tomorrow" |
| urgency: `soon` | "This week" |
| urgency: `upcoming`, `eventual`, `distant` | "Later" |

The translator is one-way: internal → user-facing. Forms accept free text; the server interprets and stores under the right internal name.

## Capture flow (the most-used path)

1. User taps "Add a note" (header button, always visible).
2. Browser shows modal with: textarea (autofocus), project picker (defaults to current project if on a project page, "Unfiled" otherwise), "Add" button.
3. User types and taps "Add".
4. Browser fetches `POST /api/note` with `{text, project_slug?}`.
5. Server resolves vault, picks project folder (or unfiled folder), generates a capture filename via existing `intent_parser` numbering rules, writes file atomically via `lib/capture_writer.py`.
6. Server returns `{success: true, id, project_slug}`.
7. Browser shows a brief "Saved" toast and closes modal.
8. The same file is now visible to Obsidian, the slash command `/sq-where-am-i`, and `squirrel status`.

If the project picker offered "Unfiled" and the user picked it, the note lands in `<vault>/99-Resources/Inbox/UNFILED-<NNN>.md`. The project author can later move it to a real project from Obsidian or by editing the file.

## Mobile / iPad considerations

- Viewport meta tag: `width=device-width, initial-scale=1`.
- Default body font: 18 px (laptop) / 20 px (tablet+).
- All tap targets ≥ 44×44 px.
- Header is fixed; "Add a note" button is reachable with thumb on iPad.
- Capture modal uses iOS-compatible `position: fixed` + safe-area insets.
- No hover-only affordances.
- Color palette has ≥ 4.5:1 contrast in both light and dark mode (WCAG AA).
- Optional: install as PWA by adding `manifest.json` (one-line; deferred to polish milestone).

## Lifecycle and binding (squirrel web subcommand)

```
squirrel web start [--port 3939] [--vault NAME] [--lan]
squirrel web stop
squirrel web status
squirrel web open
squirrel web uninstall
```

- **start**: starts server, writes PID to `~/.squirrel/web-ui.pid`, prints URL.
- **stop**: SIGTERM the PID, wait up to 5 seconds, then SIGKILL if still alive, then remove PID file.
- **status**: prints "running on http://127.0.0.1:3939" or "not running".
- **open**: starts the server if not running, then opens browser via `webbrowser` stdlib module.
- **uninstall**: stops the server, removes launchd plist if present, removes the PID file. Leaves `companions/web-ui/` source files in place (user can `rm -rf` if desired).

Binding: `127.0.0.1` by default. `--lan` binds `0.0.0.0` with a yellow stderr warning. No other binding addresses are supported.

## Optional AI proxy (Milestone D-AI)

If `~/.squirrel/config.toml` has an `[ai]` section with `provider = "anthropic"` and `api_key = "..."` (or `api_key_env = "ANTHROPIC_API_KEY"`), three buttons appear in the UI:

- "Generate brief" on a project page → calls `POST /api/ai/brief` → server reads project files, sends a templated prompt to the Anthropic API, renders the reply on screen, offers "Save as a note".
- "Help me decide" on the capture modal → multi-step wizard. User types context; AI asks clarifying questions one at a time; final result is a decision note.
- "Help me start" on the home page when nothing is in focus → AI suggests one concrete next action, drawing from the project list and recent activity.

The server side:
- Uses only `urllib.request` (stdlib) for HTTP. No `requests` dependency.
- Reads the API key from config or env. Never logs it.
- Streams the response if the Anthropic API supports it; the simple version is a single request with `max_tokens` set conservatively (≈ 2000).
- Costs are bounded by `max_tokens` and by rate-limiting: at most one in-flight AI request per browser session.

If no `[ai]` config is present, none of these buttons render. The user does not see "AI is disabled" or any hint that AI exists. The product surface is whatever the config supports.

## Constraints

### Hard

- **C1.** Python stdlib only on the backend. No `pip install`. No `requests`, no `jinja2`.
- **C2.** Python 3.9+, matching the rest of Squirrel.
- **C3.** No JavaScript build pipeline. No Node.js dependency anywhere. No `dist/` in git.
- **C4.** No third-party JS dependencies. No CDN-loaded libraries (no jQuery, no htmx, no Tailwind from CDN). One hand-written stylesheet, one hand-written JS file.
- **C5.** Localhost-only by default (`127.0.0.1`). `--lan` flag required for any other bind, with stderr warning.
- **C6.** No authentication. Mitigated by C5.
- **C7.** Atomic writes via temp file + `os.replace`.
- **C8.** mtime concurrency check on every file write.
- **C9.** No delete endpoint in v1.
- **C10.** No vault structure mutation (no creating projects, no renaming folders, no PARA reclassification).
- **C11.** WCAG 2.1 AA color contrast, 44×44 px minimum tap targets, 18 px+ default font.
- **C12.** No developer vocabulary in user-visible text (enforced by a linter check in `tests/`).
- **C13.** Optional AI features are entirely behind a config flag. Default install has no AI.

### Soft

- **C14.** First paint < 1 s on a five-year-old laptop and on iPad.
- **C15.** Total assets (HTML + CSS + JS + icons) < 100 KB.
- **C16.** Each page works with JavaScript disabled (forms degrade to standard POST). JS is sprinkles, not a requirement.
- **C17.** All error messages are in plain English, no stack traces visible to the user, no technical jargon.

## Key Decisions

### D1 — Plain HTML + vanilla JS, no React, no build pipeline

Stack chosen for: tiny surface, target audience cognitive load, maintainer simplicity, alignment with Squirrel's stdlib ethos. Rejected: React/Vite/Tailwind (the source project's stack — over-engineered for this audience), htmx (adds a vendored dep), server-side template engine (Jinja adds a dep).

### D2 — Hide every internal concept; never use developer vocabulary

Enforced by a vocabulary translator module AND a test that fails if forbidden words appear in rendered HTML. Rationale: the UI's job is to make Squirrel usable to people who don't know what a vault is.

### D3 — AI as opt-in milestone, not core

Shipping the core product without AI means: no API key dependency, no per-month cost, no privacy implications, no rate-limit failure modes in the most-used path. AI is a strict superset added later, behind a config flag.

### D4 — No file delete, no folder mutation, no sync

Three categories of operations are explicitly excluded from the UI. Each is dangerous for non-technical users (delete) or compliance-sensitive (sync) or structurally complex (folder mutation). Power users keep these in slash commands and CLI.

### D5 — Multi-vault picker only appears with >1 vault

When the user has one vault, the word "vault" / "workspace" never appears. When they have two or more, one discreet dropdown in the header lets them switch. The active vault is stored in a cookie (server-side cookies are simple to implement and survive across tabs).

### D6 — Server-side cookie for vault selection, not localStorage

Cookie is sent with every request, simplifying the server's life: the route handler always knows which vault to operate on without the client having to remember to add `?vault=` to every URL. The cookie name is `squirrel_vault`. If absent → default vault.

### D7 — Capture writes to "Unfiled" if no project picked

Better than blocking the user with a forced-choice picker. The Inbox / Unfiled folder exists already (`99-Resources/Inbox/`). User can move notes from there later, or never — they're still searchable.

### D8 — Edit textarea, not WYSIWYG

A plain textarea (raw Markdown) is the simplest editor. The audience writes prose, not structured Markdown. They will not use headings, lists, links — and that's fine. The note is still a `.md` file in the vault. Power users edit in Obsidian for the richer experience.

### D9 — Concurrency: mtime check, simple "show their version" modal on conflict

Same as the original spec, simplified UI. No diff view, no merge — just "Their version / Mine / Cancel". For this audience, simple is better than correct.

### D10 — One stylesheet, no themes

Light + dark mode via CSS custom properties. No theme system. No customization. Decision shipped: aesthetic is the project author's choice, not the user's burden.

### D11 — iPad PWA installability deferred

PWA manifest is a one-line addition but adds testing surface. Defer to a polish milestone. The site works fine as a bookmark in the meantime.

### D12 — No real-time updates, no WebSockets

Refreshing the page reloads data. For this audience, the cognitive cost of "did it update?" outweighs the savings of polling/WebSockets. Server is stateless aside from cookies; everything is GET-driven.

## Out of Scope

- Authentication, LAN, remote, multi-device
- Real-time collaboration
- File deletion
- Folder / project creation from UI
- Vault structure editing
- Markdown WYSIWYG editor
- Wiki-link autocompletion or rendering
- Tag editor or tag browser
- Frontmatter editor
- Backlinks panel
- Dataview query rendering
- Side-by-side diff, merge UI
- Keyboard shortcuts beyond browser defaults
- Multi-select bulk operations
- Native mobile app
- Custom themes / theme switcher
- WebSockets / SSE / polling for real-time updates
- AI features without explicit `[ai]` config block
- Sync-out / sync-in from UI
- GPG operations from UI
