# Quick Tasks — Focus Stack — Low-Level Design

## Architecture

Quick Tasks reuse the vault/markdown infrastructure end-to-end. Three new building
blocks (`quick_task_writer.py`, `quick_task_scanner.py`, a `QuickTaskWidget` + capture
modal) plug into the existing backend route table, the `tray_alerts.rs` poller, and the
global-shortcut registration in `lib.rs`.

```
 Capture surfaces                         Backend (server.py)                 Vault
 ─────────────────                        ───────────────────                 ─────
 ⌨ Ctrl+Cmd+Q  ─┐                                                  ┌─ SCRATCH-PAD/QT-001.md
 🍔 Tray item  ─┼─▶ capture modal ─▶ POST /api/quick-tasks ─▶ quick_task_writer ─┤  QT-002.md
 🌐 Web button ─┘                          │                                     └─ …
                                           ├─ GET /api/quick-tasks ─▶ quick_task_scanner
 tray_alerts.rs (30s poll) ─▶ GET /api/home (quick_tasks summary) ─▶ badge + in-app notif
```

### Storage: markdown files in `SCRATCH-PAD`

Each Quick Task is a markdown file in `01-Active-Projects/SCRATCH-PAD/`, named
`QT-NNN.md` where `NNN` is allocated by the existing `_next_number(folder, "QT-")`
helper (same one used for intents/captures). Frontmatter:

```yaml
id: QT-001
type: quick_task              # distinguishes from intents (type: T) so existing
                              # intent/deadline/focus scanners skip these files
quick_task: true             # explicit marker for quick_task_scanner
qt_state: active             # active | snoozed | done
qt_created_at: 2026-06-04T14:32:05   # ISO-8601 — FIFO ordering key (top = oldest)
qt_snoozed_until: 2026-06-04T15:32:05 # present only while snoozed; cleared on wake
qt_snooze_count: 0           # number of times snoozed (anti-backlog bound)
status: open                 # open | done — keeps existing scanners consistent
```

Body holds the one-line task text plus a small callout:

```markdown
# Send Q2 attachment to Ana

> ⚡ **Quick Task** · parked 2026-06-04 14:32
```

No schema migration: files lacking these keys are unaffected, and `intent_parser` already
reads arbitrary frontmatter. All writes go through the existing atomic
`write_frontmatter()` (temp file + `os.replace()`, `_DELETE` sentinel to remove keys).

### New lib module: `quick_task_writer.py`

Mirrors `reminder_writer.py` in structure. Functions:

| Function | Behavior |
|----------|----------|
| `create_quick_task(vault_path, text)` | Enforces the cap (raises `QuickTaskError("QUICK_TASK_LIMIT_REACHED")` if `active_count == 5`), allocates `QT-NNN`, writes the file with `qt_state: active`, `qt_created_at: now`, `qt_snooze_count: 0`. Returns the new id. |
| `complete_quick_task(path)` | Sets `qt_state: done`, `status: done`. Frees a slot. File is retained (no history view, but not deleted by us). |
| `delete_quick_task(path)` | Removes the file. Frees a slot. |
| `snooze_quick_task(path, until)` | Raises `QuickTaskError("QUICK_TASK_SNOOZE_LIMIT")` if `qt_snooze_count >= MAX_SNOOZES`. Otherwise sets `qt_state: snoozed`, `qt_snoozed_until: <resolved>`, increments `qt_snooze_count`. Frees a slot. |
| `activate_quick_task(path)` | Used by the wake path: sets `qt_state: active`, deletes `qt_snoozed_until`, and **re-stamps `qt_created_at = now`** so the woken task re-enters at the *bottom* of the FIFO queue. |

`until` resolution (`resolve_snooze_until`): accepts `"15m"`, `"1h"` (default), or
`"next_block"` (resolved against the AM/PM focus boundaries from the focus subsystem).
Bare ISO timestamps pass through.

Constants: `MAX_ACTIVE = 5`, `MAX_SNOOZES = 2`.

### New lib module: `quick_task_scanner.py`

Mirrors `reminder_scanner.py` — pure classification, no writes. `scan(vault_path)` reads
every `quick_task: true` file in `SCRATCH-PAD` and returns:

