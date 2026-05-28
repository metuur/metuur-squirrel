# Web UI (Simple) — Tasks

> Source: `docs/hld/web-ui-simple.md`, `docs/lld/web-ui-simple.md`, `docs/ears/web-ui-simple.md`.
> Arrow of intent: HLD → LLD → EARS → these tasks → code/tests.

## Cross-spec prerequisite

`multi-vault-core` MUST ship before this plan starts. The web UI calls `lib/config_loader.list_vaults()`, reads per-vault state, and uses the migrated config schema. Specifically these stories from `docs/tasks/multi-vault-core.md` must be done: **1.2, 1.3, 1.4, 1.5**.

## Conventions

- Story IDs are stable; never renumber. `(deps: X.Y)` references stories in *this* file only.
- `(mutex: tag)` marks stories that touch the same file; cannot run concurrently with same-tag stories.
- Acceptance line references R-X.Y in `docs/ears/web-ui-simple.md`.
- Verify line is the exact observable check — runnable command, file inspection, or test name.
- Private technical breakdown (sketches, prototypes, scratch notes) goes in `.devlocal/<user>/<story-id>/scratchpad.md`.

## Dependency overview

```
   1.1 server scaffold + route table
       │
       ├──► 1.2 squirrel web subcommands
       │
       ├──► 1.3 static asset serving + access log
       │
       ├──► 1.4 security headers + path traversal middleware
       │
       └──► 2.1 vocabulary module ──► 2.2 forbidden-words linter test
                                          │
                                          ▼
                                      3.1 CSS (mobile + dark + a11y)
                                      3.2 vanilla JS sprinkles
                                          │
                                          ▼
   ┌──────────────────────────────────────┴──────────────────────────────────┐
   │  Milestone B — Read-only MVP                                            │
   │                                                                         │
   │   4.1 home page          4.5 deadlines page                             │
   │   4.2 project view       4.6 history page                               │
   │   4.3 note view          4.7 settings page                              │
   │   4.4 search endpoint    4.8 parakeet endpoint                          │
   │   5.1 multi-vault cookie + picker (hides on single vault)               │
   │   6.1 installer integration (TUI step + install-web-ui.sh)              │
   │   6.2 launchd plist (macOS optional)                                    │
   └─────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  Milestone C — Capture & edit                                           │
   │                                                                         │
   │   7.1 lib/capture_writer.py                                             │
   │   7.2 POST /api/note + capture modal in UI                              │
   │   7.3 POST /api/note/{id} + POST /api/project/{slug} (edit endpoints)   │
   │   7.4 mtime concurrency check + conflict modal                          │
   │   7.5 plain-English error pages (no stack traces)                       │
   └─────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  Milestone D-AI — Optional AI proxy                                     │
   │                                                                         │
   │   8.1 [ai] config schema + key resolution                               │
   │   8.2 AI endpoints via urllib.request                                   │
   │   8.3 AI buttons (gated on config presence)                             │
   └─────────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │  Milestone E — Polish                                                   │
   │                                                                         │
   │   9.1 squirrel web uninstall                                            │
   │   9.2 performance budget verification                                   │
   │   9.3 accessibility audit (WCAG AA)                                     │
   │   9.4 PWA manifest                                                      │
   │   9.5 docs: companions/web-ui/README.md                                 │
   │   9.6 docs: user guide section "Using Squirrel in a browser"            │
   └─────────────────────────────────────────────────────────────────────────┘
```

---

## Unit 1 — Server foundation

- [x] 1.1 **Server scaffold and route table** (est: ~3h, mutex: server)
  - acceptance: R-1.1, R-1.11
  - verify: `companions/web-ui/server.py` runs via `python3 companions/web-ui/server.py --port 3939`; binds to `127.0.0.1`; serves a placeholder home page at `/`; has a documented route table dict. `python3 -c "import companions.web_ui.server"` raises no import errors. Zero non-stdlib imports (verified by `grep -E "^import|^from" server.py`).

