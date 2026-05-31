# Global Shortcut & Window Activation — Tasks

## Unit 1: Global Shortcut Registration

- [x] 1.1 Add `tauri-plugin-global-shortcut` crate dependency (est: ~5m)
  - acceptance: R-1.1 — THE SYSTEM SHALL register `Ctrl+Cmd+S` as a system-wide global shortcut on desktop platforms at application startup.
  - verify: `cargo build` compiles without errors; `Cargo.lock` contains `tauri-plugin-global-shortcut`

- [x] 1.2 Register shortcut plugin in `lib.rs` setup block (deps: 1.1, est: ~15m)
  - acceptance: R-1.1, R-1.2 — shortcut registered at startup; failure logs a warning and does not crash
  - verify: App launches; pressing `Ctrl+Cmd+S` from another app triggers the handler (visible via `tracing::info!` log)

- [x] 1.3 Verify shortcut auto-unregisters on exit (deps: 1.2, est: ~5m)
  - acceptance: R-1.3 — THE SYSTEM SHALL unregister the global shortcut automatically when the application process exits.
  - verify: Quit the app via tray → "Quit Squirrel"; pressing `Ctrl+Cmd+S` afterwards has no effect

## Unit 2: Shortcut-Triggered Window Show

- [x] 2.1 Call `show_main_window` from shortcut handler (deps: 1.2, est: ~10m)
  - acceptance: R-2.1 — WHEN shortcut pressed while window hidden, THE SYSTEM SHALL show and focus the main window
  - verify: Hide window → press `Ctrl+Cmd+S` → window appears and is focused

- [x] 2.2 Show is idempotent when window already visible (deps: 2.1, est: ~5m)
  - acceptance: R-2.2 — WHEN shortcut pressed while window already visible, THE SYSTEM SHALL set focus (no double-show)
  - verify: Window open → press `Ctrl+Cmd+S` → window stays open, no flicker, remains focused

- [x] 2.3 Set activation policy to `Regular` on window show (deps: 2.1, mutex: 3.2, est: ~15m)
  - acceptance: R-2.3 — WHEN shortcut triggers window show, THE SYSTEM SHALL set macOS activation policy to `Regular`
  - verify: Show window via shortcut → app icon appears in Cmd+Tab switcher and Dock

## Unit 3: Window Hide & Background Mode

- [x] 3.1 Confirm existing close-intercept hides without quit (est: ~5m)
  - acceptance: R-3.1 — WHEN user closes main window, THE SYSTEM SHALL hide it without quitting
  - verify: Click red close button → window hides; tray icon remains; app process still running (`pgrep squirrel` returns PID)

- [x] 3.2 Set activation policy to `Accessory` on window hide (deps: 3.1, mutex: 2.3, est: ~15m)
  - acceptance: R-3.2 — WHEN main window hidden, THE SYSTEM SHALL set macOS activation policy to `Accessory`
  - verify: Show window → close it → app disappears from Cmd+Tab and Dock

- [x] 3.3 Confirm tray polling continues while window is hidden (deps: 3.2, est: ~5m)
  - acceptance: R-3.3 — WHILE main window hidden, THE SYSTEM SHALL continue tray alert polling
  - verify: Hide window → wait 35s → tray menu still shows current pressing items (or "No pressing items" if backend offline)

## Unit 4: Tray Menu Consistency

- [x] 4.1 Route tray "Open Squirrel" through updated `show_main_window` (deps: 2.3, est: ~5m)
  - acceptance: R-4.1 — WHEN "Open Squirrel" tray item selected, THE SYSTEM SHALL show/focus window via same path as shortcut
  - verify: Hide window → click tray "Open Squirrel" → window shows, app appears in Cmd+Tab (policy flipped)

- [x] 4.2 Tray icon resets to Normal on any window show (deps: 4.1, est: ~5m)
  - acceptance: R-4.2 — THE SYSTEM SHALL reset tray icon to Normal whenever window is shown
  - verify: Trigger a Notification tray state → show window via shortcut → tray icon returns to Normal
