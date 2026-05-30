# In-App Notification Center — Low-Level Design

## Architecture

### Data flow — write path (daemon fires a notification)

```
  apps/cli/lib/reminder_scanner.py          apps/cli/lib/status_aggregator.py
  scan_vault_reminders()                    aggregate_status()
        │                                         │
        └──────────────────┬──────────────────────┘
                           │ JSON over HTTP
                           ▼
              apps/backend/server.py  (port 3939)
              ┌──────────────────────────────────────┐
              │ GET /api/reminders  →  approaching[] │
              │                        active[]      │
              │ GET /api/home       →  pressing[]    │
              │ GET /api/me         →  notifications │
              │                        { in_app,     │
              │                          os_popups } │
              └──────────────────────────────────────┘
                           │ reqwest (HTTP poll, 30 s)
                           ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  apps/desktop/src-tauri/src/tray_alerts.rs                          │
  │                                                                     │
  │  start_polling()  ←  tauri::async_runtime::spawn                    │
  │    │                                                                │
  │    ├─ fetch_notif_settings()  →  GET /api/me                        │
  │    │    if in_app == false  →  return early (skip everything)       │
  │    │                                                                │
  │    ├─ fetch_pressing()        →  GET /api/home                      │
  │    ├─ fetch_reminders()       →  GET /api/reminders                 │
  │    │                                                                │
  │    ├─ tray::update_alerts()   →  rebuild tray menu items            │
  │    │                                                                │
  │    └─ for each new alert/reminder:                                  │
  │         │                                                           │
  │         ├─ [dedup] SELECT FROM notifications                        │
  │         │         WHERE item_id=? AND date(fired_at)=date('now')    │
  │         │         → skip if row exists                              │
  │         │                                                           │
  │         ├─ [write] INSERT INTO notifications                        │◄──┐
  │         │         (type, item_id, title, body, item_url, fired_at)  │   │
  │         │                                                           │   │ rusqlite
  │         ├─ [count] SELECT COUNT(*) WHERE read_at IS NULL            │   │ (WAL mode)
  │         │                                                           │   │
  │         ├─ tray::set_state(Notification | Normal)                   │   │
  │         │                                                           │   │
  │         ├─ app.emit("squirrel:notif-updated", unread_count)         │   │
  │         │                                                           │   │
  │         └─ if os_popups == true:                                    │   │
  │              app.notification().builder()                           │   │
  │                .title().body().show()   →  macOS Notification Center│   │
  └─────────────────────────────────────────────────────────────────────┘   │
                                                                             │
  ~/.squirrel/state/squirrel.db  ◄────────────────────────────────────────┘
  ┌───────────────────────────────────────┐
  │  TABLE notifications                  │
  │  id            PK AUTOINCREMENT       │
  │  type          pressing|reminder_act. │
  │  item_id       TEXT (slug)            │
  │  title         TEXT                   │
  │  body          TEXT                   │
  │  item_url      TEXT                   │
  │  fired_at      TEXT (ISO 8601)        │
  │  read_at       TEXT  ← NULL=unread    │
  │  dismissed_at  TEXT  ← NULL=active    │
  └───────────────────────────────────────┘
          │ sqlite3 (Python, read/write)
          ▼
  apps/backend/server.py  (new handlers)
  ┌────────────────────────────────────────────────────────┐
  │  GET  /api/notifications?limit=3&unread=true           │
  │  POST /api/notifications/read-all                      │
  │  PATCH /api/notification/{id}/read                     │
  │  PATCH /api/notification/{id}/dismiss                  │
  │  POST /api/settings/notifications  →  config.toml      │
  └────────────────────────────────────────────────────────┘
```

### Data flow — read path (frontend renders the center)

```
  app.emit("squirrel:notif-updated", unread_count)
                    │  Tauri event (IPC)
                    ▼
  apps/desktop/src/hooks/useNotifications.ts   (new)
  ┌──────────────────────────────────────────────────┐
  │  listen("squirrel:notif-updated")                │
  │    → fetch GET /api/notifications                │
  │            ?limit=3&unread=true                  │
  │    → setState({ items, unreadCount })            │
  │                                                  │
  │  loadAll()  → fetch without limit/unread filter  │
  │  markAllRead()  → POST /api/notifications/read-all│
  │  dismiss(id)  → PATCH /api/notification/{id}/... │
  └──────────────────────┬───────────────────────────┘
                         │ props / hook return
                         ▼
  apps/desktop/src/components/NotificationCenter.tsx  (new)
  ┌──────────────────────────────────────────────────────────┐
  │                                                          │
  │  renders when unreadCount > 0                            │
  │                                                          │
  │  ┌────────────────────────────────────────────────────┐  │
  │  │ ● pressing   TASK-001  45d overdue                 │  │
  │  │              [Go to →]              [✕]            │  │
  │  │              openUrl(item_url)  dismiss(id)        │  │
  │  │                                                    │  │
  │  │ ● reminder   VISA-001  Due today                   │  │
  │  │              [Go to →]              [✕]            │  │
  │  └────────────────────────────────────────────────────┘  │
  │  ── showing 2 of 5 ──  [View all]  [Mark all read]       │
  │                         loadAll()   markAllRead()         │
  └──────────────────────────────────────────────────────────┘
                         │ mounted above FocusWidget
                         ▼
  apps/desktop/src/App.tsx
  ┌──────────────────────────────────────┐
  │  <header />                          │
  │  <NotificationCenter />   ← NEW      │
  │  <FocusWidget />                     │
  │  <DeadlinesWidget />                 │
  │  <ParakeetWidget />                  │
  └──────────────────────────────────────┘
```