- [x] 1.2 **`squirrel web` subcommand group** (deps: 1.1, est: ~2h, mutex: squirrel_cli)
  - acceptance: R-1.2, R-1.3, R-1.4, R-1.5, R-1.6, R-1.7, R-1.8, R-1.9
  - verify: `squirrel web start` writes `~/.squirrel/web-ui.pid` and prints URL. `squirrel web status` reports running. `squirrel web stop` removes PID file. `squirrel web open` launches browser. `--port`, `--lan`, `--vault` flags accepted. `--lan` prints stderr warning. `squirrel web uninstall` removes PID + plist (if any).

- [x] 1.3 **Static asset serving + access log** (deps: 1.1, est: ~1.5h, mutex: server)
  - acceptance: R-1.10, plus the static-routes portion of the LLD
  - verify: `GET /static/style.css`, `GET /static/app.js`, `GET /static/icons/*.svg`, `GET /favicon.ico` all return 200 with correct `Content-Type`. Access log at `~/.squirrel/web-ui.log` records `<ISO> <method> <path> <status>` lines; no request bodies, no cookie values present (grep test).

- [x] 1.4 **Security headers + path traversal middleware** (deps: 1.1, est: ~1.5h, mutex: server)
  - acceptance: R-9.1, R-9.2, R-9.3, R-9.4, R-9.5, R-9.6, R-9.7, R-9.8
  - verify: every response has `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`. Dynamic responses have `Cache-Control: no-store`. Request paths with `..` return 400. Methods other than GET/POST/OPTIONS return 405. File-touching routes resolve via `Path.resolve()` and reject paths outside vault root with 403. Tests: `tests/test_web_ui_security.py`.

---

## Unit 2 — Vocabulary

- [x] 2.1 **`lib/vocabulary.py` translator** (est: ~1h, mutex: vocabulary)
  - acceptance: R-4.1, R-4.5, R-4.6
  - verify: `tests/test_vocabulary.py` covers all mappings in the LLD vocabulary table. `translate("01-Proyectos-Activos") == "My projects"`, project tag → human title with fallback, urgency → friendly-time mapping (`critical`→"Today / Tomorrow", `soon`→"This week", etc.).

- [x] 2.2 **Forbidden-words linter test** (deps: 2.1, est: ~1.5h)
  - acceptance: R-4.2, R-4.3, R-4.4, R-4.7
  - verify: `tests/test_no_developer_vocabulary.py` instantiates the server in-process, walks every static template file plus a sample rendered response from each route, and asserts no forbidden term appears (`vault` when single-vault config, `frontmatter`, `PARA`, `intent`, `wiki-link`, `.md`, `proyecto`, `tipo`, `estado`, internal folder names, `shutdown note`, `parakeet`). With a multi-vault config, `workspace` is allowed but `vault` is still forbidden in user-visible HTML.

---

## Unit 3 — Static assets (CSS + JS)

- [x] 3.1 **`static/style.css` — mobile-first stylesheet** (est: ~3h, mutex: style)
  - acceptance: R-6.1, R-6.2, R-6.3, R-6.4, R-6.5, R-6.6, R-6.7
  - verify: stylesheet ≤ 30 KB. CSS custom properties for light + dark theme. Body font ≥ 18 px (≤ 1024 px viewport) / ≥ 20 px (tablet+). All buttons / dropdown triggers / link-as-button elements measured ≥ 44×44 px in browser inspector. WCAG 2.1 AA contrast checked via a small Python script using `colormath`-free stdlib math against the palette constants.

- [x] 3.2 **`static/app.js` — vanilla JS sprinkles** (est: ~2h, mutex: js)
  - acceptance: parts of R-2.11, R-5.1, R-5.2, R-5.3, R-6.5, R-7.4
  - verify: ≤ 300 LoC vanilla JS, no build step. Implements: capture modal open/close, fetch wrapper for POST endpoints, dark-mode toggle (writes `squirrel_theme` cookie), workspace dropdown change handler. Forms degrade to standard HTML POST when JS is disabled (R-2.11) — verified by disabling JS in browser and confirming each page still works.

---

## Unit 4 — Pages (read-only — Milestone B)

- [x] 4.1 **Home page** (deps: 1.4, 2.1, 3.1, 3.2, est: ~2.5h, mutex: pages)
  - acceptance: R-2.1, R-2.9, R-2.10, R-2.11
  - verify: `GET /` renders: today's focus block, deadlines today/tomorrow block, projects list, header "Add a note" button. First-paint < 1 s on localhost. Test: `tests/test_web_ui_home.py` asserts presence of each block in HTML.

