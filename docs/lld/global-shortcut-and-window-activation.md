# Global Shortcut & Window Activation — Low-Level Design

## Architecture

Two cooperating mechanisms in `src-tauri/src/`:

```
[tauri-plugin-global-shortcut]
       │ Ctrl+Cmd+S pressed (system-wide)
       ▼
  lib.rs (setup)
  shortcut handler
       │ calls
       ▼
  tray::show_main_window(app)          ← already exists (tray.rs:255)
       │ + NEW: set_activation_policy(Regular)
       │
       ▼
  window.show() + window.set_focus()

[on_window_event CloseRequested]      ← already exists (lib.rs:92)
       │ api.prevent_close()
       │ window.hide()
       │ + NEW: set_activation_policy(Accessory)
```

### Dynamic activation-policy management

macOS activation policy controls Dock visibility and Cmd+Tab presence:

| Policy | Dock | Cmd+Tab | Use |
|--------|------|---------|-----|
| `Accessory` | No | No | Window hidden / app in background |
| `Regular` | Yes (transient) | Yes | Window visible and focused |

- Switch to `Regular` in `show_main_window` (called by both shortcut and tray "Open Squirrel").
- Switch back to `Accessory` in the `CloseRequested` handler, after `window.hide()`.
- Both transitions are `#[cfg(target_os = "macos")]` guarded.

### Files to change

| File | Change |
|------|--------|
| `Cargo.toml` line 37–39 | Add `tauri-plugin-global-shortcut = "2"` under `[target.'cfg(not(any(target_os = "android", target_os = "ios")))'.dependencies]` |
| `src/lib.rs` setup block (line 38–50) | Register `tauri_plugin_global_shortcut` plugin with `Ctrl+Cmd+S` handler calling `tray::show_main_window` |
| `src/lib.rs` `on_window_event` (line 92–103) | After `window.hide()`, call `app.set_activation_policy(Accessory)` on macOS |
| `src/tray.rs` `show_main_window` (line 255) | After `window.show()` + `set_focus()`, call `app.set_activation_policy(Regular)` on macOS |
| `capabilities/default.json` | No change — Rust-side registration needs no capability entry |

### Shortcut string

`"Ctrl+Cmd+S"` — resolves to Control+Command+S on macOS (both modifiers required). The `matches()` check in the handler uses `Modifiers::CONTROL | Modifiers::SUPER` + `Code::KeyS` on macOS.

## Constraints

- `set_activation_policy` is macOS-only; calls must be `#[cfg(target_os = "macos")]` guarded.
- The plugin must be registered under the `#[cfg(desktop)]` guard (same pattern as `tauri-plugin-single-instance`).
- `tauri_plugin_global_shortcut::Builder::new().with_shortcuts([...])` returns `Result` — must propagate with `?` inside `setup`.

## Key Decisions

- **Rust-side only registration** — no JS plugin install, no capability entry. Simpler and fires before webview loads.
- **Dynamic policy (not permanent Regular)** — permanent `Regular` would leave a Dock icon always visible, contradicting the tray-bar-only intent.
- **`show_main_window` is the single show path** — both the tray menu item and the shortcut go through the same function, so the policy flip happens consistently in one place.
- **`Ctrl+Cmd+S` (both modifiers)** — chosen by the user to avoid collision with common `Cmd+Shift+S` "Save As" usage in editor apps; requiring both Control and Command makes the combo unambiguous and unlikely to clash with single-modifier shortcuts.

## Out of Scope

- User-configurable shortcut key.
- Linux / Windows activation-policy behaviour (no equivalent API; shortcut still works on those platforms).
- Frontend event emission on shortcut press.
- Hiding the Dock icon while window is open (OS side-effect of `Regular` policy; acceptable).
