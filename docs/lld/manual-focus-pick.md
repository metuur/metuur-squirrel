# Manual Focus Pick (Today & Week) — Low-Level Design

## Architecture

```
Manual Focus Pick — touched components only
│
├── apps/cli/lib/  (Python core, single source of truth)
│   ├── focus_picker.py                    [NEW]
│   │   ├── get_manual_focus(vault) -> { today, week }
│   │   │     # scans all intent files; returns ones whose
│   │   │     # focus_today / focus_week tokens match "now"
│   │   ├── set_manual_focus(vault, slot, project_slug, intent_slug)
│   │   │     # 1. compute token (date or ISO week)
│   │   │     # 2. find all intent files carrying that slot key → strip
│   │   │     # 3. write the new key on the target intent file
│   │   ├── clear_manual_focus(vault, slot)
│   │   │     # remove the slot key from any intent file carrying it
│   │   └── _token_now(slot, tz)
│   │         # "2026-05-28"  for today
│   │         # "2026-W22"    for week (ISO 8601 %G-W%V, local tz)
│   │
│   ├── intent_parser.py                   [TOUCHED]
│   │   └── read_frontmatter(path) — already exists; reused
│   │   └── write_frontmatter(path, dict)  [NEW helper]
│   │         # round-trips YAML, preserves key order, deletes keys
│   │         # whose value is the sentinel _DELETE
│   │
│   └── status_aggregator.py               [UNCHANGED]
│         # _recommend_focus() keeps its 3-rule heuristic verbatim
│
├── apps/backend/server.py                 [TOUCHED]
│   ├── GET /api/home                      [SUPERSET]
│   │   # response.focus       — UNCHANGED (heuristic)
│   │   # response.manual_focus — NEW: { today, week } | null per slot
│   ├── GET /api/focus                     [NEW]
│   │   # → { today: {...}|null, week: {...}|null }
│   ├── PUT /api/focus/today               [NEW]
│   │   # body: { project_slug, intent_slug } | { clear: true }
│   ├── PUT /api/focus/week                [NEW]
│   │   # same body shape
│   └── delegates all logic to focus_picker.py
│
├── apps/desktop/src/                      [TOUCHED]
│   ├── components/FocusWidget.tsx
│   │   ├── Primary card                   — UNCHANGED (heuristic)
│   │   └── ManualFocusPills (NEW)         — 📌 Today | 📌 This week
│   │         └── each pill: { Change | Clear } buttons
│   ├── components/FocusPickerModal.tsx    [NEW]
│   │   # project list (from /api/home.projects[])
│   │   # → expand to intents (from /api/projects/<slug>)
│   │   # → click → PUT /api/focus/<slot>
│   └── hooks/useHome.ts                   [TOUCHED]
│         # widens the typed response to include manual_focus
│
├── agent-pack/companions/macos-reminders/reminder-daemon.sh   [TOUCHED]
│   ├── compose_deeplink(project, task, action="focus")
│   │     emit_banner passes action="focus" so the URL becomes
│   │     squirrel://projects/<TAG>?action=focus
│   └── On banner click (terminal-notifier path only):
│       └── macOS opens the URL → desktop app handles it (see D-6).
│             (Older "Open" / 3-button-dialog model is gone — banners
│              have no buttons; see native-notification-banner unit 1.)
│
└── CLI commands (squirrel plugin) [NEW]
    ├── /sq-focus                          # show current picks
    ├── /sq-focus today TAG/INTENT-SLUG    # set today
    ├── /sq-focus week TAG/INTENT-SLUG     # set week
    ├── /sq-focus today --clear            # clear today
    └── /sq-focus week  --clear            # clear week
```

### Data flow — happy path (UI pick)

1. User clicks `Pick focus` on `FocusWidget` → `FocusPickerModal` opens.
2. Modal lists active projects from already-cached `/api/home.projects[]`.
3. User expands a project → modal fetches `/api/projects/<slug>` for its intents (existing endpoint).
4. User clicks an intent → modal `PUT /api/focus/today` with `{project_slug, intent_slug}`.
5. Server calls `focus_picker.set_manual_focus(vault, "today", slug, intent)`:
   1. Computes `token = "2026-05-28"`.
   2. Walks `vault/01-Proyectos-Activos/*/`, reads each intent file's frontmatter, strips any `focus_today` key whose value matches today's token (lazy cleanup). Stale tokens (different date) are left alone in this pass — they'll get pruned the next time *that* file is written to.
   3. Writes `focus_today: 2026-05-28` into the target intent file's frontmatter.
6. Server returns the new `{ today: {...}, week: {...} }` object.
7. `useHome()` refetches `/api/home`; widget re-renders with the pill populated.

### Data flow — daemon banner → desktop focus