- [x] 4.2 **Project view page** (deps: 4.1, est: ~2h, mutex: pages)
  - acceptance: R-2.2
  - verify: `GET /projects/{slug}` renders project description (from project page Markdown), list of recent notes for the project, deadlines for the project, an "Edit" button (route exists; submits to /api/project later in 7.3). Test: navigation from home page link works.

- [x] 4.3 **Note view page** (deps: 4.2, est: ~1.5h, mutex: pages)
  - acceptance: R-2.4
  - verify: `GET /notes/{id}` renders the note body, "Edit" button, "Back to project" link.

- [x] 4.4 **Search endpoint + UI hook** (deps: 4.1, est: ~2h)
  - acceptance: R-3.4
  - verify: `GET /api/search?q=...` returns JSON `[{path, title, snippet_lines: [...]}]` with up to 3 lines per hit. Header search input on home page submits to this endpoint and lists matches as links.

- [x] 4.5 **Deadlines page** (deps: 2.1, 4.1, est: ~2h, mutex: pages)
  - acceptance: R-2.6, R-3.5
  - verify: `GET /deadlines` groups items into "Today", "This week", "Later" using `lib/vocabulary` mapping from `deadline_scanner` urgency levels. `GET /api/parakeet` returns user-facing message (no developer vocabulary). Header "what's pressing" message shows the parakeet text.

- [x] 4.6 **History page** (deps: 4.1, est: ~1.5h, mutex: pages)
  - acceptance: R-2.7
  - verify: `GET /history` lists the 30 most-recently-modified items across the active workspace, newest first. Each item links to its note view.

- [x] 4.7 **Settings page** (deps: 4.1, est: ~1.5h, mutex: pages)
  - acceptance: R-2.8, R-6.5, R-6.6
  - verify: `GET /settings` renders: dark-mode toggle (writes `squirrel_theme` cookie, no-cookie path honors `prefers-color-scheme`), workspace picker (visible only when ≥2 vaults configured), "About" block with version.

---

## Unit 5 — Multi-vault awareness (Milestone B)

- [x] 5.1 **Workspace cookie + picker** (deps: 1.4, 4.1, est: ~2h)
  - acceptance: R-7.1, R-7.2, R-7.3, R-7.4, R-7.5, R-7.6
  - verify: with single-vault config: no `workspace` word and no picker anywhere in rendered HTML (assert via `test_no_developer_vocabulary.py`). With two-vault config: discreet header dropdown lists both by `name`. Selecting one POSTs to `/api/vault`, sets `squirrel_vault` cookie, page reloads, subsequent requests use the new vault. Stale cookie (vault name no longer exists) falls back to default and clears the cookie.

---

## Unit 6 — Installer integration (Milestone B)

- [x] 6.1 **Installer TUI step + `install-web-ui.sh`** (deps: 1.2, est: ~1.5h, mutex: installer)
  - acceptance: R-11.1, R-11.2, R-11.3, R-11.4, R-11.5
  - verify: `install.sh` shows a new optional step "Web UI (browser interface)" default "No". Selecting "Yes" runs `scripts/install-web-ui.sh` which prints URL and confirms no Node required. `--auto` skips this step unless `--with-web-ui` is passed.

- [x] 6.2 **Optional launchd auto-start (macOS)** (deps: 1.2, est: ~1h, mutex: installer)
  - acceptance: R-11.6, R-11.7
  - verify: `companions/web-ui/launchd/install.sh` installs `~/Library/LaunchAgents/org.squirrel.web-ui.plist`, loads it via `launchctl`, confirms server starts on next login. `--uninstall` reverses cleanly. Non-macOS hosts exit cleanly with a one-line message and no side effects.

---

## Unit 7 — Capture & edit (Milestone C)

- [x] 7.1 **`lib/capture_writer.py`** (deps: 2.1, est: ~2h)
  - acceptance: R-5.6 (helper portion)
  - verify: `tests/test_capture_writer.py` covers: `write_capture(vault_path, "PROYECTO-A", "my note")` creates `<vault>/01-Proyectos-Activos/PROYECTO-A/PROYECTO-A-CAPTURE-NNN.md` with proper frontmatter. `write_capture(vault_path, None, "my note")` creates `<vault>/99-Resources/Inbox/UNFILED-NNN.md`. Numbering increments correctly. Atomic write via temp file + `os.replace`.

