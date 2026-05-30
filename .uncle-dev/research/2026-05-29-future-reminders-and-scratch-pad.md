# Research: Future Reminders & Scratch Pad Project

**Date:** 2026-05-29  
**Scope:** How to implement future reminders on tasks/notes/captures, and a default Scratch Pad project.  
**Status:** Research only — what IS, not what should be.

---

## 1. Storage Architecture

The vault is **fully file-based** — no database, no migrations. All data lives as Markdown files with YAML frontmatter. Schema evolution means editing frontmatter fields or adding new files.

| Item type | Location | Naming |
|-----------|----------|--------|
| Projects | `<vault>/01-Proyectos-Activos/<TAG>/` | `<TAG>/<TAG>.md` (page) |
| Tasks/Intents | `<vault>/01-Proyectos-Activos/<TAG>/` | `<TAG>-<SUBAREA>-NNN.md` |
| Unfiled captures | `<vault>/99-Resources/Inbox/` | `UNFILED-NNN.md` |
| Project captures | `<vault>/01-Proyectos-Activos/<TAG>/` | `<TAG>-CAPTURE-NNN.md` |
| Areas | `<vault>/03-Areas/` | scanned by `deadline_scanner` |

`deadline_scanner.py` scans `01-Proyectos-Activos` and `03-Areas` — not `99-Resources/Inbox`.

---

## 2. Current Deadline / Notification System

### Frontmatter field

The single date field on both intents and captures is `deadline: YYYY-MM-DD`.  
Intent template (`agent-pack/templates/intent.md`, line 8): `deadline: <YYYY-MM-DD>   # ISO date; omit if no hard deadline`  
Capture writer (`apps/cli/lib/capture_writer.py`): no deadline field written at all.

### Classification (`apps/cli/lib/deadline_scanner.py`)

`classify_urgency()` (line 37) maps a deadline to exactly one of six urgency levels:

| Level | Condition |
|-------|-----------|
| `critical` | Already past (`is_overdue=True`, `days_overdue=N`) OR today with < 4 h left |
| `urgent` | Today ≥ 4 h left, or tomorrow |
| `soon` | 2–3 days |
| `upcoming` | 4–7 days |
| `eventual` | 8–30 days |
| `distant` | > 30 days |

`scan_vault_deadlines()` (line 75) reads all `.md` frontmatter at request time — no persistent state, no scheduling. Completed tasks (`estado: done/completado/archived`) are skipped (line 115).

### API endpoints

- `GET /api/home` (server.py ~line 457) — returns `pressing[]` array: overdue + critical + urgent items, capped at 5.
- `GET /api/deadlines` (server.py line 807) — returns all urgency groups.
- `GET /api/parakeet` (server.py line 878) — returns a plain-text human summary string.

No `/api/reminders` endpoint exists.

### Notification delivery (`apps/desktop/src-tauri/src/tray_alerts.rs`)

Tauri's Rust async loop is the **only timed trigger** in the system:

| Constant | Value | Role |
|----------|-------|------|
| `POLL_INTERVAL` | 30 s | How often `/api/home` is polled |
| `REQUEST_TIMEOUT` | 3 s | Per-request timeout |
| `MAX_ALERTS` | 3 | Max pressing items shown in tray menu |
| `NOTIF_INTERVAL` | 120 s | Min gap between notification batches |
| `ITEM_COOLDOWN` | 3600 s | Per-item notification cooldown |
| `MAX_DIALOGS_PER_DAY` | 8 | Daily OS notification cap |

`check_notifications()` (line 158) uses `tauri_plugin_notification` to fire native OS banners. Sleep/wake detection (line 254) resets `last_check_at` on wakes to suppress burst notifications.

The backend Python server (`server.py`) starts a bare `HTTPServer.serve_forever()` (line 1140) — **no threads, timers, or schedulers** are started there.

launchd (`apps/backend/launchd/plist.template`) keeps `server.py` running as a persistent daemon; it has no `StartInterval` key — it is not a periodic trigger.

---

