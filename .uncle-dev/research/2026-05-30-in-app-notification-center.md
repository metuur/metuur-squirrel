# Research: In-App Notification Center
**Date:** 2026-05-30  
**Topic:** Current notification architecture — what exists, how it flows, what is absent

---

## 0. Architecture Overview (Current State)

```
  Vault (.md files)
  ┌────────────────────────────────────────┐
  │  reminder_date: 2026-06-01             │
  │  reminder_dismissed: (empty)           │
  │  reminder_snoozed_until: (empty)       │
  └──────────────┬─────────────────────────┘
                 │ rglob("*.md")
                 ▼
  Python CLI lib (one-shot, sync)
  ┌───────────────────────────────┐
  │  reminder_scanner.py          │
  │  ├─ approaching[]  (1–7 days) │
  │  └─ active[]       (≤ 0 days) │
  └──────────────┬────────────────┘
                 │ called on every request
                 ▼
  Python HTTP Server  (port 3939)
  ┌───────────────────────────────────────────────────────┐
  │  GET  /api/reminders  → {approaching[], active[]}     │
  │  GET  /api/home       → {reminders: {counts only}}    │
  │  PATCH /api/reminder/{id}/dismiss                     │
  │  PATCH /api/reminder/{id}/snooze                      │
  └─────────┬──────────────────────┬────────────────────--┘
            │ HTTP poll (30 s)     │ HTTP fetch (on mount)
            │                      │
            ▼                      ▼
  Tauri Rust daemon            Web UI (browser)
  ┌────────────────────────┐   ┌──────────────────────────┐
  │  tray_alerts.rs        │   │  RemindersWidget.tsx      │
  │  ├─ select_candidates  │   │  ├─ approaching section   │
  │  ├─ rate-limit guards  │   │  └─ active section        │
  │  │  (8/day, 1hr/item)  │   │     ├─ Dismiss button     │
  │  └─ check_notifications│   │     └─ Snooze date picker │
  │       │                │   └──────────────────────────┘
  │  tray.rs               │
  │  ├─ update_alerts()    │
  │  │  (tray menu items)  │
  │  └─ set_state()  ← DEAD│   ← Notification icon never set
  └────────┬───────────────┘
           │ tauri_plugin_notification
           ▼
  macOS Notification Center
  ┌──────────────────────────┐
  │  ⏰ squirrel: {alert.id} │
  │  📅 squirrel: {rem.id}   │
  └──────────────────────────┘

  Tauri Desktop Frontend (popup)
  ┌──────────────────────────┐
  │  FocusWidget             │
  │  DeadlinesWidget         │   ← No notification UI exists
  │  ParakeetWidget          │   ← No Tauri events received
  │  (no NotifCenter)        │   ← plugins.ts = smoke import only
  └──────────────────────────┘

  ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
  MISSING LINKS (no wire exists today):
    Rust daemon  ──✗──▶  Desktop frontend   (no app.emit)
    Tray icon    ──✗──▶  Notification state (set_state dead)
    Desktop app  ──✗──▶  Dismiss / Snooze  (only in web UI)
  ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
```

---

## 1. The Current OS Notification Path

### How notifications fire today

The entire notification path lives in the Rust/Tauri backend. There is no frontend involvement.

**`tray_alerts.rs` — polling loop (`start_polling`, line 324)**  
Runs inside `tauri::async_runtime::spawn`. Every **30 seconds** (`POLL_INTERVAL`) it:
1. Fetches `http://127.0.0.1:3939/api/home` → extracts `pressing` alerts
2. Fetches `http://127.0.0.1:3939/api/reminders` → extracts `approaching` and `active` reminder lists
3. Calls `tray::update_alerts()` → rebuilds tray menu with current data
4. Calls `check_notifications()` → fires OS notifications via `tauri_plugin_notification`

