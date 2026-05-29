# Tauri Native Notifications — EARS Specifications

## Unit 1: Notification polling interval and state

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL extend the existing `tray_alerts` 30-second polling loop to call a `check_notifications` function on every tick. |
| R-1.2 | `check_notifications` SHALL send notifications at most once per `NOTIF_INTERVAL` (2 minutes, hard-coded). THE SYSTEM SHALL track the time of the last notification check in `TauriNotificationState.last_check_at` and return early if `Instant::now() - last_check_at < NOTIF_INTERVAL`. |
| R-1.3 | `TauriNotificationState` SHALL be stored behind a `Mutex` in Tauri app state and initialised in `lib.rs` alongside the existing `PendingDeepLink` state. |
| R-1.4 | THE SYSTEM SHALL NOT persist `TauriNotificationState` to disk. State is in-memory only and resets to zero on app restart. |

## Unit 2: Sleep / hibernation handling

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | BEFORE each `tokio::time::sleep(POLL_INTERVAL)` call, THE SYSTEM SHALL record `Instant::now()` in `TauriNotificationState.last_poll_at`. |
| R-2.2 | AFTER the sleep returns, THE SYSTEM SHALL compute `actual_elapsed = last_poll_at.elapsed()`. IF `actual_elapsed > POLL_INTERVAL + SLEEP_THRESHOLD` (15 s), THE SYSTEM SHALL infer a sleep/wake event. |
| R-2.3 | WHEN a sleep/wake event is inferred, THE SYSTEM SHALL set `last_check_at = Instant::now()`, forcing a full `NOTIF_INTERVAL` (2 min) wait before the next notification batch can fire. |
| R-2.4 | THE SYSTEM SHALL log a single-line entry with tag `notif-wake-detected` and `actual_elapsed_secs` when a sleep/wake is inferred. |

## Unit 3: Daily cap and per-item cooldown

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL maintain a `dialogs_today` counter and a `dialogs_date` string (YYYY-MM-DD local date) in `TauriNotificationState`. |
| R-3.2 | WHEN `check_notifications` runs AND the current local date differs from `dialogs_date`, THE SYSTEM SHALL reset `dialogs_today = 0` and update `dialogs_date` to today. |
| R-3.3 | IF `dialogs_today >= MAX_DIALOGS_PER_DAY` (8), THE SYSTEM SHALL return early from `check_notifications` without sending any notification. |
| R-3.4 | THE SYSTEM SHALL maintain `last_notified: HashMap<String, Instant>` keyed on `alert.id`. |
| R-3.5 | WHEN selecting candidates for a notification batch, THE SYSTEM SHALL exclude any item whose `last_notified` entry is present AND within the past `ITEM_COOLDOWN` (1 hour). |
| R-3.6 | THE SYSTEM SHALL send at most 3 notifications per `check_notifications` invocation, taking the first 3 qualifying candidates from the pressing list. |

## Unit 4: Notification content and send

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN sending a notification for a pressing item, THE banner title SHALL be `"⏰ squirrel: <alert.id>"`. |
| R-4.2 | THE banner body SHALL be the same string produced by `alert.menu_label()` (e.g. `"3d overdue · PROJ-A"`). |
| R-4.3 | THE SYSTEM SHALL assign a monotonically increasing integer `id` to each notification and store `pending_clicks.insert(id, task_url)` where `task_url = format!("{}/notes/{}", BACKEND_ORIGIN, alert.id)`. |
| R-4.4 | THE notification SHALL be sent via `tauri_plugin_notification::NotificationExt` with the task URL encoded in the notification's extra data map under key `"taskUrl"`. |
| R-4.5 | AFTER a successful send, THE SYSTEM SHALL update `last_notified.insert(alert.id, Instant::now())` AND increment `dialogs_today`. |
| R-4.6 | IF the notification `show()` call returns an error, THE SYSTEM SHALL log tag `notif-send-failed` and the error message, and SHALL NOT increment `dialogs_today`. |
| R-4.7 | THE SYSTEM SHALL log tag `notif-sent` with `project_id` and `notification_id` for each successful send. |

