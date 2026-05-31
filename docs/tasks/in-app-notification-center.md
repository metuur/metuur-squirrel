# In-App Notification Center — Tasks

Spec: `docs/ears/in-app-notification-center.md`
Design: `docs/lld/in-app-notification-center.md`

Execution order: 1 → 5 → 4 → 2+3 → 8 → 6 → 7 → 9

---

## Unit 1: SQLite Schema

- [x] 1.1 Add `notifications` table to Python db.py (est: ~20m) `(mutex: db-schema)`
  - acceptance: R-1.1, R-1.2, R-1.3 — `init_schema()` in `apps/cli/lib/db.py` creates `notifications` table and `idx_notifications_item_day` index; connection uses WAL mode (already set on every connection in `get_conn`)
  - verify: `python3 -c "import sys; sys.path.insert(0,'apps/cli/lib'); import db, sqlite3; conn=db.get_conn('/tmp/sq-test'); db.init_schema(conn); print([r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()])"` — output includes `notifications`

- [x] 1.2 Create `notifications` table from Rust daemon on startup (deps: 1.1, est: ~30m) `(mutex: tray-alerts)`
  - acceptance: R-1.4 — `tray_alerts.rs` runs `CREATE TABLE IF NOT EXISTS notifications (...)` via rusqlite on first open; WAL mode set via `PRAGMA journal_mode=WAL`
  - verify: delete `~/.squirrel/state/squirrel.db`, launch app, confirm table exists with `sqlite3 ~/.squirrel/state/squirrel.db ".tables"`

---

## Unit 5: Python HTTP API — Settings

_Must land before Unit 2 (daemon reads /api/me) and Unit 9 (UI writes settings)._
_All stories in this unit touch `server.py` — run sequentially._

- [x] 5.1 Add `[notifications]` read/write to `config_loader.py` (est: ~30m) `(mutex: server-py)`
  - acceptance: R-5.4 — `load_notifications_settings(cfg) -> dict` returns `{"in_app": True, "os_popups": False}` when section absent; `save_notifications_settings(cfg, in_app, os_popups)` writes section to `config.toml`
  - verify: unit test — create temp `config.toml` without `[notifications]`, call loader, assert defaults; call saver, re-read file, assert values written

- [x] 5.2 Include `notifications` key in `GET /api/me` response (deps: 5.1, est: ~20m) `(mutex: server-py)`
  - acceptance: R-5.3 — `api_me` handler adds `"notifications": {"in_app": bool, "os_popups": bool}` to response JSON, reading from `config.toml` via 5.1
  - verify: `curl -s http://127.0.0.1:3939/api/me | python3 -m json.tool | grep -A3 notifications` — shows both flags

- [x] 5.3 Add `POST /api/settings/notifications` route (deps: 5.1, est: ~25m) `(mutex: server-py)`
  - acceptance: R-5.1, R-5.2 — new route persists `{in_app, os_popups}` to `config.toml`; returns HTTP 400 if either key missing; returns `{"success": true}` on success
  - verify: `curl -s -X POST http://127.0.0.1:3939/api/settings/notifications -H 'Content-Type: application/json' -d '{"in_app":true,"os_popups":false}'` → `{"success":true}`; check `config.toml` updated

---

## Unit 4: Python HTTP API — Notification Endpoints

_All stories touch `server.py` — run sequentially. Depends on Unit 1 (table must exist)._

- [x] 4.1 Add `GET /api/notifications` with `limit` and `unread` params (deps: 1.1, est: ~30m) `(mutex: server-py)`
  - acceptance: R-4.1, R-4.2, R-4.3 — returns `{items[], unread_count, total_count}`; `unread=true` filters to `read_at IS NULL AND dismissed_at IS NULL`; `limit=N` caps rows ordered by `fired_at DESC`
  - verify: insert 2 rows manually into DB, call `GET /api/notifications?limit=1&unread=true` → `items` has 1 item, `unread_count` is 2, `total_count` is 2

