# In-App Notification Center — EARS Specifications

## Unit 1: SQLite Schema

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL create a `notifications` table in `~/.squirrel/state/squirrel.db` with columns `id`, `type`, `item_id`, `title`, `body`, `item_url`, `fired_at`, `read_at`, `dismissed_at` if it does not already exist. |
| R-1.2 | THE SYSTEM SHALL create an index on `(item_id, date(fired_at))` to support deduplication queries. |
| R-1.3 | THE SYSTEM SHALL open the SQLite connection in WAL journal mode to allow concurrent reads from the Python server and writes from the Rust daemon. |
| R-1.4 | WHEN the Rust daemon starts and the `notifications` table does not exist, THE SYSTEM SHALL create it before attempting any INSERT. |

---

## Unit 2: Daemon — Notification Detection & Storage

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the daemon poll cycle runs and `settings.notifications.in_app` is `false`, THE SYSTEM SHALL skip all notification logic and return without inserting, emitting, or updating the tray icon. |
| R-2.2 | WHEN the daemon detects a pressing alert or active reminder and `in_app` is `true`, THE SYSTEM SHALL query the `notifications` table for an existing row with the same `item_id` and a `fired_at` date equal to the current calendar day. |
| R-2.3 | IF no matching row exists from R-2.2, THE SYSTEM SHALL INSERT a new row with `type`, `item_id`, `title`, `body`, `item_url`, `fired_at = now()`, `read_at = NULL`, `dismissed_at = NULL`. |
| R-2.4 | WHEN an INSERT is performed, THE SYSTEM SHALL query the count of rows where `read_at IS NULL AND dismissed_at IS NULL`. |
| R-2.5 | WHEN the unread count from R-2.4 is greater than zero, THE SYSTEM SHALL set the tray icon to `IconState::Notification`. |
| R-2.6 | WHEN the unread count from R-2.4 is zero, THE SYSTEM SHALL set the tray icon to `IconState::Normal`. |
| R-2.7 | WHEN an INSERT is performed, THE SYSTEM SHALL emit a Tauri event `"squirrel:notif-updated"` with the current unread count as the payload. |
| R-2.8 | WHERE `type` is `"pressing"`, THE SYSTEM SHALL set `item_url` to `http://127.0.0.1:3939/notes/{item_id}`. |
| R-2.9 | WHERE `type` is `"reminder_active"`, THE SYSTEM SHALL set `item_url` to `http://127.0.0.1:3939/notes/{item_id}`. |

---

## Unit 3: Daemon — OS Notification Guard

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN the daemon would fire a notification and `settings.notifications.os_popups` is `false`, THE SYSTEM SHALL skip the `tauri_plugin_notification` call entirely. |
| R-3.2 | WHEN `settings.notifications.os_popups` is `true`, THE SYSTEM SHALL fire an OS notification via `tauri_plugin_notification` subject to the existing rate-limiting guards (`MAX_DIALOGS_PER_DAY`, `ITEM_COOLDOWN`, `NOTIF_INTERVAL`). |
| R-3.3 | THE SYSTEM SHALL read `in_app` and `os_popups` values from `GET /api/me` on every poll cycle. |
| R-3.4 | IF `GET /api/me` fails or returns no `notifications` key, THE SYSTEM SHALL default to `in_app = true` and `os_popups = false`. |

---

## Unit 4: Python HTTP API — Notification Endpoints

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL expose `GET /api/notifications` returning `{ items[], unread_count, total_count }`. |
| R-4.2 | WHEN `GET /api/notifications` is called with query param `unread=true`, THE SYSTEM SHALL return only rows where `read_at IS NULL AND dismissed_at IS NULL`. |
| R-4.3 | WHEN `GET /api/notifications` is called with query param `limit=N`, THE SYSTEM SHALL return at most N rows ordered by `fired_at DESC`. |
| R-4.4 | THE SYSTEM SHALL expose `PATCH /api/notification/{id}/read` which sets `read_at = now()` for the given row and returns `{ success: true }`. |
| R-4.5 | THE SYSTEM SHALL expose `PATCH /api/notification/{id}/dismiss` which sets `dismissed_at = now()` for the given row and returns `{ success: true }`. |
| R-4.6 | THE SYSTEM SHALL expose `POST /api/notifications/read-all` which sets `read_at = now()` for all rows where `read_at IS NULL` and returns `{ updated: N }`. |
| R-4.7 | WHEN any of R-4.4, R-4.5, or R-4.6 complete successfully, THE SYSTEM SHALL not automatically update the tray icon — the daemon will correct the badge on the next poll cycle. |

