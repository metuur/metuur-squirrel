# Plan — Web UI + API for Squirrel (full skill parity + multi-vault)

> Planning doc only. No code changes yet. Updated 2026-05-25 to reflect two new requirements: (1) UI must provide the same functionality as Obsidian + skills so the user picks whichever interface fits, and (2) Squirrel core must support multiple vaults.
>
> Source reference: `/Users/javierbenavides/others/ai-agents/personal-initiative-tracker` (vanilla Python `http.server` + React 19 + Vite + Tailwind).

---

## Context & goal

Squirrel today has three ways to do work:

| Interface | Strength | Weakness |
|---|---|---|
| **Slash commands** in Claude Code / Codex / Cursor | Conversational, AI-augmented | Locked to one agent at a time |
| **Standalone `squirrel` CLI** | Scriptable, terminal-fast | Not visual, no editing |
| **Obsidian + vault Markdown** | Rich editing, backlinks, dataview | No skill automation, single-vault only |

The user's request: **add a 4th interface — a web UI — that has parity with Obsidian (file tree, editor, search, backlinks, tags) AND parity with every slash command (capture, brief, sync, decisions, chunking, etc.).** Users pick whichever interface fits the moment. They're not mutually exclusive — all four edit the same vault files.

**Second requirement:** support **multiple vaults** (e.g., `personal`, `work`, `client-a`). Slash commands, CLI, and the UI must all let you pick which vault to operate on. Today, `config.toml` has a single `vault_path`.

---

## Architectural shape

```
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │   Slash cmd      │  │   squirrel CLI   │  │     Obsidian     │  │     Web UI       │
   │   (Claude/Codex) │  │   (terminal)     │  │   (desktop app)  │  │   (browser)      │
   └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
            │                     │                     │                     │
            │                     │                     │                     │
            └─────────────────────┴─────────────────────┴─────────────────────┘
                                              │
                                              ▼
                              ┌──────────────────────────────┐
                              │   lib/  (Python stdlib)      │   ← all logic lives here
                              │   intent_parser              │
                              │   status_aggregator          │
                              │   deadline_scanner           │
                              │   chunk_helper               │
                              │   estimate_buffer            │
                              │   package_protocol           │
                              │   session_scanner            │
                              │   switch_tracker             │
                              │   dashboard_generator        │
                              └──────────┬───────────────────┘
                                         │
                                         ▼
                              ┌──────────────────────────────┐
                              │   Vault(s) — Markdown files  │   ← source of truth
                              │   ~/vault-tdah/              │
                              │   ~/work-vault/              │
                              │   ~/client-a-vault/          │
                              └──────────────────────────────┘
```

**Key invariant:** every interface calls the same `lib/` functions. No interface gets shortcuts; no interface has logic the others lack. Adding the web UI is a new client of `lib/`, not a new system.

---

## Guiding constraints

| Principle | Implication |
|---|---|
| **Vault is the source of truth** | API reads/writes Markdown only. Obsidian sees the same files. |
| **No Python deps** | `server.py` uses only `http.server` + stdlib. Matches `lib/`. |
| **All interfaces equal** | Anything a slash command does, the UI must do. Anything Obsidian shows, the UI must show. |
| **Multi-vault from day one** | Every operation takes a `vault` parameter. No "current vault" global. |
| **Backward-compatible config** | Existing single-vault configs auto-migrate. |
| **Localhost-only by default** | Bind `127.0.0.1`. No auth means no LAN exposure. |
| **Opt-in install** | Web UI is a companion, not a default. |

---

# Phase 0 — Multi-vault support in core Squirrel

**This is a prerequisite for the UI. It also benefits slash commands and the CLI on its own.** Could ship before the UI work even starts.

## Config schema change

Today (`~/.squirrel/config.toml`):
```toml
vault_path = "~/vault-tdah"
environment_name = "personal"
```