- [x] 4.2 Add `PATCH /api/notification/{id}/read` and `PATCH /api/notification/{id}/dismiss` (deps: 1.1, est: ~25m) `(mutex: server-py)`
  - acceptance: R-4.4, R-4.5 — `/read` sets `read_at=now()`; `/dismiss` sets `dismissed_at=now()`; both return `{"success": true}`; R-4.7 — neither updates tray icon
  - verify: insert row, call PATCH /read, re-query — `read_at` is non-null; call PATCH /dismiss on another row — `dismissed_at` is non-null

- [x] 4.3 Add `POST /api/notifications/read-all` (deps: 1.1, est: ~20m) `(mutex: server-py)`
  - acceptance: R-4.6 — sets `read_at=now()` for all rows where `read_at IS NULL`; returns `{"updated": N}`
  - verify: insert 3 unread rows, call POST /read-all → `{"updated": 3}`; re-query — all rows have `read_at` set

---

## Unit 2 + 3: Rust Daemon — Storage, Badge & OS Guard

_All stories touch `tray_alerts.rs` — run sequentially. Depends on Units 1 and 5._

- [x] 2.1 Fetch notification settings per poll cycle with early-exit guard (deps: 1.2, 5.2, est: ~20m) `(mutex: tray-alerts)`
  - acceptance: R-2.1, R-3.3, R-3.4 — `fetch_notif_settings()` calls `GET /api/me`, reads `.notifications`; if `in_app=false` poll returns immediately; defaults to `{in_app:true, os_popups:false}` on fetch failure
  - verify: set `in_app=false` in `config.toml`, observe no new rows in `notifications` table after one poll cycle

- [x] 2.2 Dedup check and INSERT into notifications with item_url (deps: 2.1, est: ~40m) `(mutex: tray-alerts)`
  - acceptance: R-2.2, R-2.3, R-2.8, R-2.9 — for each pressing alert and active reminder, SELECT for existing row with same `item_id` + today's date; INSERT only when absent; `item_url = "http://127.0.0.1:3939/notes/{item_id}"`
  - verify: trigger an active reminder, confirm exactly one row in `notifications` after multiple poll cycles within the same day; confirm `item_url` is set correctly

- [x] 2.3 Unread count → tray badge → Tauri event emit (deps: 2.2, est: ~30m) `(mutex: tray-alerts)`
  - acceptance: R-2.4, R-2.5, R-2.6, R-2.7 — after INSERT, `SELECT COUNT(*) WHERE read_at IS NULL AND dismissed_at IS NULL`; calls `set_state(Notification)` if count > 0, else `set_state(Normal)`; emits `"squirrel:notif-updated"` with unread count
  - verify: tray icon changes to notification state when a new alert row is inserted; reverts to normal after `POST /api/notifications/read-all`; event received in frontend devtools

- [x] 3.1 Guard OS notification calls behind `os_popups` flag (deps: 2.1, est: ~15m) `(mutex: tray-alerts)`
  - acceptance: R-3.1, R-3.2 — `check_notifications()` wrapped in `if settings.os_popups { ... }`; existing rate-limiting guards remain intact inside the block
  - verify: set `os_popups=false` in `config.toml`, trigger alert — no macOS system notification appears; set `os_popups=true` — system notification fires normally

---

## Unit 8: Tray Menu

_Depends on Unit 2 (unread count available in daemon state). Both stories touch `tray.rs`._

- [x] 8.1 Re-enable reminder tray items and thread `item_url` through `update_alerts()` (deps: 2.2, est: ~40m) `(mutex: tray-rs)`
  - acceptance: R-8.4, R-8.5, R-8.6 — `ReminderAlert` struct gains `item_url: String` field; `update_alerts()` signature updated to accept `item_url` per reminder; `disabled()` call removed from reminder menu items; click handler routes `ids::REMINDER_PREFIX` to `open_url(app, item_url)`
  - verify: reminder appears in tray menu, clicking it opens `http://127.0.0.1:3939/notes/{id}` in the browser

- [x] 8.2 Add conditional "Notifications (N)" menu item (deps: 2.3, 8.1, est: ~30m) `(mutex: tray-rs)`
  - acceptance: R-8.1, R-8.2, R-8.3 — `ids::VIEW_NOTIFICATIONS = "view_notifications"` item with label `"Notifications ({n})"` inserted above final separator when `unread_count > 0`; handler calls `show_main_window(app)`; item absent when count is zero
  - verify: with unread notifications, tray menu shows "Notifications (N)" item; clicking it opens popup; after "Mark all read", item disappears on next poll