---

## Unit 5: Python HTTP API — Settings

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL expose `POST /api/settings/notifications` accepting `{ "in_app": bool, "os_popups": bool }` and persisting the values to `config.toml` under `[notifications]`. |
| R-5.2 | WHEN either value is missing from the `POST /api/settings/notifications` body, THE SYSTEM SHALL return HTTP 400. |
| R-5.3 | THE SYSTEM SHALL include a `notifications` key in `GET /api/me` response with `{ "in_app": bool, "os_popups": bool }` reflecting the current `config.toml` values. |
| R-5.4 | IF `[notifications]` section is absent from `config.toml`, THE SYSTEM SHALL default to `in_app = true` and `os_popups = false`. |

---

## Unit 6: Desktop Frontend — useNotifications Hook

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE SYSTEM SHALL register a Tauri event listener for `"squirrel:notif-updated"` on mount and unregister it on unmount. |
| R-6.2 | WHEN the `"squirrel:notif-updated"` event fires, THE SYSTEM SHALL fetch `GET /api/notifications?limit=3&unread=true`. |
| R-6.3 | THE SYSTEM SHALL expose `{ items, unreadCount, markAllRead, dismiss, loadAll }` from the hook for use by `NotificationCenter`. |
| R-6.4 | WHEN `loadAll()` is called, THE SYSTEM SHALL fetch `GET /api/notifications` without `limit` or `unread` filters. |

---

## Unit 7: Desktop Frontend — NotificationCenter Component

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | WHEN `unreadCount > 0`, THE SYSTEM SHALL render the `NotificationCenter` panel above `FocusWidget` in the tray popup. |
| R-7.2 | THE SYSTEM SHALL display at most 3 notification rows by default. |
| R-7.3 | WHEN more than 3 notifications exist, THE SYSTEM SHALL render a "View all (N)" control that triggers `loadAll()` and shows the full list. |
| R-7.4 | EACH notification row SHALL display: title, body, a "Go to →" button, and a dismiss button. |
| R-7.5 | WHEN the user clicks "Go to →", THE SYSTEM SHALL call `openUrl(item.item_url)` via `tauri-plugin-opener`. |
| R-7.6 | WHEN the user clicks the dismiss button on a row, THE SYSTEM SHALL call `PATCH /api/notification/{id}/dismiss` and remove the row from the rendered list optimistically. |
| R-7.7 | THE SYSTEM SHALL render a "Mark all read" control that calls `POST /api/notifications/read-all` and clears the panel. |
| R-7.8 | WHEN `unreadCount` returns to zero after R-7.7, THE SYSTEM SHALL hide the `NotificationCenter` panel. |

---

## Unit 8: Tray Menu

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | WHEN `unread_count > 0`, THE SYSTEM SHALL display a "Notifications (N)" menu item in the tray menu positioned above the final separator before "Quit Squirrel". |
| R-8.2 | WHEN the "Notifications (N)" menu item is clicked, THE SYSTEM SHALL call `show_main_window()` to open the tray popup. |
| R-8.3 | WHEN `unread_count` is zero, THE SYSTEM SHALL hide or omit the "Notifications (N)" menu item. |
| R-8.4 | THE SYSTEM SHALL enable reminder tray menu items (currently disabled) so they respond to click events. |
| R-8.5 | WHEN a reminder tray menu item is clicked, THE SYSTEM SHALL call `open_url(app, item_url)` where `item_url` is `http://127.0.0.1:3939/notes/{reminder.id}`. |
| R-8.6 | THE SYSTEM SHALL pass `item_url` for each reminder through `update_alerts()` into the tray menu item data so the click handler can resolve it. |

---

## Unit 9: Web UI Settings Page

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | THE SYSTEM SHALL render a "Notifications" section in the Web UI Settings page with the same `SettingsSection` component used by Appearance and Obsidian Vault sections. |
| R-9.2 | THE SYSTEM SHALL display an "In-app notifications" toggle reflecting `me.notifications.in_app`. |
| R-9.3 | THE SYSTEM SHALL display an "OS notifications" toggle reflecting `me.notifications.os_popups`. |
| R-9.4 | WHEN either toggle is changed, THE SYSTEM SHALL call `POST /api/settings/notifications` with both current flag values and update the local `useMe` cache. |
| R-9.5 | WHEN `in_app` is toggled to `false`, THE SYSTEM SHALL disable the "OS notifications" toggle and visually indicate it is unavailable. |
| R-9.6 | IF `POST /api/settings/notifications` fails, THE SYSTEM SHALL revert the toggle to its previous state and show a toast error. |