- [x] 7.2 **Capture POST + modal** (deps: 7.1, 3.2, est: ~2.5h)
  - acceptance: R-3.1, R-5.1, R-5.2, R-5.3, R-5.4, R-5.5, R-5.7
  - verify: `POST /api/note` accepts `{text, project_slug?}` and calls `capture_writer`. "Add a note" button visible on every page in header. Modal autofocuses textarea, project dropdown defaults to current project or "Unfiled", "Add" submits and closes on success, "Cancel" closes. Failed write shows plain-English error and keeps modal open.

- [x] 7.3 **Edit endpoints (note + project)** (deps: 1.4, 4.3, est: ~2h)
  - acceptance: R-3.2, R-3.3, R-2.3, R-2.5
  - verify: `GET /notes/{id}/edit` and `GET /projects/{slug}/edit` render a textarea + save button. `POST /api/note/{id}` and `POST /api/project/{slug}` accept `{body, mtime}` and overwrite via `os.replace`.

- [x] 7.4 **mtime concurrency check + conflict modal** (deps: 7.3, est: ~2.5h)
  - acceptance: R-3.8, R-3.9, R-3.10, R-8.1, R-8.2, R-8.3, R-8.4, R-8.5
  - verify: every file GET includes `mtime` in response; every file POST requires `mtime`. Mismatched mtime returns 409 with `{current_body, current_mtime, message}`. UI shows modal: "Show their version" / "Keep mine" / "Cancel". Three-way merge explicitly absent in v1. Test: `tests/test_concurrency.py`.

- [x] 7.5 **Plain-English error pages** (deps: 1.4, est: ~1.5h)
  - acceptance: R-10.1, R-10.2, R-10.3, R-10.4, R-3.7
  - verify: triggering a malformed JSON POST returns 400 with `{error: "<plain English>"}`. Triggering an internal exception returns 500 page (HTML) or 500 JSON (api) — never a stack trace in response body. Stack trace appears in `~/.squirrel/web-ui.log`. Manually inspected error copy contains no "EIO", "Traceback", "stacktrace", etc.

---

## Unit 8 — Optional AI proxy (Milestone D-AI)

- [x] 8.1 **`[ai]` config schema + key resolution + gating** (est: ~1.5h)
  - acceptance: R-12.1, R-12.3, R-12.4
  - verify: when `~/.squirrel/config.toml` has no `[ai]` section, no AI-related buttons or copy render anywhere (test: render every page, grep for "AI" / "Generate brief" / "Help me"). When `[ai]` has `provider = "anthropic"` and `api_key = "..."` or `api_key_env = "ENV_NAME"`, AI buttons appear. Key value never appears in logs (grep test on `web-ui.log`).

- [x] 8.2 **AI endpoints via stdlib `urllib.request`** (deps: 8.1, est: ~3h)
  - acceptance: R-12.2 (endpoint side), R-12.5, R-12.6, R-12.7, R-12.8
  - verify: `POST /api/ai/brief`, `POST /api/ai/decide`, `POST /api/ai/start` each make one Anthropic API call via `urllib.request` (verified by `grep -E "import (httpx|requests|anthropic)" companions/web-ui/server.py` returning zero matches). `max_tokens ≤ 2000` enforced. One in-flight request per browser session (cookie-keyed lock). Network/rate-limit errors return plain-English "Try again" message.

- [x] 8.3 **AI buttons in UI** (deps: 8.2, est: ~2h)
  - acceptance: R-12.2 (UI side)
  - verify: "Generate brief" button on project page, "Help me decide" button in capture modal, "Help me start" button on home page when no focus is set. Each opens a result panel with "Save as a note" action. Buttons absent when `[ai]` config missing.

---

## Unit 9 — Polish (Milestone E)