## 3. What Doesn't Exist (Reminder-Related)

- No `reminder_date` frontmatter field on any file type (intent, capture, project).
- No "future reminder" urgency level in `deadline_scanner.py`.
- No reminder-specific scan or API endpoint.
- No snooze/dismiss state on any task/note.
- No 7-day pre-reminder window logic anywhere.
- The `Alert` struct in `tray_alerts.rs` (line 56) only carries `is_overdue`, `hours_left`, `days_overdue`, `urgency_label` — no reminder concept.
- No persistent state for "user dismissed this reminder" — all cooldowns in `TauriNotificationState` are **in-memory** (lost on app restart).

---

## 4. Project System

### Creation (`apps/cli/lib/new_project_writer.py`)

`create_project()` (line 240) requires:
- `tag` — matches `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` (line 57)
- `tipo` — must be one of `{A, B, C}` (line 59)
- WIP capacity check via `status_aggregator.aggregate_status()` (line 180), default cap = 3, overridable with `force=True`

Project page frontmatter written (template lines 74–98): `id`, `tipo`, `estado: wip`, `creado`, `deadline`, `stakeholders`, `tags`.

### Project detection

A project "exists" if and only if its directory `01-Proyectos-Activos/<TAG>/` exists (line 266). There is no registry, no config file, no database record.

### What doesn't exist for Scratch Pad

- No `system: true` or `protected: true` frontmatter flag on any project.
- No initialization hook (e.g., run-at-vault-setup).
- No "cannot delete" constraint in the API — the only delete check is `PROJECT_EXISTS` (refuses to overwrite, not to protect).
- No fallback routing to a named project in `write_capture()` — unfiled items go to `99-Resources/Inbox/` (line 57–58).
- WIP cap would count Scratch Pad as a regular project unless exempted.
- No `tipo` equivalent for "scratch/utility" projects — only A/B/C exist.

---

## 5. Frontend State

**Task creation:** `NewTaskModal` (`apps/backend/app/src/components/NewTaskModal.tsx`) — fields: `tag`, `title`, `description` (markdown), `deadline` (native `<input type="date">`). Calls `api.intentCreate()`. No `reminder_date` input.

**Task editing:** `NoteEditPage` (`apps/backend/app/src/pages/NoteEditPage.tsx`) — edits raw frontmatter as plain text + body. No structured field UI. No reminder field.

**Capture modal:** `CaptureModal` — text only, no date fields, no project selector shown for reminders.

**Deadlines display:** `DeadlinesWidget` (desktop, `apps/desktop/src/components/DeadlinesWidget.tsx`) — read-only; shows `pressing` items with overdue chips. Not editable.

**Desktop-to-backend:** all via plain `fetch` to `http://127.0.0.1:3939`. No Tauri `invoke()` IPC for data operations.

---

## 6. Key File References

| File | Relevance |
|------|-----------|
| `apps/cli/lib/deadline_scanner.py:37` | `classify_urgency()` — the 6-level classification |
| `apps/cli/lib/deadline_scanner.py:75` | `scan_vault_deadlines()` — full vault scan |
| `apps/cli/lib/new_project_writer.py:240` | `create_project()` — project creation API |
| `apps/cli/lib/new_project_writer.py:57` | Tag regex + WIP cap logic |
| `apps/cli/lib/capture_writer.py:29` | `write_capture()` — unfiled goes to `99-Resources/Inbox/` |
| `apps/backend/server.py:457` | `api_home()` — builds `pressing[]` |
| `apps/backend/server.py:807` | `api_deadlines()` — grouped urgency response |
| `apps/desktop/src-tauri/src/tray_alerts.rs:22` | Constants: poll interval, cooldown, daily cap |
| `apps/desktop/src-tauri/src/tray_alerts.rs:158` | `check_notifications()` — OS notification gate |
| `apps/backend/app/src/components/NewTaskModal.tsx` | Only deadline `<input type="date">` in UI |
| `agent-pack/templates/intent.md` | Intent frontmatter template (no reminder field) |