**`check_notifications` (tray_alerts.rs:215)**  
Uses `app.notification().builder().id(id).title(&title).body(&body).show()`.  
- Pressing alerts: title `"⏰ squirrel: {alert.id}"`, body = `alert.menu_label()`
- Active reminders: title `"📅 squirrel: {reminder.id}"`, body = `reminder.menu_label()`
- Approaching reminders: **NOT passed** to `check_notifications` (per R-4.4)

**Rate-limiting constants (tray_alerts.rs:21–29):**
| Constant | Value |
|---|---|
| `POLL_INTERVAL` | 30 s |
| `NOTIF_INTERVAL` | 120 s minimum between notification batches |
| `ITEM_COOLDOWN` | 3600 s (1 hr) per item |
| `MAX_DIALOGS_PER_DAY` | 8 |
| `MAX_ALERTS` | 3 per batch |

**Guard state (`TauriNotificationState`, tray_alerts.rs:31–53):**
- `last_notified: HashMap<String, Instant>` — per-item cooldown
- `dialogs_today: u32` + `dialogs_date: String` — daily cap with date rollover
- `last_check_at: Instant` — NOTIF_INTERVAL guard
- `pending_clicks: HashMap<i32, String>` — maps notification id → task URL; **populated but never consumed** (dead field)
- `next_id: i32` — auto-incrementing OS notification ID

---

## 2. Tray Icon & Menu

### Tray icon states (`tray.rs:50–57`)

Four states exist, each backed by embedded PNG assets (`icons/tray/`):
- `Normal`, `Notification`, `Processing`, `Error`

**`set_state` (tray.rs:244–250)** — sets the tray icon via `tray.set_icon(...)`.  
This function is **dead code** today. Comment reads: *"first caller arrives in Story 2.4"*.  
`show_main_window` calls `set_state(Normal)` to clear a badge when the window opens — but `check_notifications` never calls `set_state(Notification)` to set the badge in the first place.

### Tray menu structure (`build_menu`, tray.rs:79–176)

```
Open Squirrel          [OPEN]
Open Web UI            [OPEN_WEB_UI]
───────────────────
PRESSING NOW           [disabled header]
  <alert 1..3>         [alert:{id}, clickable → opens backend URL]
  No pressing items    [fallback, disabled]
───────────────────
On your radar          [disabled header]        ← if approaching non-empty
  <reminder 1..N>      [reminder:{id}, disabled]
───────────────────
Reminder due           [disabled header]        ← if active non-empty
  <reminder 1..N>      [reminder:{id}, disabled]
───────────────────
Quit Squirrel          [QUIT]
```

**Reminder tray items are disabled** (no click handler). Clicking a pressing alert opens `{BACKEND_ORIGIN}/notes/{task_id}` in the browser.

### No events emitted by tray/tray_alerts

Neither `tray.rs` nor `tray_alerts.rs` emit any Tauri events (`app.emit` / `window.emit`). The Rust daemon is completely isolated from the frontend.

---

## 3. Backend HTTP API (Python, server.py)

All reminder API runs on `http://127.0.0.1:3939`.

| Method | Route | Handler | Description |
|---|---|---|---|
| `GET` | `/api/reminders` | `api_reminders` (line 859) | Full `approaching[]` + `active[]` items |
| `PATCH` | `/api/reminder/{id}/dismiss` | `api_reminder_dismiss` (line 871) | Sets `reminder_dismissed` in vault file |
| `PATCH` | `/api/reminder/{id}/snooze` | `api_reminder_snooze` (line 884) | Sets `reminder_snoozed_until` in vault file |
| `GET` | `/api/home` | `api_home` (line 451) | Returns counts only: `{approaching_count, active_count}` |

**No read/unread tracking exists.** Reminder state is only: active, approaching, dismissed, or snoozed — all persisted as frontmatter fields in vault `.md` files.

**No server-side caching.** Every `/api/reminders` request re-scans the entire vault.

**No WebSocket or SSE.** The server is HTTP-only. No push channel from server to clients.

---