- [x] 9.1 **`squirrel web uninstall`** (deps: 1.2, 6.2, est: ~1h, mutex: squirrel_cli)
  - acceptance: R-14.1, R-14.2, R-14.3, R-14.4
  - verify: `squirrel web uninstall` stops server, removes launchd plist if present, removes PID file. Vault untouched (mtime fingerprint pre/post). Removing `companions/web-ui/` directory entirely leaves all other squirrel commands functional (test: run `squirrel status` after `rm -rf companions/web-ui` and confirm exit 0).

- [x] 9.2 **Performance budget verification** (deps: 4.1, est: ~1.5h)
  - acceptance: R-13.1, R-13.2, R-13.3, R-13.4
  - verify: script that fetches every page route, measures HTML+CSS+JS+icons total bytes (must be ≤ 100 KB uncompressed per page). First-paint < 1 s measured via headless browser timing on localhost. No external network requests during page load (assert via inspecting HTML for any `https://` references in `<link>`, `<script>`, `<img>` tags).

- [x] 9.3 **Accessibility audit (WCAG 2.1 AA)** (deps: 3.1, 4.7, est: ~2h)
  - acceptance: R-6.4 (formal verification), other R-6.x already verified by stories above
  - verify: run an automated a11y checker (e.g., `pa11y` or `axe-core` via headless browser) against every page route in both light and dark mode. Zero failures at AA level. Manually verify focus states are visible.

- [x] 9.4 **PWA manifest (optional install on iPad)** (deps: 4.7, est: ~1h)
  - acceptance: R-15.4 (PWA portion)
  - verify: `companions/web-ui/static/manifest.json` present and linked from every page. iPad Safari → Share → Add to Home Screen → app launches as standalone. App icon present.

- [x] 9.5 **`companions/web-ui/README.md`** (deps: 6.1, 9.1, est: ~1h, mutex: docs)
  - acceptance: R-14.4
  - verify: README covers: what the companion does, how to start/stop, how to uninstall, security model (localhost-only, no auth), what's NOT in scope. Plain language, screenshots optional.

- [x] 9.6 **User guide: "Using Squirrel in a browser"** (deps: 4.1, 7.2, est: ~1.5h, mutex: docs)
  - acceptance: R-15.4 (docs portion)
  - verify: new section in `docs/guides/getting-started.md` titled "Using Squirrel in a browser" — covers: when to use it, how to install (refer to TUI), how to start/stop, how to add a note, how to switch workspace (if multiple). Written for non-technical readers (matches the existing tone of that guide).

---

## Estimates & critical path

| Milestone | Stories | Wall-clock estimate |
|---|---|---|
| Foundation | 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 3.1, 3.2 | ~16h |
| Milestone B (read-only) | 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 5.1, 6.1, 6.2 | ~18.5h |
| Milestone C (capture & edit) | 7.1, 7.2, 7.3, 7.4, 7.5 | ~10.5h |
| Milestone D-AI (optional AI) | 8.1, 8.2, 8.3 | ~6.5h |
| Milestone E (polish) | 9.1, 9.2, 9.3, 9.4, 9.5, 9.6 | ~8h |
| **Total** | **32 stories** | **~59.5h** focused dev |

Calendar at half-time: **~3 weeks** for Foundation + Milestone B (the minimum shippable). Milestone C adds another ~5 days. D-AI + E another ~5 days combined.

Minimum demoable to your wife / a 60-year-old user: **end of Milestone B** — they can browse projects, see today, see deadlines, switch workspaces, dark mode. They cannot add or edit notes yet (that's Milestone C).

## Parallelization opportunities

- 1.2, 1.3, 1.4 can run in parallel after 1.1 (different concerns, but all touch `server.py` → respect mutex tag).
- 2.1, 3.1, 3.2 are independent of each other.
- All Milestone-B page stories (4.1–4.7) can be split across people once 2.1 + 3.1 + 3.2 + 1.4 are in.
- 6.1 and 6.2 are independent.
- 8.1, 8.2, 8.3 form a strict chain within D-AI.
- 9.1, 9.5, 9.6 are independent; 9.2 + 9.3 can run in parallel after the pages exist.

## Cross-spec dependencies

Multi-vault-core stories that MUST be done first:
- 1.2 (config_loader read API) — used by 1.4, 5.1, 7.x, 8.1
- 1.3 (config_loader write API) — used by 5.1, settings page
- 1.4 (migration) — implicit on every config load
- 1.5 (per-vault state) — used by 5.1