---

## Unit 6: Desktop Frontend Hook

_Depends on Units 2 (Tauri event) and 4 (HTTP endpoints)._

- [x] 6.1 Implement `useNotifications` hook (deps: 2.3, 4.1, 4.2, 4.3, est: ~45m)
  - acceptance: R-6.1, R-6.2, R-6.3, R-6.4 — `apps/desktop/src/hooks/useNotifications.ts` registers `listen("squirrel:notif-updated")` on mount, unregisters on unmount; on event fires `GET /api/notifications?limit=3&unread=true`; exposes `{ items, unreadCount, markAllRead, dismiss, loadAll }`; `loadAll()` fetches without filters
  - verify: open popup with pending notifications — `items` populates; call `markAllRead()` — `unreadCount` drops to 0; call `loadAll()` — full history returned

---

## Unit 7: Desktop Frontend Component

_Depends on Unit 6._

- [x] 7.1 Implement `NotificationCenter` component (deps: 6.1, est: ~60m)
  - acceptance: R-7.1, R-7.2, R-7.3, R-7.4, R-7.5, R-7.6, R-7.7, R-7.8 — renders when `unreadCount > 0`; shows ≤3 rows by default; "View all (N)" triggers `loadAll()`; each row has title, body, "Go to →" (`openUrl(item_url)`), dismiss button (optimistic remove + PATCH); "Mark all read" calls `markAllRead()`; panel hides when count reaches 0
  - verify: with 5 unread notifications — panel shows 3 rows + "View all (5)"; dismiss one row — it disappears immediately; click "Go to →" — browser opens correct URL; "Mark all read" — panel hides

- [x] 7.2 Mount `NotificationCenter` in `App.tsx` (deps: 7.1, est: ~10m)
  - acceptance: R-7.1 — `<NotificationCenter />` inserted between `<header>` and `<FocusWidget />` in `apps/desktop/src/App.tsx`; `useNotifications()` called at App level and passed as props
  - verify: open tray popup with pending alert — notification panel visible above focus widget

---

## Unit 9: Web UI Settings

_Depends on Unit 5._

- [x] 9.1 Add Notifications section to `SettingsPage.tsx` (deps: 5.2, 5.3, est: ~40m)
  - acceptance: R-9.1, R-9.2, R-9.3, R-9.4, R-9.5, R-9.6 — new `<SettingsSection icon="notifications" title="Notifications">` block with "In-app notifications" and "OS notifications" toggles reading from `me.notifications`; `onChange` calls `POST /api/settings/notifications` + `mutate()`; when `in_app=false` OS toggle is visually disabled; on API failure toggle reverts + toast error shown
  - verify: toggle "OS notifications" ON — `config.toml` updates within seconds; toggle "In-app notifications" OFF — OS toggle greys out; disconnect backend, toggle — toast error appears and toggle reverts

---

## Dependency Summary

```
1.1 ──► 1.2
1.1 ──► 4.1, 4.2, 4.3
5.1 ──► 5.2, 5.3
5.2 ──► 2.1
1.2 ──► 2.1
2.1 ──► 2.2 ──► 2.3 ──► 8.2
                2.2 ──► 8.1 ──► 8.2
2.3 ──► 6.1
4.1 + 4.2 + 4.3 ──► 6.1
6.1 ──► 7.1 ──► 7.2
5.2 + 5.3 ──► 9.1
3.1 (after 2.1, before or alongside 2.2 — same file)
```

## Mutex groups

| Tag | Stories | Reason |
|---|---|---|
| `tray-alerts` | 1.2, 2.1, 2.2, 2.3, 3.1 | All modify `tray_alerts.rs` |
| `tray-rs` | 8.1, 8.2 | Both modify `tray.rs` |
| `server-py` | 4.1, 4.2, 4.3, 5.2, 5.3 | All modify `server.py` |
| `db-schema` | 1.1 | Modifies `db.py` schema (only one story, no contention) |