Proposed:
```toml
# Legacy fields kept for backward compatibility — auto-migrated on first load
vault_path = "~/vault-tdah"          # ← becomes vaults[0].path if vaults missing
environment_name = "personal"        # ← becomes vaults[0].name if vaults missing

[[vaults]]
name = "personal"
path = "~/vault-tdah"
default = true

[[vaults]]
name = "work"
path = "~/work-vault"
default = false

[[vaults]]
name = "client-a"
path = "~/clients/acme/vault"
default = false

# 'environment_name' for sync packages now refers to which env this MACHINE is.
# Vault selection is separate.
machine_environment = "personal"   # or "work" — used by sync-out/in
```

**Migration logic** (runs once, on first load by any tool):

1. If `[[vaults]]` already exists, do nothing.
2. Else if legacy `vault_path` exists, append a single vault entry:
   ```
   [[vaults]]
   name = "<environment_name or 'default'>"
   path = "<vault_path>"
   default = true
   ```
3. Move `environment_name` → `machine_environment`.
4. Write back to disk with a `# Auto-migrated <date>` comment.

## Code changes in `lib/`

Every `lib/*.py` function already takes `vault_path` as a parameter — that's good. What changes:

| File | Change |
|---|---|
| `lib/config_loader.py` (new — extract from `squirrel` CLI) | Load TOML, expand `~`, resolve `vaults` list, migrate legacy, provide `get_vault(name=None) → Vault` |
| `lib/intent_parser.py` | No change (takes a path) |
| `lib/status_aggregator.py` | No change (takes a path) |
| `lib/deadline_scanner.py` | No change |
| `lib/chunk_helper.py` | No change (vault-independent) |
| `lib/estimate_buffer.py` | No change |
| `lib/session_scanner.py` | Already loads config — update to handle new schema |
| `lib/package_protocol.py` | Reads `machine_environment` (was `environment_name`) |
| `lib/dashboard_generator.py` | Take optional `vault_name` param to title the dashboard |

## CLI changes

`squirrel` subcommands accept a `--vault NAME` flag everywhere:

```bash
squirrel status                   # default vault
squirrel status --vault work      # named vault
squirrel deadlines --vault client-a
squirrel chunk --hours 8          # vault-independent
squirrel install --agent claude   # not vault-specific
squirrel vaults list              # NEW: list configured vaults
squirrel vaults add NAME PATH     # NEW: add a vault
squirrel vaults remove NAME       # NEW: remove a vault
squirrel vaults default NAME      # NEW: change default
```

## Slash command changes

Every slash command that reads/writes the vault gains an optional `--vault NAME` arg:

```
/sq-where-am-i              # uses default
/sq-where-am-i --vault work # named
/sq-status --vault personal
/sq-brief PROYECTO-A --vault work
```

`/sq-init` becomes vault-aware:

```
/sq-init                    # first run: configures machine + first vault
/sq-init --add-vault        # subsequent: add another vault
```

State per vault: `~/.squirrel/state.json` becomes `~/.squirrel/state/<vault-name>.json`. Current active project, active intent, last switch — all per vault.

## Skills changes

Each skill's `SKILL.md` is updated to:
1. Accept an optional `vault_name` argument
2. If not given, use the default vault
3. Pass `--vault` through to its underlying script call

The skill's `find` fallback for `lib/*.py` doesn't change — that's about locating the script binary, not the vault.

---

# Phase 1 — Web UI feature scope

This is the work that brings Obsidian-like ergonomics plus skill automation into the browser.

## Obsidian-parity features