1. Daemon's `emit_banner(project, ntitle, subtitle, body)` runs for project TAG.
2. `compose_deeplink "$project" "$project" "focus"` yields `squirrel://projects/<TAG>?action=focus`.
3. `terminal-notifier -open <url>` registers the URL as the banner's click target. (The `osascript display notification` and `show_dialog_fallback` paths have no URL-on-click affordance — focus-set is unavailable there; recorded in R-8.3 as a v1 limitation.)
4. User clicks the banner; macOS routes the `squirrel://` URL to the registered Tauri app (`tauri-plugin-deep-link` — `native-notification-banner` story 2.1).
5. Tauri's `on_open_url` handler (`native-notification-banner` story 3.3) inspects the parsed URL — including the `action=focus` query — and dispatches to a focus-action handler (consumed by a future story in unit 4 of `native-notification-banner`).
6. Desktop calls `apps/cli/lib/status_aggregator.active_intent_for(vault, project_slug)` (story 8.1) and then `PUT /api/focus/today` with `{project_slug, intent_slug}`.
7. Desktop navigates to the project page. Daemon state file is unaffected by the click; cadence / cap accounting still happens at emission time via `update_state_after_emit`.

### Data flow — lazy expiry on read

1. `GET /api/home` calls `focus_picker.get_manual_focus(vault)`.
2. Function walks intent files; for each one with a `focus_today` key:
   - If value equals today's local-date token → include it as `manual_focus.today` candidate.
   - If value is any other string → skip (treat as expired/stale).
3. If multiple candidates exist for the same slot, pick the one with the most-recent file mtime.
4. The function does **not** rewrite any file during a read. Pruning happens only on write paths.

## Constraints

- **No new storage system.** Picks live in vault Markdown frontmatter only. No `~/.squirrel/focus.json`, no SQLite, no in-memory cache that outlives a request.
- **Python core stays the source of truth.** Tauri Rust never reads or writes intent frontmatter. The desktop popup always goes through `/api/focus/*`.
- **Backwards-compatible response shapes.** `GET /api/home.focus` shape and semantics are frozen. The `manual_focus` field is purely additive.
- **YAML round-trip safety.** Writes MUST preserve existing frontmatter keys, comments, and key order. We use `ruamel.yaml` (if already a dependency) or a minimal hand-rolled round-tripper if not — TBD in implementation, validated by a golden-file test.
- **Single-pick invariant per slot.** Enforced at write time only. If a manual Obsidian edit creates duplicates, read-time picks the most-recently-modified file (deterministic, no crash).
- **Local timezone for date/week computation.** Both today's date and the ISO week are computed in the *user's local* timezone, not UTC. This matches how the deadline scanner already works (`deadline_scanner.py:37–72`).
- **ISO-8601 week format.** `focus_week` uses `%G-W%V` (e.g. `2026-W22`) — the same format used in calendar tooling, week-numbered relative to the ISO calendar (Monday = day 1).
- **Daemon curl timeout = 2s.** Daemon runs in a launchd context with limited time; backend reachability is best-effort. Daemon never blocks the user's choice on backend availability.
- **CSP unchanged.** No new origins; `/api/focus/*` is on the same `127.0.0.1:3939` already allowed by Phase 2's CSP (`R-5.1`).

## Key Decisions

### D-1 — Flag on the intent file, not the project page
**Decision**: Store `focus_today` / `focus_week` on the **intent file's** frontmatter.
**Rationale**: The pick is (project + intent). Intent files already uniquely identify both (they live as siblings inside the project folder). Storing on the project page would force a second key for "which intent" and create an inconsistency window if either side gets stale.
**Rejected alternative**: Store on the project page with a sub-key. Rejected — uglier, no advantage.

### D-2 — Value doubles as expiry marker
**Decision**: The YAML value IS the date (`focus_today: 2026-05-28`) or ISO week (`focus_week: 2026-W22`).
**Rationale**: One key, one field. No background job needed. Lazy read-time check: if the value doesn't match "now", treat as cleared. Obsidian users immediately see *when* the focus was set just by reading the frontmatter.
**Rejected alternative**: Boolean flag (`focus_today: true`) + separate `focus_set_at: <iso>`. Rejected — two keys to keep in sync, and `true` without a date means the file would stay "focused" forever after the user closed their laptop.

### D-3 — Lazy cleanup, no background sweeper
**Decision**: Stale entries are ignored on read; only pruned when the user picks a new focus.
**Rationale**: No daemon, no cron, no launchd. ADHD-friendly: nothing silently mutates the vault behind the user's back. Obsidian git-sync stays predictable.
**Rejected alternative**: Sweep on every `GET /api/home`. Rejected — performs writes on a GET, breaks request idempotence, and touches files the user might be editing in Obsidian (sync conflict risk).

### D-4 — Single-pick invariant enforced at write
**Decision**: When the user picks a new focus, scan the vault for *any* intent file carrying the same slot key with today's token; strip the key from each before writing the new one.
**Rationale**: Cheap (vault size is bounded — Squirrel is a personal tool, dozens of intents at most). Guarantees `count(focus_today == today) ≤ 1` at all times when the API is the sole writer.
**Limitation**: Manual Obsidian edits can create transient duplicates. Handled by read-time tiebreak (most-recent mtime).