### Tray menu changes — `tray.rs`

```
  Before                          After
  ──────────────────────────────────────────────────────────
  Open Squirrel                   Open Squirrel
  Open Web UI                     Open Web UI
  ───────────                     ───────────
  PRESSING NOW                    PRESSING NOW
    TASK-001 → opens URL            TASK-001 → opens URL  (unchanged)
  ───────────                     ───────────
  REMINDERS DUE                   REMINDERS DUE
    VISA-001  [disabled]            VISA-001 → opens URL  ← re-enabled
  ───────────                     ───────────
  Quit Squirrel                   Notifications (3)  →  show_main_window()
                                  ───────────                ↑ NEW
                                  Quit Squirrel
```

### Settings flow — `config.toml` ↔ Web UI ↔ Daemon

```
  ~/.squirrel/config.toml
  [notifications]
  in_app    = true
  os_popups = false
       │ read by Python on each /api/me request
       │ written by POST /api/settings/notifications
       ▼
  apps/backend/app/src/pages/SettingsPage.tsx
  ┌──────────────────────────────────────────────────┐
  │  🔔 Notifications                                │
  │     In-app notifications   [●  ON  ]             │ → in_app
  │     OS notifications       [○  OFF ]             │ → os_popups
  │                                                  │
  │  onChange → POST /api/settings/notifications     │
  │          → mutate() useMe cache                  │
  └──────────────────────────────────────────────────┘
       │ next poll cycle (≤ 30 s), daemon re-reads
       ▼
  tray_alerts.rs: fetch_notif_settings() → GET /api/me
  flags applied immediately, no restart required
```

## Components

### 1. SQLite — `notifications` table

Added to `apps/cli/lib/db.py` `init_schema()`. Migration is additive (`CREATE TABLE IF NOT EXISTS`). Schema:

```sql
CREATE TABLE IF NOT EXISTS notifications (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  type         TEXT NOT NULL,
  item_id      TEXT NOT NULL,
  title        TEXT NOT NULL,
  body         TEXT NOT NULL,
  item_url     TEXT,
  fired_at     TEXT NOT NULL,
  read_at      TEXT,
  dismissed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_notifications_item_day
  ON notifications(item_id, date(fired_at));
```

### 2. Rust daemon — `tray_alerts.rs`

**Settings check (per poll cycle):**
- `fetch_notif_settings(&app) -> NotifSettings { in_app: bool, os_popups: bool }`
- Hits `GET /api/me`, reads `notifications` key
- If `in_app == false`: skip all notification logic, return early

**Deduplication before INSERT:**
```sql
SELECT id FROM notifications
WHERE item_id = ? AND date(fired_at) = date('now')
LIMIT 1
```
Insert only if no row found.

**After INSERT:**
```sql
SELECT COUNT(*) FROM notifications
WHERE read_at IS NULL AND dismissed_at IS NULL
```
→ Call `set_state(app, IconState::Notification)` if count > 0, else `IconState::Normal`
→ Call `app.emit("squirrel:notif-updated", unread_count)`

**OS popup guard:**
```rust
if settings.os_popups {
    app.notification().builder().title(&title).body(&body).show();
}
```

**`TauriNotificationState` additions:**
- `notif_db_path: PathBuf` — resolved once at startup from config state dir

### 3. Python HTTP server — `server.py`

**New routes (added to ROUTES table):**

| Method | Pattern | Handler |
|---|---|---|
| `GET` | `/api/notifications` | `api_notifications` |
| `POST` | `/api/notifications/read-all` | `api_notifications_read_all` |
| `PATCH` | `/api/notification/(?P<nid>[0-9]+)/read` | `api_notification_read` |
| `PATCH` | `/api/notification/(?P<nid>[0-9]+)/dismiss` | `api_notification_dismiss` |
| `POST` | `/api/settings/notifications` | `api_settings_notifications` |