| Obsidian feature | UI implementation |
|---|---|
| File tree (folder browser) | `<VaultTree>` — collapsible tree, lazy-loaded, mirrors PARA structure |
| Open any `.md` file | `<FileEditor>` — Markdown editor + live preview pane |
| Markdown editing | Use [CodeMirror 6](https://codemirror.net/) with Markdown mode (already MIT-licensed, small bundle) |
| Live preview | `marked` (already used by source project) renders alongside |
| Backlinks panel | `<BacklinksPanel>` — `[[WIKILINK]]` references, computed by a new `lib/backlink_scanner.py` |
| Full-text search | Existing source pattern (regex over `.md`), via `GET /api/search?q=...&vault=...` |
| Tag browser | `<TagBrowser>` — group files by frontmatter `tags`, computed by `lib/tag_parser.py` (already exists!) |
| Frontmatter editing | `<FrontmatterEditor>` — form-based YAML editor (split from raw editor) |
| Dataview queries | Use the existing templates in `templates/dataview/` — render with a server-side resolver |
| Vault switcher | `<VaultSwitcher>` — dropdown in header; persists last-chosen vault in localStorage |

## Skill-parity features

Every slash command gets a UI surface. Some are simple forms; some are multi-step wizards.

| Slash command | UI implementation |
|---|---|
| `/sq-where-am-i` | `<WhereAmI>` page — auto-loads on entry, shows recommended focus per vault |
| `/sq-status` | `<Status>` page — full status aggregator output, refreshable |
| `/sq-deadlines` | `<DeadlineList>` page — grouped by urgency, click to jump to file |
| `/sq-capture` | `<CaptureForm>` modal — text area + project picker, POST `/api/capture` |
| `/sq-start` | `<SessionStart>` modal — pick project, see loading note, jump to first action |
| `/sq-end` | `<SessionEnd>` modal — fill shutdown note structure, save + suggest commit |
| `/sq-brief` | `<BriefGenerator>` page — pick project + format (short/email/all), show output, copy button |
| `/sq-decision` | `<DecisionWizard>` modal — multi-step form (context → decision → alternatives → consequences) |
| `/sq-sync-out` | `<SyncOutBuilder>` page — pick scope, run compliance check, show package, copy/email/save |
| `/sq-sync-in` | `<SyncInApplier>` page — paste package, show diff plan, confirm + apply |
| `/sq-chunk` | `<ChunkTool>` page — duration input, see chunk plan + Gantt-ish view |
| `/sq-chunk-intent` | `<ChunkIntent>` — pick existing intent, decompose, write chunks back to it |
| `/sq-estimate` | `<EstimateTool>` page — input estimate, see ADHD-adjusted output |
| `/sq-recover` | `<Recover>` page — list interrupted sessions, click to restore |
| `/sq-task-initiation` | `<TaskInitiation>` modal — diagnose block type, apply protocol |
| `/sq-parakeet` | `<Parakeet>` widget — embedded in header; shows current urgency-toned message |
| `/sq-dashboard` | Already exists as static HTML — link to it from header |
| `/sq-reminders-install` | `<RemindersInstall>` page (macOS only) — install/uninstall buttons |
| `/sq-init` | `<InitWizard>` flow — first-run setup + "add vault" later |

**Browser-native bonuses that slash commands can't do well:**

- **Drag-and-drop file move** between PARA folders (write metadata + move file)
- **Inline checkbox toggling** in Markdown without opening the editor
- **Side-by-side compare** of two intents or two decisions
- **Multi-select bulk operations** (archive 5 intents at once)
- **Visual deadline calendar** (month grid showing deadlines)
- **Kanban board** view of intents grouped by `estado`

---

# Phase 2 — Backend API design

All routes wrap functions that already exist in `lib/`. The web server is a thin HTTP envelope. **All routes take a `vault` query param** (defaults to the user's default vault).

## Vault management

| Method | Route | Wraps |
|---|---|---|
| `GET` | `/api/vaults` | `config_loader.list_vaults()` — returns `[{name, path, default}]` |
| `POST` | `/api/vaults` | Adds a vault to config |
| `DELETE` | `/api/vaults/{name}` | Removes a vault (does not delete files) |
| `PUT` | `/api/vaults/{name}/default` | Marks as default |

## Read operations

| Method | Route | Wraps |
|---|---|---|
| `GET` | `/api/health` | new — `{ok, version}` |
| `GET` | `/api/config` | redacted config view |
| `GET` | `/api/status?vault=...` | `status_aggregator.aggregate_status` |
| `GET` | `/api/deadlines?vault=...&level=...` | `deadline_scanner.scan_vault_deadlines` |
| `GET` | `/api/projects?vault=...&folder=...` | walks vault, parses frontmatter |
| `GET` | `/api/projects/{id}?vault=...` | project page + all related files |
| `GET` | `/api/files/{path}?vault=...` | reads file, parses frontmatter, returns body |
| `GET` | `/api/search?q=...&vault=...` | regex scan over `.md` files |
| `GET` | `/api/tags?vault=...` | `tag_parser` — all tags across vault |
| `GET` | `/api/backlinks/{id}?vault=...` | new `lib/backlink_scanner.py` |
| `GET` | `/api/sessions?vault=...` | `session_scanner.scan_sessions` |
| `GET` | `/api/parakeet?vault=...` | `deadline_scanner` + parakeet tone selection |
| `GET` | `/api/dashboard.html?vault=...` | `dashboard_generator.generate_html` |

## Write operations

| Method | Route | What it does |
|---|---|---|
| `POST` | `/api/capture?vault=...` | new capture file with frontmatter |
| `POST` | `/api/files/{path}?vault=...` | overwrite file (atomic via temp + rename) |
| `POST` | `/api/files/{path}/append?vault=...` | append text to file |
| `POST` | `/api/sessions/start?vault=...` | write loading note, update state |
| `POST` | `/api/sessions/end?vault=...` | write shutdown note |
| `POST` | `/api/decisions?vault=...` | new decision file (ADR format) |
| `POST` | `/api/intents/{id}/chunk?vault=...` | decompose + write chunks back to intent |
| `POST` | `/api/move?vault=...` | move file between folders (PARA reclassify) |

## Compute / non-vault operations

| Method | Route | Wraps |di
|---|---|---|
| `POST` | `/api/chunk` | `chunk_helper.chunk_task` (no vault) |
| `POST` | `/api/estimate` | `estimate_buffer.adjust_estimate` (no vault) |

## Sync flow

| Method | Route | What it does |
|---|---|---|
| `POST` | `/api/sync/out?vault=...` | `package_protocol.generate_package` — returns the package text |
| `POST` | `/api/sync/in?vault=...` | `package_protocol.apply_package` — takes pasted block, returns diff plan |
| `POST` | `/api/sync/in/apply?vault=...` | confirms and applies a previously-planned package |

## Static serving

| Method | Route | What it does |
|---|---|---|
| `GET` | `/*` | serves `frontend/dist/`; SPA fallback to `index.html` |

---

# Phase 3 — Frontend layout

```
companions/web-ui/
├── README.md
├── server.py                       # ~1000–1200 LoC (stdlib only)
├── frontend/
│   ├── package.json                # react, react-dom, marked, @codemirror/lang-markdown
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── index.html
│   └── src/
│       ├── App.tsx                 # router + global vault state + dark mode
│       ├── api.ts                  # typed fetch client (every route above)
│       ├── types.ts                # Vault, Project, Intent, Decision, Capture, Deadline, ...
│       ├── routes.tsx              # client-side router config
│       ├── stores/
│       │   ├── vaultStore.ts       # current vault + switching
│       │   └── searchStore.ts      # search query + matched files
│       ├── styles.css
│       └── components/
│           ├── layout/
│           │   ├── Header.tsx
│           │   ├── Sidebar.tsx
│           │   ├── VaultSwitcher.tsx
│           │   └── ParakeetWidget.tsx
│           ├── tree/
│           │   ├── VaultTree.tsx        # PARA tree
│           │   ├── TagBrowser.tsx
│           │   └── BacklinksPanel.tsx
│           ├── editor/
│           │   ├── FileEditor.tsx       # CodeMirror + preview
│           │   ├── FrontmatterEditor.tsx
│           │   └── MarkdownPreview.tsx
│           ├── views/
│           │   ├── WhereAmI.tsx
│           │   ├── Status.tsx
│           │   ├── DeadlineList.tsx
│           │   ├── BriefGenerator.tsx
│           │   ├── DecisionWizard.tsx
│           │   ├── SyncOutBuilder.tsx
│           │   ├── SyncInApplier.tsx
│           │   ├── ChunkTool.tsx
│           │   ├── EstimateTool.tsx
│           │   ├── Recover.tsx
│           │   ├── TaskInitiation.tsx
│           │   ├── RemindersInstall.tsx
│           │   ├── InitWizard.tsx
│           │   ├── ProjectBoard.tsx     # kanban by estado
│           │   ├── ProjectList.tsx
│           │   ├── ProjectDetail.tsx
│           │   └── DeadlineCalendar.tsx
│           └── modals/
│               ├── CaptureForm.tsx
│               ├── SessionStart.tsx
│               ├── SessionEnd.tsx
│               └── DailyBriefingModal.tsx
└── launchd/                        # macOS auto-start (optional)
    ├── install.sh
    ├── plist.template
    └── server-daemon.sh
```

**Estimated frontend size:** ~4,500–6,000 LoC (this is 2–3× the source because of the skill UIs).

---

# Phase 4 — Integration with installer + CLI

## `squirrel web` subcommand

```bash
squirrel web start [--port 3939] [--vault NAME] [--lan]
squirrel web stop
squirrel web status              # is it running? on what port?
squirrel web open                # start if not running + open browser
squirrel web rebuild             # re-run npm install + npm run build
```

PID stored at `~/.squirrel/web-ui.pid`. Logs to `~/.squirrel/web-ui.log`.

## TUI installer integration

Add a step to `install.sh` (between current step 5 and 6):

```
── Step 6/7 — Web UI (optional) ──

  Browser dashboard with the same capabilities as Obsidian + every slash command.
  Localhost-only, no auth.

  Requires:
    • Node.js ≥ 18 to build the frontend (~2 min)
    • The frontend is built once; no Node needed at runtime

  ▶ No  — skip (default)
    Yes — install
```

If yes, installer runs `companions/web-ui/install.sh` which does `npm install` + `npm run build`.

In `--auto` mode: skip unless `--with-web-ui` is passed.

## macOS auto-start (optional)

Mirror `companions/macos-reminders/install.sh`. Launchd plist runs the server at login. Opt-in via `/sq-web-install` slash command or `companions/web-ui/launchd/install.sh`.

---

# Phase 5 — Security & operations

| Concern | Mitigation |
|---|---|
| No auth | Bind `127.0.0.1` only by default. `--lan` flag required to bind elsewhere, prints a big warning. |
| Multi-vault path traversal | Every vault lookup goes through `config_loader.get_vault(name)` which returns an absolute path. Every file path is then `resolve()`'d and checked to start with that vault root. |
| CORS | Dev mode (Vite on :3000): `Access-Control-Allow-Origin: http://localhost:3000`. Prod (same-origin): no CORS headers needed. |
| File writes | Atomic via temp file + `os.replace`. No partial writes. |
| Delete operations | Not exposed in v1. Period. |
| Sensitive data in `.md` | Don't log request bodies. Access log records URL + status only, opt-in. |
| Server crash | Stateless except for the PID file. Restart-safe. |
| Concurrent edits between UI + Obsidian | Out of scope for v1. Last-write-wins. Document this clearly. |

---

# Phase 6 — Sequenced delivery

Realistic phasing if you decide to ship this:

## Milestone A — Multi-vault core (1 week)

- Config schema change + auto-migration
- New `lib/config_loader.py`
- `squirrel vaults list/add/remove/default` subcommands
- All `lib/*.py` accept vault path (already do — verify only)
- All slash commands accept `--vault NAME`
- Per-vault `state.json` files
- Update `INSTALL.md` + user guide with multi-vault docs
- **No UI work yet** — slash commands and CLI users immediately benefit

## Milestone B — Web UI read-only MVP (1 week)

- `companions/web-ui/server.py` with all GET routes
- Frontend scaffold (Vite, Tailwind, App, Header, Sidebar, VaultSwitcher)
- `<VaultTree>` — file browser
- `<FileEditor>` — read-only Markdown preview (no edit yet)
- `<WhereAmI>`, `<Status>`, `<DeadlineList>` pages
- `<ProjectList>` + `<ProjectDetail>` (read-only)
- Search across vault
- `squirrel web start/stop` CLI
- Installer integration

At this point: you can browse the vault in a browser, run status/deadlines, see projects — but not edit. Obsidian still owns editing.

## Milestone C — Editing + Capture (1 week)

- CodeMirror integration in `<FileEditor>`
- `<FrontmatterEditor>`
- `<CaptureForm>` modal
- POST `/api/files/{path}` and `/api/capture`
- `<TagBrowser>`, `<BacklinksPanel>` (Obsidian-like exploration)
- Drag-and-drop file move

At this point: a user can do their daily capture/edit loop entirely in the browser, with Obsidian as an alternative.

## Milestone D — Skill UIs (1.5 weeks)

- `<SessionStart>` + `<SessionEnd>`
- `<BriefGenerator>`
- `<DecisionWizard>`
- `<ChunkTool>` + `<EstimateTool>` + `<ChunkIntent>`
- `<Recover>` + `<TaskInitiation>`
- `<ParakeetWidget>` in header
- `<DailyBriefingModal>`

At this point: every slash command has a UI. The web UI is a full peer to the AI agent interface.

## Milestone E — Sync + advanced (1 week)

- `<SyncOutBuilder>` with compliance check UI
- `<SyncInApplier>` with diff preview
- `<InitWizard>` for first-run UI setup
- `<RemindersInstall>` (macOS)
- `<DeadlineCalendar>` month view
- `<ProjectBoard>` kanban (drag between estados)

## Milestone F — Polish (1 week)

- Theming refinement
- Keyboard shortcuts (Cmd-K command palette, Cmd-P file picker — Obsidian parity)
- Dataview-style query rendering (use existing `templates/dataview/`)
- Side-by-side compare view
- Multi-select bulk operations
- Documentation pass: `companions/web-ui/README.md`, update `INSTALL-README.md`, update user guide

**Total: ~6.5 weeks of focused work**, or ~13 weeks at half-time.

---

# Open questions

1. **Editor library:** CodeMirror 6 vs Monaco vs `<textarea>` + preview? CodeMirror 6 is small (~150KB gzipped), Obsidian-grade syntax, and MIT. Recommended.
2. **Bundle Node for end users?** Pre-build `frontend/dist/` and commit to git so users don't need Node at install. Adds ~1MB to clone size but removes a major install friction. Recommended.
3. **Concurrent edit safety:** If a user has the same file open in Obsidian AND the web UI, what happens? Simplest: last-write-wins with no warning. Better: file mtime check before write, refuse if changed since last read. Decision needed.
4. **Should the UI support multiple vaults simultaneously (tabs/splits) or one-at-a-time?** Obsidian itself uses one vault per window. One-at-a-time is simpler — recommend that for v1.
5. **Dataview query rendering:** Squirrel ships Dataview templates in `templates/dataview/`. These use Obsidian's Dataview plugin syntax. Re-implementing Dataview in JS is large. Options:
   - (a) Render a static snapshot at request time on the server (Python evaluates the query against vault metadata, returns rendered table). **Recommended for v1.**
   - (b) Implement a JS Dataview evaluator. Out of scope.
   - (c) Skip Dataview in the web UI; tell users to use Obsidian for those views.
6. **Auth for future LAN/multi-device:** Out of v1 scope, but design choice now affects later: HTTP Basic over localhost forwarded via SSH is the easiest path. Don't build auth in v1 — document this.
7. **Mobile?** The source project is desktop-only. Squirrel's web UI could be responsive, but mobile-first is a big addition. Recommend: ship desktop-first, leave mobile for later.

---

# Decisions needed before implementation starts

1. **Greenlight Milestone A (multi-vault) standalone?** It's valuable independent of the UI work and unblocks everything else.
2. **For Milestone B onwards: ship pre-built `dist/` in git, or require Node at install time?**
3. **CodeMirror 6 acceptable as a frontend dependency?**
4. **Concurrent edit model: last-write-wins or mtime check?**
5. **Dataview: server-side snapshot, JS reimplementation, or skip in v1?**
6. **In-repo as `companions/web-ui/` or a separate satellite repo?**

After these 6 answers, the plan above is essentially the spec — every route, every component, and every milestone is named.