```python
{
  "active":   [ {id, text, path, qt_created_at}, … ],   # sorted by qt_created_at ASC
  "snoozed":  [ {id, text, path, qt_snoozed_until, wake_due: bool}, … ],
  "active_count": int,
}
```

Classification:

| Condition | Bucket |
|-----------|--------|
| `qt_state == done` (or `status: done`) | excluded |
| `qt_state == active` | `active` |
| `qt_state == snoozed` and `qt_snoozed_until > now` | `snoozed` (`wake_due: false`) |
| `qt_state == snoozed` and `qt_snoozed_until <= now` | `snoozed` (`wake_due: true`) — eligible to return |

`active` is sorted ascending by `qt_created_at` (oldest first = top of stack).

### Wake handling (lazy, capacity-aware)

The scanner never mutates. The **GET handlers** (`/api/quick-tasks` and `/api/home`)
perform a deterministic wake-commit step after scanning:

1. Scan.
2. For each `snoozed` task with `wake_due == true`, ordered by `qt_snoozed_until` ASC:
   while `active_count < MAX_ACTIVE`, call `activate_quick_task(path)` (re-stamps
   `qt_created_at`, so it lands at the bottom) and increment the working `active_count`.
3. Any still-due snoozed tasks that could not fit remain `snoozed` and are returned with a
   `return_blocked: true` flag so the UI can nudge the user to free a slot.

This honors the hard cap (a woken task never pushes active past 5) and the brief's noted
risk (a task ready to return while the stack is full waits rather than being dropped).

### API changes (`server.py`)

New entries in the regex route table (alongside the reminder routes ~line 345):

| Endpoint | Method | Handler | Purpose |
|----------|--------|---------|---------|
| `/api/quick-tasks` | GET | `api_quick_tasks_list` | Scan + wake-commit; returns `{ active, snoozed, active_count, limit: 5 }` |
| `/api/quick-tasks` | POST | `api_quick_task_create` | Body `{ text }`. `201` with the new id, or `409 {"error":"QUICK_TASK_LIMIT_REACHED"}` |
| `/api/quick-task/<id>/complete` | PATCH | `api_quick_task_complete` | Mark done, free slot |
| `/api/quick-task/<id>/snooze` | PATCH | `api_quick_task_snooze` | Body `{ until? }`. `409 {"error":"QUICK_TASK_SNOOZE_LIMIT"}` past `MAX_SNOOZES` |
| `/api/quick-task/<id>` | DELETE | `api_quick_task_delete` | Remove file, free slot |
| `/api/home` | GET (extend) | `api_home` | Add `quick_tasks: { active: [...top N], active_count, snoozed_count, oldest }` |

`<id>` matches the existing note-id regex shape (`[A-Za-z0-9][A-Za-z0-9_-]*`). All write
handlers resolve the file under `SCRATCH-PAD` only (never elsewhere in the vault) and
invalidate the home cache like the other write handlers (`server.py` ~line 559).

### Tauri global shortcut + capture modal

In `lib.rs`, register a second global shortcut next to `Ctrl+Cmd+S` (~line 152), using the
already-bundled `tauri_plugin_global_shortcut`:

```rust
app.handle().global_shortcut().on_shortcut("Ctrl+Cmd+Q", |app, _s, event| {
    if event.state == ShortcutState::Pressed {
        show_and_focus_window(app);            // reuse the Ctrl+Cmd+S activation path
        let _ = app.emit("quick-task://capture-open", ());
    }
})?;
```

The frontend listens for `quick-task://capture-open` (new `useQuickTaskCapture` hook,
mirroring `useDeepLink`/`useNotifications`) and shows a minimal modal: one text input,
Enter = submit (`POST /api/quick-tasks`), Esc = cancel. The tray menu "➕ Add Quick Task"
item and the widget's `+` button emit/trigger the same modal so there is a single capture
path. On a `409` the modal shows an inline "Stack is full — clear one first" message and
does not close.

### Tray surfacing (`tray_alerts.rs`)

The 30s poll loop already fetches `/api/home`. Extend the home struct to deserialize the new
`quick_tasks` section. Then:

