# Phase 1 MVP — Desktop Shell — Tasks

Source spec: `docs/ears/phase-1-mvp-desktop-shell.md`
Architectural context: `docs/lld/phase-1-mvp-desktop-shell.md`

Conventions:
- `R-x.y` references the EARS requirement that gates the story.
- `deps:` references story IDs in this same file.
- `(mutex: tag)` blocks concurrent execution with other stories sharing the same tag.
- Estimates are wall-clock for a single engineer working in focus. ADHD buffer not pre-applied.

---

## Unit 0: Project bootstrap (prerequisite — not in EARS)

- [x] 0.1 Scaffold Tauri v2 + React + TypeScript project at repo root (est: ~45m)
  - acceptance: `pnpm tauri dev` (or chosen package manager) launches an empty Tauri v2 window on macOS; `cargo` builds cleanly; `src-tauri/tauri.conf.json` sets `productName="Squirrel"` and bundle identifier `com.squirrel.app`.
  - verify: `pnpm tauri dev` shows a blank window titled "Squirrel"; `pnpm tauri build` produces an unsigned `.app` bundle under `src-tauri/target/release/bundle/macos/`.

- [x] 0.2 Wire `tauri-plugin-notification`, `tauri-plugin-single-instance`, `tauri-plugin-store`, and `tauri-plugin-autostart` into `Cargo.toml` and `tauri.conf.json` (deps: 0.1, est: ~20m)
  - acceptance: All four plugins compile, are registered in `lib.rs` / `main.rs`, and their JS bindings install cleanly into the React app.
  - verify: `pnpm tauri dev` still boots; calling each plugin's smallest no-op JS API from the React console returns without error.

- [x] 0.3 Set up structured logging to `~/.squirrel/logs/squirrel.log` using `tracing` + `tracing-appender` (deps: 0.1, est: ~30m)
  - acceptance: Rust `info!`, `warn!`, `error!` macros append to `~/.squirrel/logs/squirrel.log` at INFO level; file is created on first write; existing log is appended to on subsequent runs.
  - verify: Start the app, observe log file exists, contains a startup line with ISO-8601 timestamp; restart and confirm the line is appended, not overwritten.

- [ ] 0.4 Ensure `~/.squirrel/` is created on first launch (deps: 0.3, est: ~10m)
  - acceptance: R-1.1 — WHEN the user launches Squirrel for the first time, THE SYSTEM SHALL create the directory `~/.squirrel/` if it does not exist.
  - verify: Delete `~/.squirrel/`, launch app, confirm the directory and `logs/` subdirectory now exist.

---

## Unit 1: Application lifecycle

- [ ] 1.1 Enforce single-instance via `tauri-plugin-single-instance` (deps: 0.2, est: ~20m)
  - acceptance: R-1.3 — IF a Squirrel process is already running and the user launches Squirrel again, THE SYSTEM SHALL focus the existing main window and SHALL NOT spawn a second tray icon or process.
  - verify: Launch the app twice from Finder; observe only one tray icon, and the existing window receives focus on the second launch.

- [ ] 1.2 Intercept window close → hide window without quitting (deps: 0.1, est: ~20m)
  - acceptance: R-1.4 — WHEN the user clicks the main window's close button, THE SYSTEM SHALL hide the window and SHALL NOT terminate the process. R-1.5 — WHILE the main window is hidden, THE SYSTEM SHALL keep the SQ menu bar icon visible and the fake watcher running.
  - verify: Open dashboard, click red close button, confirm window disappears, process is still alive in Activity Monitor, log file still receives entries.

- [ ] 1.3 Configure macOS as accessory/agent app (no persistent Dock icon while window hidden) (deps: 0.1, est: ~15m)
  - acceptance: R-1.7 — WHERE the host operating system is macOS, THE SYSTEM SHALL behave as a menu bar / accessory app (no persistent Dock icon while the window is hidden).
  - verify: Hide window; observe Dock has no Squirrel entry; re-open window via tray; observe behaviour matches a standard menu bar app.

- [ ] 1.4 Implement explicit quit path (deps: 1.2, 2.2, est: ~15m)
  - acceptance: R-1.6 — WHEN the user selects "Quit Squirrel" from the tray menu, THE SYSTEM SHALL terminate the process, remove the SQ icon from the menu bar, and stop the fake watcher.
  - verify: Click Quit Squirrel from tray; process exits in Activity Monitor; tray icon disappears; no orphan threads.

