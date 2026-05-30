# Tasks: Global Shortcut and Window Activation Policy

Stories for `Cmd+Shift+S` global shortcut and dynamic macOS activation-policy management.

## Epic 1 — Global Shortcut Registration

- [x] **1.1** Add `tauri-plugin-global-shortcut = "2"` to desktop-only deps in `Cargo.toml`
- [x] **1.2** Register `CmdOrCtrl+Shift+S` in `setup` closure via `GlobalShortcutExt::on_shortcut`; handler calls `tray::show_main_window`; registration failure logs a warning and does not crash the app

## Epic 2 — Activation Policy: Regular on Show

- [x] **2.1** `show_main_window` is the single code path invoked by the shortcut handler
- [x] **2.2** Handler fires `tray::show_main_window(app)` on `ShortcutState::Pressed`
- [x] **2.3** `show_main_window` sets `ActivationPolicy::Regular` (macOS) before calling `window.show()` so the app appears in Cmd+Tab and the Dock

## Epic 3 — Activation Policy: Accessory on Hide

- [x] **3.1** Existing `on_window_event` handler intercepts `CloseRequested` for the `"main"` window, calls `api.prevent_close()` and `window.hide()` — confirmed at `lib.rs:121-144`, no code change needed
- [x] **3.2** After successful `window.hide()`, `on_window_event` sets `ActivationPolicy::Accessory` (macOS) so the app vanishes from Cmd+Tab and the Dock while hidden

## Epic 4 — Tray Menu Integration

- [x] **4.1** Tray "Open Squirrel" calls `show_main_window` — policy flip is already inside `show_main_window`, so no routing change needed
- [x] **4.2** `set_state(app, IconState::Normal)` is called inside `show_main_window` — no change needed

---

*All stories implemented in commit `feat(desktop): add Cmd+Shift+S global shortcut and dynamic activation policy`.*