### D-5 — Both heuristic and manual focus surfaced via different fields
**Decision**: `GET /api/home.focus` keeps its current shape (heuristic only). A new `GET /api/home.manual_focus` field carries the user's picks.
**Rationale**: Zero risk to existing consumers (browser SPA, future agents) of the current `focus` field. UI composes both views explicitly rather than the server collapsing them.
**Rejected alternative**: Overload `focus` with a `source: "heuristic" | "manual"` tag. Rejected — breaks consumers that key off `focus.project` to highlight the overdue card.

### D-6 — Daemon emits a `?action=focus` deep-link; desktop sets focus on click
**Decision**: The daemon's `compose_deeplink` helper accepts an optional `action` argument. `emit_banner` calls it as `compose_deeplink "$project" "$project" "focus"`, producing `squirrel://projects/<TAG>?action=focus`. That URL is passed to `terminal-notifier -open`. When the user clicks the banner, macOS routes the URL to the registered Tauri app via `tauri-plugin-deep-link`; the desktop app resolves the active intent and calls `PUT /api/focus/today`, then navigates to the project page.
**Rationale**: `native-notification-banner` stories 1.x replaced the legacy 3-button `osascript display dialog` with native banners. Banners have no custom action buttons; the only click-target a banner can express is a URL. Tagging the URL with `?action=focus` lets the desktop distinguish a focus-bearing click from a plain "navigate to project" deep-link click, without inventing new URL schemes or path conventions (so `deep_link::validate` from `native-notification-banner` story 3.1 still passes — it ignores query strings).
**Rejected alternatives**:
- Restore the 3-button `osascript display dialog` for daemon alerts. Rejected — undoes the recently-shipped banner work and reintroduces the UX trade-offs banners were chosen to fix.
- Daemon does the `PUT /api/focus/today` eagerly at emission time. Rejected — "the banner appeared" ≠ "the user committed". User may dismiss without clicking; eager focus-set would falsify the pick.
- Encode the active intent in the URL path (e.g. `squirrel://projects/<TAG>/<INTENT>?action=focus`). Rejected — conflates the `task_id` segment that `deep_link::validate` already defines; cleaner to keep intent resolution on the desktop side (it has access to the live `/api/home` payload via `useHome`).

**Acknowledged trade-off**: On the `osascript display notification` and `show_dialog_fallback` paths, clicking the banner cannot open our URL. Focus-set is unavailable on those paths in v1. Recorded as R-8.3; revisit if the fallback paths become primary.

### D-7 — Auto-clear is "from the user's perspective", not "physical key removal"
**Decision**: After local midnight, `manual_focus.today` is reported as `null` even though the YAML key still physically exists in the intent file (with yesterday's date).
**Rationale**: This is the lazy-cleanup principle (D-3) made explicit at the API boundary. The user said "the user should pick every day the focus for the day or the week" — that's a UX guarantee, not a filesystem guarantee.
**Implication for tests**: The test for "auto-clear at midnight" asserts the API response, not the file contents.

### D-8 — `Clear` action deletes the key, never writes `null`
**Decision**: When the user clears a pick (button, CLI `--clear`, or PUT with `{clear: true}`), the YAML key is fully removed from the frontmatter — not set to `null` or empty string.
**Rationale**: Obsidian's frontmatter search treats `focus_today: null` as a value. A cleared pick should be invisible to all consumers.

### D-9 — Week boundary follows ISO 8601 (Monday-start)
**Decision**: `focus_week` uses `%G-W%V`. The week rolls over at Monday 00:00 local time.
**Rationale**: Matches `deadline_scanner.py`'s existing weekday convention (Mon=1). Aligns with most users' mental model of "this week".
**Note for the user**: If you prefer Sunday-start weeks, this is a one-line change in `_token_now()` and the constant can be flipped post-implementation without changing storage.

## Out of Scope

- **Backfill / migration**: there are no existing `focus_today` keys to migrate. The vault is "empty" of these flags on day one.
- **A vault-wide "stale focus" cleanup command**: out of scope. If the user wants to scrub old keys, they can `grep -r "focus_today:" vault/` and edit by hand. Future work if it becomes a real pain.
- **Sync semantics across multiple machines**: relies on whatever syncs the vault (iCloud, git, Obsidian Sync). Last-write-wins per file is acceptable.
- **A "focus history" view in the desktop**: out of scope. Each pick overwrites the previous one in the YAML.
- **Telemetry / metrics on how often users pick vs use the heuristic**: out of scope. Squirrel is local-first; no telemetry.
- **Auth on `/api/focus/*`**: out of scope. Same `127.0.0.1`-only binding as every other endpoint. `--lan` mode users accept the same risk model as for `/api/notes`.