## Unit 5: Click handling — open browser

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | WHEN the React `App` component mounts, THE SYSTEM SHALL register an `onAction` listener via `@tauri-apps/plugin-notification`. |
| R-5.2 | THE listener SHALL be torn down on `App` unmount (no listener leak). |
| R-5.3 | WHEN a notification action fires (default click action), THE SYSTEM SHALL extract `action.notification.extra.taskUrl`. IF `taskUrl` is absent or empty, THE SYSTEM SHALL log a console warning and take no further action. |
| R-5.4 | IF `taskUrl` is present AND `status.online` is `true`, THE SYSTEM SHALL call `openUrl(taskUrl)` via `@tauri-apps/plugin-opener`. |
| R-5.5 | IF `openUrl` rejects, THE SYSTEM SHALL log the error to the browser console with tag `notif-openurl-failed`. |
| R-5.6 | IF `taskUrl` is present AND `status.online` is `false`, THE SYSTEM SHALL NOT call `openUrl`. Instead, THE SYSTEM SHALL send a secondary macOS notification with title `"Squirrel"` and body `"Backend offline — start the server first."` |
| R-5.7 | THE secondary "backend offline" notification SHALL NOT count against `dialogs_today` (it is informational, not a deadline reminder). |

## Unit 6: Daemon cold-start fallback

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE `reminder-daemon.sh` script SHALL add a guard immediately after config loading: IF `pgrep -x "Squirrel"` exits 0, THE SYSTEM SHALL log tag `tauri-app-running` and exit 0 without emitting any notification. |
| R-6.2 | THE guard SHALL use the exact process name `Squirrel` (matching the Tauri bundle executable name). |
| R-6.3 | THE daemon's workday-window check, cadence logic, daily-cap counter, state-file reads/writes, and item-selection loop SHALL remain unchanged when the guard is not triggered. |
| R-6.4 | WHEN the Tauri app is not running, THE daemon SHALL behave identically to its pre-feature behaviour. |

## Unit 7: Notification permission

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | BEFORE the first `show()` call in `check_notifications`, THE SYSTEM SHALL check notification permission via `isPermissionGranted()`. |
| R-7.2 | IF permission is not granted, THE SYSTEM SHALL call `requestPermission()` once per app session (tracked in `TauriNotificationState`). |
| R-7.3 | IF permission remains denied after the request (user declined), THE SYSTEM SHALL set a `permission_denied: bool` flag in state and skip all subsequent notification sends for the remainder of the session. THE SYSTEM SHALL log tag `notif-permission-denied` once. |
| R-7.4 | THE permission check and request SHALL happen on the JS/React side, surfaced via a one-time effect in `App.tsx` that runs on mount. |

## Unit 8: Invariants preserved

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | THE 30-second tray-alerts polling loop behaviour (menu rebuild, `update_alerts`) SHALL remain unchanged. |
| R-8.2 | THE deep-link handler (`deep_link.rs`) and its `squirrel://` URL handling SHALL remain unchanged. |
| R-8.3 | THE `tray_alerts` module SHALL NOT add any new Cargo dependencies. `tauri-plugin-notification` is already declared in `Cargo.toml`. |
| R-8.4 | THE `BACKEND_ORIGIN` constant SHALL remain the single source of truth for the backend URL used in task URLs. |
| R-8.5 | THE daemon's `reminder-daemon.sh` pgrep guard SHALL be the ONLY change to the daemon script in this feature. All EARS from `native-notification-banner` and `manual-focus-pick` that govern daemon behaviour remain in force. |

## Unit 9: Logging and observability

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | ALL log entries from `check_notifications` SHALL use `tracing::info` (success) or `tracing::warn` (failure), consistent with existing `tray_alerts.rs` conventions. |
| R-9.2 | Tags emitted by `check_notifications` SHALL be exactly one of: `notif-sent`, `notif-send-failed`, `notif-wake-detected`, `notif-permission-denied`. |
| R-9.3 | Tags emitted by the daemon guard SHALL be exactly: `tauri-app-running`. |
