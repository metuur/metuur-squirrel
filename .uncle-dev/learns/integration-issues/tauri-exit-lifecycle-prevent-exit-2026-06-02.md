---
title: "Tauri v2: call api.prevent_exit() in ExitRequested; defer shutdown to RunEvent::Exit"
date: 2026-06-02
category: integration-issues
module: desktop-app
problem_type: integration_issue
component: tooling
severity: critical
symptoms:
  - Cmd+Q terminates the app entirely instead of hiding the window
  - Dock right-click → Quit bypasses the custom close handler and kills the process
  - Backend supervisor is shut down on every quit gesture, including intercepted ones
root_cause: missing_workflow_step
resolution_type: code_fix
tags: [tauri, app-lifecycle, exit-requested, prevent-exit, cmd-q, dock-quit, shutdown, menu-bar-app]
---

# Tauri v2: call api.prevent_exit() in ExitRequested; defer shutdown to RunEvent::Exit

## Problem

Cmd+Q and Dock → Quit fully terminated the Squirrel process instead of hiding the window and staying alive as a tray app. The only intended quit path is the "Quit Squirrel" item in the system tray menu.

## Symptoms

- Cmd+Q exits the app entirely — window and tray icon both disappear
- Dock → Quit has the same effect
- Backend supervisor process is killed on every interceptable quit gesture

## What Didn't Work

Handling `RunEvent::ExitRequested` with only `backend_supervisor::shutdown(app)` and no `api.prevent_exit()`. The shutdown ran, but the runtime proceeded with termination anyway — nothing told Tauri to cancel the exit sequence.

## Solution

`apps/desktop/src-tauri/src/lib.rs`

```rust
// Before
tauri::RunEvent::ExitRequested { .. } => {
    backend_supervisor::shutdown(app);
}

// After
tauri::RunEvent::ExitRequested { api, .. } => {
    api.prevent_exit();
    // Redirect to the same hide+Accessory behaviour as the X button
    if let Some(window) = app.get_webview_window("main") {
        if window.is_visible().unwrap_or(false) {
            let _ = window.hide();
            #[cfg(target_os = "macos")]
            let _ = app.set_activation_policy(tauri::ActivationPolicy::Accessory);
        }
    }
}

// Only reached via app.exit(0) — tray "Quit" item
tauri::RunEvent::Exit => {
    backend_supervisor::shutdown(app);
}
```

The tray Quit item calls `app.exit(0)` directly. This fires `RunEvent::Exit` and bypasses `ExitRequested` entirely, so shutdown runs exactly once on the intended path.

## Why This Works

`RunEvent::ExitRequested` fires for all user-initiated quit gestures: Cmd+Q, Dock → Quit, `app.request_exit()`. Calling `api.prevent_exit()` cancels the exit sequence — same model as `api.prevent_close()` on `CloseRequested`. `RunEvent::Exit` only fires when the process is genuinely going to terminate: either nothing prevented the exit, or `app.exit(0)` was called directly. Shutdown in `Exit` guarantees it runs once, only on the real quit path.

The two-path contract:
- External quit gesture → `ExitRequested` → `api.prevent_exit()` → hide window → stay alive
- Tray "Quit Squirrel" → `app.exit(0)` → `Exit` → `backend_supervisor::shutdown`

## Prevention

- Treat `ExitRequested` like `CloseRequested`: always decide — prevent or allow. An empty or shutdown-only match arm that never calls `prevent_exit()` is almost always a bug.
- Shutdown logic belongs in `RunEvent::Exit`, not `ExitRequested`. `ExitRequested` is the intercept point; `Exit` is the teardown point.
- Document the two-path quit contract in a comment near the `.run()` callback so future contributors adding a quit path know which event they will fire.

## Related Issues

- [`tauri-window-close-vs-hide-2026-06-02.md`](tauri-window-close-vs-hide-2026-06-02.md) — the `CloseRequested` handler that `ExitRequested` mirrors for the window X-button path
