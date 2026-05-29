# Tauri Native Notifications — Low-Level Design

## Architecture

```
tray_alerts.rs (30s loop)
  └── every tick: update tray menu        ← unchanged
  └── every tick: call check_notifications(state, alerts)
        ├── sleep-wake guard  (elapsed >> POLL_INTERVAL → reset timer)
        ├── 2-min interval guard           (last_check_at)
        ├── daily cap guard                (dialogs_today / dialogs_date)
        ├── per-item cooldown filter       (last_notified[id] < 1h)
        └── send via tauri-plugin-notification
              ↓ click fires Tauri event
App.tsx  onAction listener
  ├── extract task URL from notification data
  ├── if status.online → openUrl(task_url)
  └── if !status.online → send secondary "Backend offline" notification
```

```
reminder-daemon.sh
  └── pgrep -x "Squirrel" → exit 0 (log tauri-app-running)
```

## Key Data Structures

**`TauriNotificationState`** — managed via `Mutex<TauriNotificationState>` in Tauri app state:

```rust
struct TauriNotificationState {
    // Per-item 1h cooldown: item_id → Instant of last send
    last_notified: HashMap<String, Instant>,
    // Daily cap counters
    dialogs_today: u32,        // reset when dialogs_date changes
    dialogs_date: String,      // YYYY-MM-DD local date
    // 2-minute notification interval guard
    last_check_at: Instant,
    // Sleep detection: anchor set before each tokio::sleep
    last_poll_at: Instant,
    // Map notification_id → web-UI task URL for click handling
    pending_clicks: HashMap<i32, String>,
    next_id: i32,
}
```

## Sleep / Hibernation Detection

Inside the `tray_alerts` polling loop, before each `tokio::time::sleep(POLL_INTERVAL)`:
1. Record `last_poll_at = Instant::now()` in state.
2. After sleep returns, compute `actual_elapsed = last_poll_at.elapsed()`.
3. If `actual_elapsed > POLL_INTERVAL + SLEEP_THRESHOLD` (threshold = 15 s), a sleep/wake event is inferred.
4. On detected wake: set `state.last_check_at = Instant::now()` — this forces a fresh 2-minute wait before any notification fires.

Constants:
```rust
const POLL_INTERVAL:        Duration = Duration::from_secs(30);   // unchanged
const NOTIF_INTERVAL:       Duration = Duration::from_secs(120);  // 2 min
const SLEEP_THRESHOLD:      Duration = Duration::from_secs(15);
const ITEM_COOLDOWN:        Duration = Duration::from_secs(3600); // 1h
const MAX_DIALOGS_PER_DAY:  u32      = 8;
```

## Notification Send Flow

`check_notifications(app, state, alerts)`:

1. **Sleep-wake guard**: update `last_poll_at`, detect wake as above.
2. **Interval guard**: if `Instant::now() - last_check_at < NOTIF_INTERVAL`, return early.
3. **Date rollover**: if today's local date ≠ `dialogs_date`, reset `dialogs_today = 0` and update `dialogs_date`.
4. **Daily cap**: if `dialogs_today >= MAX_DIALOGS_PER_DAY`, return early.
5. **Candidate filtering**: from `alerts`, keep items where `last_notified[id]` is absent or older than `ITEM_COOLDOWN`. Cap at 3 per check.
6. For each candidate:
   - Assign `id = state.next_id++`.
   - Build task URL: `format!("{}/notes/{}", BACKEND_ORIGIN, alert.id)`.
   - Store `state.pending_clicks.insert(id, task_url)`.
   - Send notification via `app.notification().builder().id(id).title(…).body(…).show()`.
   - Update `state.last_notified.insert(alert.id.clone(), Instant::now())`.
   - Increment `state.dialogs_today`.
7. Update `state.last_check_at = Instant::now()`.

## Click Handling

Notification action events are bridged to the React layer via Tauri's event system (tauri-plugin-notification emits a Tauri event for each action). In `App.tsx`:

```ts
// on mount
onAction((action) => {
  const url = action.notification.extra?.taskUrl;
  if (!url) return;
  if (!status.online) {
    sendNotification({ title: "Squirrel", body: "Backend offline — start the server first." });
    return;
  }
  openUrl(url).catch((err) => console.error("[App] notification openUrl failed:", err));
});
```

The `extra.taskUrl` value is set when the notification is built on the Rust side by encoding the task URL into the notification's extra data map.

## Daemon Guard

At the top of the `main()` body in `reminder-daemon.sh`, after config loading and before the item-selection loop:

```bash
if pgrep -x "Squirrel" >/dev/null 2>&1; then
    log "tauri-app-running: skipping daemon notifications"
    exit 0
fi
```

The pgrep process name must match the bundle's executable name exactly. The daemon's workday-window check, cadence, cap accounting, and state-file writes are all untouched.

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Extend 30s loop rather than new loop | Single async task, no extra thread; interval guard achieves the 2-min cadence without spawning |
| In-memory state only (no disk persistence) | Simplicity; state resets on restart are acceptable since the 1h cooldown is short |
| `pending_clicks` map for click→URL routing | Avoids encoding URLs in notification titles/bodies; keeps notification copy clean |
| React-side `onAction` for click handling | tauri-plugin-notification's action callback surface is JS-primary; Rust-side listen is possible but more complex for a thin action |
| pgrep guard in daemon | Zero shared state needed; stateless boolean check; daemon needs no knowledge of Tauri's internal state |

## Out of Scope

- Tauri popup scroll/highlight on notification click (browser-only path)
- Configurable interval or cooldown
- Notification permission request UI (system dialog fires automatically on first `show()`)
- Persistent daily-cap state across restarts
- Windows / Android notification paths