**`GET /api/notifications` query params:**
- `limit=N` — cap rows returned (default: no limit)
- `unread=true` — filter to `read_at IS NULL AND dismissed_at IS NULL`

**Response shape:**
```json
{
  "items": [
    {
      "id": 42,
      "type": "reminder_active",
      "item_id": "VISA-SETUP-001",
      "title": "VISA-SETUP-001",
      "body": "Due today",
      "item_url": "http://127.0.0.1:3939/notes/VISA-SETUP-001",
      "fired_at": "2026-05-30T14:22:00",
      "read_at": null,
      "dismissed_at": null
    }
  ],
  "unread_count": 3,
  "total_count": 7
}
```

**`POST /api/settings/notifications` body:**
```json
{ "in_app": true, "os_popups": false }
```
Persisted to `config.toml` under `[notifications]`. `/api/me` reads and includes these values.

**`/api/me` additions:**
```json
{
  "notifications": {
    "in_app": true,
    "os_popups": false
  }
}
```

### 4. Desktop frontend — `apps/desktop/src/`

**`hooks/useNotifications.ts`** (new)
```typescript
// listen to Tauri event → refetch /api/notifications?limit=3&unread=true
// returns { items, unreadCount, markRead, dismiss, loadAll }
```

**`components/NotificationCenter.tsx`** (new)
- Renders when `items.length > 0` or `unreadCount > 0`
- Row layout: `[● type-dot] title / body … [Go to →] [✕]`
- `openUrl(item.item_url)` via `tauri-plugin-opener` (already used elsewhere)
- "View all" toggles `showAll` state → re-fetches without `limit`
- "Mark all read" → `POST /api/notifications/read-all` → clears badge

**`App.tsx` changes:**
- Mount `<NotificationCenter />` between header and `<FocusWidget />`
- `unreadCount` from `useNotifications()` drives no additional badge UI — tray icon badge is handled entirely in Rust

### 5. Tray menu — `tray.rs`

**Reminder items re-enabled:**
- Remove `disabled()` call on reminder menu items
- Handler: `ids::REMINDER_PREFIX` → `open_url(app, item_url)` (same as pressing alerts)
- `item_url` must be threaded through `update_alerts()` call from `tray_alerts.rs`

**New "View Notifications" menu item:**
```
ids::VIEW_NOTIFICATIONS = "view_notifications"
```
- Shown only when `unread_count > 0`, label: `"Notifications (N)"`
- Handler: `show_main_window(app)` (opens the tray popup where NotificationCenter renders)
- Positioned just above the final separator before "Quit"

### 6. Web UI Settings — `SettingsPage.tsx`

New `<SettingsSection icon="notifications" title="Notifications" subtitle="Control how Squirrel surfaces alerts">` block with three toggle rows:
- **In-app notifications** — `in_app` flag, master toggle
- **Menu bar badge** — not a separate flag; follows `in_app` (badge is part of the in-app system)
- **OS notifications** — `os_popups` flag, independent

Toggle component: same button-group style as theme picker, or a simple checkbox — matches existing design language.

## Constraints

- Rust opens SQLite directly via `rusqlite` (WAL mode, same path as Python: `~/.squirrel/state/squirrel.db`). WAL mode allows concurrent reads from Python and writes from Rust without locking.
- The Rust daemon must not crash if the DB is absent at startup — it should create the table on first write if needed (call `init_schema` equivalent in Rust via raw SQL).
- Settings flags are read on each poll cycle (not cached in Rust state) so changes in the Web UI take effect within one poll interval (≤ 30 s) without restart.
- `item_url` for pressing alerts: `http://127.0.0.1:3939/notes/{alert.id}` — same as existing tray click handler.
- `item_url` for reminders: `http://127.0.0.1:3939/notes/{reminder.id}` — same pattern.

## Key Decisions

| Decision | Rationale |
|---|---|
| Rust writes SQLite directly (rusqlite) | Avoids HTTP round-trip for write path; WAL mode makes concurrent access safe |
| Settings read from `/api/me` per poll | No config-file parsing in Rust; Python already owns config.toml |
| OS notifications default OFF | User asked to move away from OS popups; opt-in is safer |
| Approaching reminders excluded from notification center | They already appear in the tray menu; adding them to the center would duplicate and clutter |
| In-app flag is master toggle | If in_app=false, there is nothing to show; OS popups alone without the center defeats the purpose |
| Badge driven by Rust unread count | Rust already has the count after INSERT; avoids a frontend→Rust invoke for badge updates |
| Deduplication by item_id + calendar day | Prevents duplicate rows when daemon polls every 30 s for the same active alert |

## Out of Scope

- Per-notification snooze from the in-app center (stays in Web UI RemindersWidget)
- Notification sounds
- Windows / Linux support
- Approaching reminders in notification center
- Multi-vault or multi-user notification state