## 4. Reminder Data Schema

`ReminderItem` (TypeScript interface, api/client.ts:165–171):
```typescript
{
  id:            string;         // file stem e.g. "VISA-SETUP-001"
  title:         string;
  path:          string;         // vault-relative path
  reminder_date: string;         // "YYYY-MM-DD"
  proyecto:      string | null;  // parent project slug
}
```

No `read`, `unread`, `seen`, or `priority` fields exist.

**Source of truth:** vault `.md` files, frontmatter fields:
- `reminder_date: YYYY-MM-DD`
- `reminder_dismissed: YYYY-MM-DD`
- `reminder_snoozed_until: YYYY-MM-DD`

---

## 5. CLI Reminder Scanner (Python)

`apps/cli/lib/reminder_scanner.py` — one-shot synchronous vault scan.

- Walks `01-Proyectos-Activos` and `03-Areas` folders
- Skips: done/archived projects, no `reminder_date`, non-empty `reminder_dismissed`, future `reminder_snoozed_until`
- **Proximity buckets:** `days_ahead <= 0` → `active`; `1–7` → `approaching`; `> 7` → excluded

**No OS notification calls anywhere in Python code** (no `osascript`, `notify-send`, `terminal-notifier`). The CLI only outputs JSON to stdout.

---

## 6. Desktop Frontend (React, apps/desktop/src/)

### What exists

Single-view popup app (no routing). Components: `FocusWidget`, `DeadlinesWidget`, `ParakeetWidget`, `CaptureModal`, `FocusPickerModal`, `Toast`.

**No notification UI components exist.** No notification center, no unread badge, no notification list, no alert panel.

**Tauri plugin imports (lib/plugins.ts:11–13):**  
`isPermissionGranted` from `@tauri-apps/plugin-notification` is imported as a smoke check only. The import is **never called at runtime**. Comment says: *"feature code (notifications, store, autostart) starting in Unit 4 / Unit 6"*.

**No Tauri event listeners** for notifications. The only `listen` call is for deep-link events (`useDeepLink.ts:33`).

**No `invoke` calls** that trigger tray updates or notification state changes.

**State management:** React `useState`/`useEffect` only. No Zustand/Redux. No shared notification state or context.

---

## 7. Web UI Frontend (React, apps/backend/app/src/)

### RemindersWidget

`apps/backend/app/src/components/RemindersWidget.tsx`

- Fetches `/api/reminders` once on mount (no polling, no re-fetch on home refresh)
- Shows "On your radar" (approaching) with title/date badge — no action buttons
- Shows "Reminder due" (active) with dismiss and snooze controls
- **Optimistic updates:** removes items from local state immediately before API call resolves
- Dismiss/snooze errors are silently swallowed (`.catch(() => {})`)
- Returns `null` if no data or both lists empty

---

## 8. Gaps Relative to Desired In-App Notification Behavior

The following capabilities **do not exist** today:

| Capability | Status |
|---|---|
| Tray icon badge set to `Notification` state | `set_state` dead code, never called |
| Rust daemon emitting events to frontend | No `app.emit` / `window.emit` calls exist |
| In-app notification center UI in desktop app | No component exists |
| Unread/pending alert count in frontend | No state tracking |
| Menu bar item "View Notifications" | Not present in tray menu |
| Desktop frontend dismiss/snooze controls | Only in web UI RemindersWidget |
| Notification count badge on tray icon | Icon states exist but badge never set |
| `pending_clicks` handler in Rust | Populated but never consumed |

---

## 9. What the Daemon Already Knows (and Already Polls)

The Rust daemon already does:
- Polls `/api/reminders` every 30 s
- Maintains active/approaching reminder lists in memory
- Updates tray menu with reminder sections on every poll
- Has `TauriNotificationState` struct with all rate-limiting logic

The daemon does **not** need to know about the new notification center — it already has the data; it just needs to route alerts to the frontend instead of (or in addition to) OS-level notifications.