- [ ] 1.5 Emit lifecycle log lines for start/window-hide/window-show/watcher-on/watcher-off/notification-fired/notification-clicked/quit (deps: 0.3, est: ~25m)
  - acceptance: R-1.8 — THE SYSTEM SHALL write log entries to `~/.squirrel/logs/squirrel.log` at INFO level for every lifecycle event listed.
  - verify: Walk through each event (launch, hide window, show window, toggle watcher off/on, wait for event, click notification, quit); confirm each produces a distinct INFO log line.

---

## Unit 2: Tray icon and tray menu

- [ ] 2.1 Create four SQ icon assets (Normal, Notification, Processing, Error) at all required resolutions and wire them as bundled resources (est: ~40m)
  - acceptance: R-2.1 — THE SYSTEM SHALL support exactly four SQ icon states: Normal, Notification, Processing, Error. Assets exist at 16/32/64/128/256px (or Tauri's required template sizes for macOS menu bar) and are visually distinguishable.
  - verify: Bundle resources include all four files; load each from Rust and confirm `image::open()` succeeds for every variant.

- [ ] 2.2 Install tray icon at startup with the five-item menu in the exact order from R-2.5 (deps: 0.1, 2.1, est: ~45m)
  - acceptance: R-1.2 — WHEN the user launches Squirrel, THE SYSTEM SHALL display an SQ icon in the macOS menu bar within 2 seconds of process start. R-2.5 — THE SYSTEM SHALL expose a tray menu containing exactly these items, in order: Open Squirrel, Background Watcher (On/Off toggle), Settings, View Logs, Quit Squirrel.
  - verify: Launch app; stopwatch ≤2s until SQ icon appears in menu bar; click icon and confirm menu items appear in the specified order.

- [ ] 2.3 Set Normal icon state on startup with no pending events (deps: 2.2, est: ~10m)
  - acceptance: R-2.2 — WHEN the application starts and no events are pending, THE SYSTEM SHALL set the SQ icon to the Normal state.
  - verify: Fresh launch; visual confirmation icon is Normal variant.

- [ ] 2.4 Implement icon state machine API (`set_icon_state(state)`) and developer-only command exposed to dashboard (deps: 2.2, est: ~25m)
  - acceptance: R-2.9 — THE SYSTEM SHALL provide a developer-only command to force any of the four icon states for verification purposes, callable from the dashboard.
  - verify: From React devtools or hidden dashboard control, invoke command with each of the four states; observe icon swap each time.

- [ ] 2.5 Wire tray "Open Squirrel" → show + focus main window; reset icon to Normal (deps: 2.2, 2.4, 1.2, est: ~15m)
  - acceptance: R-2.4 (part 1) — WHEN the user opens the main window via the tray menu's "Open Squirrel" item, THE SYSTEM SHALL reset the SQ icon to the Normal state.
  - verify: Force icon to Notification state via 2.4's dev command; click "Open Squirrel"; window appears and icon returns to Normal.

- [ ] 2.6 Wire tray "View Logs" → opens `~/.squirrel/logs/squirrel.log` (or its parent dir) in OS default file viewer (deps: 2.2, 0.3, est: ~15m)
  - acceptance: R-2.8 — WHEN the user selects "View Logs" from the tray menu, THE SYSTEM SHALL open `~/.squirrel/logs/squirrel.log` (or its containing directory) in the operating system's default file viewer.
  - verify: Click "View Logs"; Finder reveals the log file (or opens it in Console/text editor).

- [ ] 2.7 Wire tray "Background Watcher" toggle item with visual checkmark state (deps: 2.2, 3.1, est: ~20m, mutex: watcher-toggle)
  - acceptance: Menu item displays current On/Off state with a checkmark or label change.
  - verify: Toggle the item; checkmark/label flips; toggle again returns to original.

- [ ] 2.8 Toggle Off behaviour: stop watcher emissions, set icon to Error (gray) (deps: 2.7, 3.1, 2.4, est: ~15m, mutex: watcher-toggle)
  - acceptance: R-2.6 — WHEN the user toggles "Background Watcher" in the tray menu to Off, THE SYSTEM SHALL stop emitting simulated events AND set the SQ icon to the Error state.
  - verify: Toggle Off; observe no notifications for ≥120s; icon shows Error variant.

- [ ] 2.9 Toggle On behaviour: resume 60s emissions, set icon to Normal (deps: 2.7, 3.1, 2.4, est: ~10m, mutex: watcher-toggle)
  - acceptance: R-2.7 — WHEN the user toggles "Background Watcher" in the tray menu to On, THE SYSTEM SHALL resume emitting simulated events on the standard 60-second interval AND set the SQ icon to the Normal state.
  - verify: After 2.8, toggle back On; icon returns to Normal; a `SimulatedEvent` fires within ~60s.

- [ ] 2.10 Wire tray "Settings" as inert placeholder menu item (disabled or no-op) (deps: 2.2, est: ~5m)
  - acceptance: Settings item appears in menu (per R-2.5 ordering) but takes no action when clicked in Phase 1.
  - verify: Click Settings; nothing crashes; no window opens (Phase 1 has no Settings UI).

---

## Unit 3: Background watcher (Phase 1 simulated)

- [ ] 3.1 Implement Rust async `SimulatedEvent` emitter on a tokio interval, gated by a `watcher_enabled: AtomicBool` (deps: 0.1, est: ~40m)
  - acceptance: R-3.1 — WHILE the application is running AND the Background Watcher setting is On, THE SYSTEM SHALL emit one `SimulatedEvent` every 60 seconds (±2 seconds tolerance). R-3.2 — THE `SimulatedEvent` SHALL include a unique identifier and a timestamp. R-3.4 — WHILE the Background Watcher setting is Off, THE SYSTEM SHALL NOT emit `SimulatedEvent`s.
  - verify: Run app with watcher on; instrument log shows event emitted at ~60s ±2s; flip flag off; no further emissions observed across ≥3 expected ticks; flip on; emissions resume.

- [ ] 3.2 Connect `SimulatedEvent` → notification firing + icon swap to Notification + JS event broadcast (deps: 3.1, 2.4, 4.2, est: ~25m)
  - acceptance: R-3.3 — WHEN a `SimulatedEvent` is emitted, THE SYSTEM SHALL trigger a native notification AND update the SQ icon to the Notification state AND broadcast the event to the React UI.
  - verify: Open dashboard; wait for event; observe native notification, icon swap, and a JS-side console log of the event payload.

- [ ] 3.3 Default `watcher_enabled` to `true` on every startup (deps: 3.1, est: ~5m)
  - acceptance: R-3.5 — Phase 1 does not persist the watcher toggle across launches; startup defaults to On.
  - verify: Toggle Off; quit; relaunch; observe watcher is On again, events fire within 60s.

---

## Unit 4: Native notifications

- [ ] 4.1 Request macOS notification permission on first launch only; mark "asked" persistently so it is never re-requested (deps: 0.2, 0.3, est: ~25m)
  - acceptance: R-4.1 — WHEN the application starts for the first time on a given user account, THE SYSTEM SHALL request operating-system notification permission. R-4.6 — WHERE notification permission is denied, THE SYSTEM SHALL NOT prompt repeatedly on subsequent launches.
  - verify: Reset macOS notification permission in System Settings; launch app, confirm system prompt appears once; deny; relaunch, confirm prompt does NOT reappear.

- [ ] 4.2 Fire a native notification with title "Squirrel" and body "New vault activity detected" when permission granted, for `SimulatedEvent`s (deps: 4.1, est: ~20m)
  - acceptance: R-4.2 (part) — IF notification permission is granted, THE SYSTEM SHALL fire a native notification for every `SimulatedEvent`. R-4.4 (part) — title "Squirrel", body "New vault activity detected" for simulated events.
  - verify: With permission granted, wait for next 60s tick; observe macOS notification with exact strings.

- [ ] 4.3 Fire a "Test notification" body for user-triggered test notifications (deps: 4.2, 5.5, est: ~10m)
  - acceptance: R-4.2 (part) — fire for every "Trigger Test Notification" action. R-4.4 (part) — body "Test notification" for user-triggered ones.
  - verify: Click dashboard's "Trigger Test Notification"; observe immediate notification with body "Test notification".

- [ ] 4.4 Permission-denied path: log warning + show non-blocking dashboard banner; continue running (deps: 4.1, 5.3, est: ~25m)
  - acceptance: R-4.3 — IF notification permission is denied, THE SYSTEM SHALL continue running, SHALL log a warning, AND SHALL display a non-blocking banner reading "Notifications disabled — enable in System Settings to receive alerts."
  - verify: Deny permission, relaunch, open dashboard; banner is visible; app is otherwise functional; warning line exists in log.

- [ ] 4.5 Handle notification click → show + focus window + reset icon to Normal (deps: 4.2, 2.4, 2.5, est: ~20m)
  - acceptance: R-4.5 — WHEN the user clicks a Squirrel native notification, THE SYSTEM SHALL show and focus the main window AND reset the SQ icon to the Normal state. R-2.4 (part 2) — applies via notification-click path.
  - verify: Hide window; wait for event; click resulting notification; window appears focused; icon returns to Normal.

---

## Unit 5: Dashboard UI

- [ ] 5.1 Render "Status: Running" line in DashboardView (deps: 0.1, est: ~10m)
  - acceptance: R-5.1 — THE dashboard SHALL display a status line reading "Status: Running" while the application is alive.
  - verify: Open dashboard; text "Status: Running" is visible.

- [ ] 5.2 Render watcher indicator: "Watcher: Active" / "Watcher: Paused" reflecting `watcher_enabled` in real time (deps: 5.1, 3.1, est: ~20m)
  - acceptance: R-5.2.
  - verify: Toggle watcher Off via tray; dashboard updates to "Watcher: Paused" within 1s; toggle On; updates to "Watcher: Active".

- [ ] 5.3 Render notifications indicator: "Notifications: Enabled" / "Notifications: Disabled" based on permission state (deps: 5.1, 4.1, est: ~15m)
  - acceptance: R-5.3.
  - verify: With permission granted, dashboard shows "Notifications: Enabled"; revoke + relaunch, shows "Notifications: Disabled".

- [ ] 5.4 Render "Last Event: <relative time>" with auto-refresh ≥ every 30s; show "Last Event: never" when no events have fired (deps: 5.1, 3.2, est: ~30m)
  - acceptance: R-5.4 — updated at least once every 30 seconds. R-5.5 — "Last Event: never" before any event.
  - verify: Fresh session, dashboard shows "Last Event: never"; after first event, shows "Last Event: just now" (or "<1 min ago"); wait 2 minutes without interaction, value updates to reflect new age.

- [ ] 5.5 Add "Trigger Test Notification" button → invokes notification path (deps: 5.1, 4.3, est: ~15m)
  - acceptance: R-5.6, R-5.7.
  - verify: Click button; macOS notification appears immediately (subject to permission).

- [ ] 5.6 Add "Open Logs" button mirroring tray's View Logs (deps: 5.1, 2.6, est: ~10m)
  - acceptance: R-5.8, R-5.9.
  - verify: Click button; log file/folder opens (same behaviour as tray).

- [ ] 5.7 Add "Quit" button mirroring tray's Quit Squirrel (deps: 5.1, 1.4, est: ~10m)
  - acceptance: R-5.10.
  - verify: Click button; process exits, tray icon disappears.

---

## Unit 6: Auto-start at login

- [ ] 6.1 Read `auto_start_enabled` from `~/.squirrel/config.json` on startup; absence → `false` (deps: 0.2, 0.4, est: ~25m)
  - acceptance: R-6.1 — defaults to OFF on a fresh install. R-6.4 — read from config; absence treated as `false`.
  - verify: Delete config file; launch; auto-start UI toggle is Off. Manually write `{"auto_start_enabled": true}`; launch; toggle reflects On.

- [ ] 6.2 Enable path: register with OS login items via `tauri-plugin-autostart` AND persist `true` to config (deps: 6.1, est: ~25m)
  - acceptance: R-6.2.
  - verify: Toggle Enable in UI; macOS System Settings → Login Items lists Squirrel; `~/.squirrel/config.json` contains `"auto_start_enabled": true`.

- [ ] 6.3 Disable path: deregister AND persist `false` (deps: 6.2, est: ~15m)
  - acceptance: R-6.3.
  - verify: Toggle Disable; Squirrel removed from Login Items; config persists `false`.

- [ ] 6.4 Surface auto-start toggle in dashboard (deps: 5.1, 6.2, 6.3, est: ~15m)
  - acceptance: Toggle in dashboard wires to 6.2/6.3 paths. (No EARS gate; this is the minimal UI affordance to make Unit 6 testable end-to-end.)
  - verify: Use the toggle to flip state both directions and confirm Login Items + config update accordingly.

---

## Unit 7: Packaging and install

- [ ] 7.1 Confirm Tauri v2 bundle config: `productName="Squirrel"`, `identifier="com.squirrel.app"`, app icon set, minimum macOS 12 (deps: 0.1, est: ~30m)
  - acceptance: R-7.3 — bundle identifier and app name. R-7.2 (part) — macOS 12 floor declared in config.
  - verify: `pnpm tauri build` emits `.app` whose Info.plist shows `CFBundleIdentifier=com.squirrel.app`, `CFBundleName=Squirrel`, `LSMinimumSystemVersion=12.0`.

- [ ] 7.2 Produce `Squirrel.dmg` artefact via Tauri build pipeline (deps: 7.1, all Unit 1-6 stories complete, est: ~30m)
  - acceptance: R-7.1 — distributable as a single `Squirrel.dmg`.
  - verify: `pnpm tauri build` produces `Squirrel.dmg` under `src-tauri/target/release/bundle/dmg/`; mounting and dragging to /Applications results in a runnable app.

- [ ] 7.3 Verify Windows MSI build configuration remains intact (compile-only check, not a release artefact) (deps: 0.1, est: ~15m)
  - acceptance: R-7.4 — Tauri project configuration SHALL remain capable of producing an `.msi` build.
  - verify: `tauri.conf.json` bundle targets list includes `msi`; no Windows-specific code paths are deleted or fenced off in a way that blocks a future Windows build.

- [ ] 7.4 Fresh-install acceptance walkthrough on a clean macOS account (deps: 7.2, est: ~30m)
  - acceptance: All seven steps of "Success Criteria" in `docs/hld/phase-1-mvp-desktop-shell.md` pass.
  - verify: Execute each numbered step; record pass/fail; attach screenshots or log excerpts under `.devlocal/<user>/7.4/acceptance-walkthrough.md`.

---

## Unit 8: Out-of-scope guards (verification only — no implementation)

- [ ] 8.1 Scope audit: confirm no Flask/Python/sidecar/CLI/Obsidian/AI dependencies have crept in (deps: 7.2, est: ~20m)
  - acceptance: R-8.1, R-8.2, R-8.3, R-8.4, R-8.5.
  - verify: Grep repo for `flask`, `python`, `sidecar`, `obsidian`, `openai`, `anthropic`, `vault`, `notify` (the crate), `squirrel-cli`; confirm only mentions are in spec/docs, not in `Cargo.toml`, `package.json`, or source code. Confirm `Cargo.toml` contains no `notify` crate. Confirm `tauri.conf.json` declares no sidecars.

---

## Suggested execution order

```
0.1 → 0.2 → 0.3 → 0.4
              ↓
            1.5 (logging hooks ride on each step below)

Tray foundations:    2.1 → 2.2 → 2.3 → 2.4
Lifecycle:           1.1, 1.2, 1.3 (parallel after 0.1)
                     1.4 needs 2.2

Watcher:             3.1 → 3.3
Notifications:       4.1 → 4.2; 4.4 parallel after 4.1
Integration:         3.2 (joins watcher + tray + notifications)
                     4.5 (notification click handler)

Tray wiring:         2.5, 2.6, 2.7, 2.8, 2.9, 2.10 after their respective deps

Dashboard:           5.1 → 5.2, 5.3, 5.4, 5.5, 5.6, 5.7
Auto-start:          6.1 → 6.2 → 6.3 → 6.4

Packaging gate:      7.1 → 7.2 → 7.4
Scope audit:         8.1 last
```

Total stories: 39. Total estimated focus time: ~12h (no ADHD buffer applied; expect 1.5–2× wall-clock).
