# In-App Notification Center — Low-Level Design

## Architecture

```
~/.squirrel/state/squirrel.db
┌──────────────────────────────────────────────────────────┐
│  TABLE notifications                                      │
│  id           INTEGER PK AUTOINCREMENT                    │
│  type         TEXT  'pressing' | 'reminder_active'        │
│  item_id      TEXT  alert/reminder slug                   │
│  title        TEXT  display label                         │
│  body         TEXT  subtitle / detail text                │
│  item_url     TEXT  http://127.0.0.1:3939/notes/{id}      │
│  fired_at     TEXT  ISO 8601 timestamp                    │
│  read_at      TEXT  NULL = unread                         │
│  dismissed_at TEXT  NULL = not dismissed                  │
└──────────────────────────────────────────────────────────┘
         ▲ rusqlite                      ▲ sqlite3 (Python)
         │                               │
  Rust daemon                     Python HTTP server (3939)
  tray_alerts.rs                  server.py + db.py
  ─────────────────               ─────────────────────────
  • reads notif settings          • GET  /api/notifications
    from /api/me on each poll     • POST /api/notifications/read-all
  • deduplicates by item_id       • PATCH /api/notification/{id}/read
    + calendar day before INSERT  • PATCH /api/notification/{id}/dismiss
  • calls set_state(Notification) • POST /api/settings/notifications
    when unread > 0               • /api/me includes notif settings
  • calls app.emit(               
    "squirrel:notif-updated",    
    unread_count)                 
  • guards OS popup behind        
    os_popups flag                
         │                               │
         └──────────────┬────────────────┘
                        │
              Tauri Desktop Frontend
              apps/desktop/src/
              ─────────────────────────────────────
              useNotifications() hook
              • listens: "squirrel:notif-updated"
              • fetches: GET /api/notifications?limit=3&unread=true
              • state: { items[], unreadCount, showAll }

              NotificationCenter component
              • renders inside existing tray popup (App.tsx)
              • shows up to 3 unread rows by default
              • "View all (N)" expands full list
              • each row: title, body, [Go to →], [✕ Dismiss]
              • "Mark all read" clears badge

              App.tsx update
              • mounts NotificationCenter above FocusWidget
              • tray badge driven by unreadCount from hook
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
