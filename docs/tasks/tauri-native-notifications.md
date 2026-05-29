# Tauri Native Notifications — Tasks

## Unit 1: Notification state and interval guard

- [x] 1.1 Add `TauriNotificationState` struct and constants to `tray_alerts.rs` (est: ~15m)
  - acceptance: R-1.3, R-1.4 — `TauriNotificationState` declared with fields `last_notified: HashMap<String, Instant>`, `dialogs_today: u32`, `dialogs_date: String`, `last_check_at: Instant`, `last_poll_at: Instant`, `pending_clicks: HashMap<i32, String>`, `next_id: i32`; constants `NOTIF_INTERVAL = 120s`, `SLEEP_THRESHOLD = 15s`, `ITEM_COOLDOWN = 3600s`, `MAX_DIALOGS_PER_DAY = 8u32` declared at module level
  - verify: `cargo check` passes; struct fields compile; constants visible to `start_polling`

## Unit 2: Sleep / hibernation handling

- [x] 1.2 Wire sleep/wake detection into the `start_polling` loop (deps: 1.1, est: ~20m)
  - acceptance: R-2.1, R-2.2, R-2.3, R-2.4 — before each `tokio::time::sleep(POLL_INTERVAL)`, `last_poll_at = Instant::now()` is recorded; after sleep, `actual_elapsed` is computed; if `actual_elapsed > POLL_INTERVAL + SLEEP_THRESHOLD`, `last_check_at` is reset to `Instant::now()` and `tracing::info!` logs tag `notif-wake-detected` with `actual_elapsed_secs`
  - verify: put machine to sleep briefly (or simulate by advancing time in a unit test); confirm log tag appears and `last_check_at` is updated; `cargo test` passes

## Unit 3: Daily cap, per-item cooldown, candidate selection

- [x] 1.3 Implement filtering logic inside `check_notifications` (deps: 1.1, est: ~25m)
  - acceptance: R-1.2, R-3.1–R-3.6 — `check_notifications` returns early if `Instant::now() - last_check_at < NOTIF_INTERVAL`; date-rollover resets `dialogs_today`; returns early if `dialogs_today >= MAX_DIALOGS_PER_DAY`; candidates are filtered by `ITEM_COOLDOWN`; at most 3 candidates selected per invocation
  - verify: unit test with mocked `TauriNotificationState` confirms: (a) early-return when interval not elapsed, (b) cap blocks at 8, (c) item with `last_notified < 1h` is excluded, (d) at most 3 items returned

## Unit 4: Notification send and lib.rs wiring

- [x] 1.4 Send notifications via `tauri-plugin-notification` and register state in `lib.rs` (deps: 1.2, 1.3, est: ~35m)
  - acceptance: R-4.1–R-4.7, R-8.1–R-8.4 — for each candidate: `id = next_id++`, `task_url` built from `BACKEND_ORIGIN + "/notes/" + alert.id`, `pending_clicks.insert(id, task_url)`, notification sent via `app.notification().builder().id(id).title(…).body(…).show()`; `last_notified[id]` and `dialogs_today` updated on success; `tracing::info!` logs `notif-sent`; on error logs `notif-send-failed`; `check_notifications` called each loop tick from `start_polling`; `TauriNotificationState` registered in `lib.rs` via `.manage(Mutex::new(TauriNotificationState::new()))` alongside `PendingDeepLink`
  - verify: run app with backend serving pressing items; wait ≤ 2 min; confirm macOS notification banner appears with correct title and body; confirm `notif-sent` in Tauri logs

## Unit 5: React — permission request and click handler

- [ ] 2.1 Request notification permission on mount and wire `onAction` click handler in `App.tsx` (est: ~25m)
  - acceptance: R-5.1–R-5.7, R-7.1–R-7.4 — on mount: `isPermissionGranted()` checked; if not granted, `requestPermission()` called once; if denied, `permission_denied` state prevents further requests; `onAction` listener registered on mount and torn down on unmount; on action: `taskUrl` extracted from `action.notification.extra.taskUrl`; if `status.online` → `openUrl(taskUrl).catch(err => console.error("[App] notif-openurl-failed", err))`; if `!status.online` → `sendNotification({ title: "Squirrel", body: "Backend offline — start the server first." })`
  - verify: (a) click a notification while backend is running → browser opens at correct `/notes/<id>` URL; (b) stop backend, click notification → secondary "Backend offline" banner appears, browser does not open; (c) DevTools confirms listener is registered and removed on HMR cycle

## Unit 6: Daemon cold-start fallback

- [ ] 3.1 Add `pgrep` guard to `reminder-daemon.sh` and extend bash unit test (est: ~15m)
  - acceptance: R-6.1–R-6.4 — inside `main()`, immediately after `log "Daemon run started"`: `if pgrep -x "Squirrel" >/dev/null 2>&1; then log "tauri-app-running: skipping daemon notifications"; exit 0; fi`; existing workday, cadence, cap, and state-file logic follow unchanged
  - verify: (a) with Squirrel.app running: `reminder-daemon.sh --force` exits 0 and logs `tauri-app-running`; (b) with Squirrel.app not running: `reminder-daemon.sh --force` proceeds to deadline scan as before; extend `test_reminder_daemon.sh` with a scenario that stubs `pgrep` to succeed and asserts the log tag