- Add a tray menu section **"QUICK TASKS (N)"** listing active tasks (top = oldest),
  below the existing PRESSING NOW / REMINDERS DUE sections.
- For the **oldest active** task, fire a low-key in-app notification via the existing
  `insert_notification_if_new` path (source tagged `quick_task`), governed by the existing
  `ITEM_COOLDOWN` (3600s) and `MAX_DIALOGS_PER_DAY` (8) guards. This makes it appear in the
  in-app notification center and lights the tray badge through `update_badge_and_emit`.
- If `quick_tasks.return_blocked` is set, surface a single "A snoozed quick task is ready —
  clear a slot" nudge (same cooldown).

OS popups are **not** specially enabled; they follow the existing notification setting.

### Web UI: `QuickTaskWidget`

New React component `apps/desktop/src/components/QuickTaskWidget.tsx` (+ `.module.css` +
`.test.tsx`), mirroring `DeadlinesWidget`. Always visible. Renders the FIFO stack with the
top (oldest) item emphasized, each row offering **✓ Complete · 💤 Snooze · ✕ Delete**, and a
`+ Add Quick Task` button (disabled with a tooltip when `active_count === 5`). Snooze offers
15m / 1h / next block. Data via `GET /api/quick-tasks`; refetches on the Tauri event emitted
after the daemon poll (same pattern as `useNotifications`).

## Constraints

- File system is the only storage layer for Quick Tasks — no new SQLite table (the
  notifications table is reused only for surfacing). Atomic writes via temp file +
  `os.replace()`.
- All date/time handling uses ISO-8601 and must tolerate both string and native
  `datetime` values returned by the frontmatter parser (same caveat as the reminder code).
- The cap check and the wake-commit step must be race-tolerant for the single-process
  backend: read the live directory state immediately before writing, never a stale count.
- macOS desktop only; the global shortcut must fail soft if `Ctrl+Cmd+Q` is already held by
  another app (log and continue, like `Ctrl+Cmd+S`).
- `quick_task` files must be invisible to the intent, deadline, focus, and reminder
  scanners — guaranteed by `type: quick_task` and those scanners' existing type/status
  filters; verify each scanner skips it.

## Key Decisions

**Markdown in `SCRATCH-PAD`, not a SQLite table.** Chosen to reuse the entire existing
vault/frontmatter/atomic-write toolchain (`write_frontmatter`, `_next_number`,
`ensure_scratch_pad`) and keep one storage model. The known downside — Quick Tasks becoming
"real" vault files — is contained by the hard active cap (5) and the bounded snooze model,
which together prevent the accumulation the feature is meant to fight.

**`type: quick_task` marker rather than reusing `type: T` intents.** A distinct type keeps
Quick Tasks out of every existing scanner (focus, deadline, reminder, WIP) with zero changes
to those modules, preserving their EARS specs.

**FIFO by `qt_created_at`, re-stamped on wake.** Ordering is purely temporal, so "oldest at
top / new at bottom" needs no separate position field. Re-stamping on wake makes a returning
task re-enter at the bottom, matching the brief.

**Snooze is bounded (`MAX_SNOOZES = 2`) and capacity-aware on return.** Unbounded snoozing
would recreate the backlog the feature exists to prevent. Capping snooze count and refusing
to breach the active cap on wake keeps the stack genuinely small and honest.

**Lazy, handler-side wake-commit instead of a background sweeper.** Matches the reminder
system's "classify at scan time" philosophy and avoids a second timer; the only writes happen
when a GET handler runs, which is also when results are about to be shown.

**Separate `quick_task_writer`/`quick_task_scanner` modules.** Parallels the
reminder_writer/reminder_scanner split — keeps Quick Task logic isolated and independently
testable, consistent with the codebase's one-concern-per-module convention.

## Out of Scope

- Editing Quick Task text, manual reordering, priorities, tags, deadlines, estimates.
- Quick Task recurrence and a completed-task history/audit view.
- Any change to project WIP rules, focus picking, or the existing reminder/deadline scanners.
- Windows/Linux tray support and any new OS-notification channel or sound.
- Migrating existing `99-Resources/Inbox/` captures into the Quick Task Stack.
