---
title: "Tauri v2: use .close() not .hide() to trigger CloseRequested; add allow-close capability"
date: 2026-06-02
category: integration-issues
module: desktop-app
problem_type: integration_issue
component: frontend_stimulus
severity: high
symptoms:
  - App window hides but macOS Dock icon remains visible
  - After switching to .close(), button appears to do nothing — no error, no UI response
root_cause: wrong_api
resolution_type: code_fix
tags: [tauri, window-management, capabilities, ipc, dock-icon, activation-policy]
---

# Tauri v2: use .close() not .hide() to trigger CloseRequested; add allow-close capability

## Problem

The custom close button called `getCurrentWindow().hide()` from JS. The window disappeared but the macOS Dock icon remained. Switching to `.close()` caused the button to silently do nothing until `core:window:allow-close` was added to capabilities.

## Symptoms

- Window disappears when close button is clicked, but the Dock icon stays
- App behaves inconsistently with standard menu-bar apps (Dock icon should disappear on hide)
- After switching the call to `.close()`: button appears to do nothing — no error, no visual response

## What Didn't Work

- `getCurrentWindow().hide()` from React: sends IPC directly to Tauri's hide handler, bypassing `WindowEvent::CloseRequested`. The Rust handler — which calls `api.prevent_close()`, `window.hide()`, and `app.set_activation_policy(tauri::ActivationPolicy::Accessory)` — never ran. The Accessory policy change is what tells macOS to remove the Dock icon.
- Assuming `.close()` was sufficient without checking capabilities: `core:window:allow-close` was absent from `capabilities/default.json`. Tauri v2 silently drops any uncapabilitied IPC call — the promise never resolves, no JS exception is thrown.

## Solution

**Step 1 — Change the button to call `.close()`**

`apps/desktop/src/components/CloseWindowButton.tsx`

```tsx
// Before
await getCurrentWindow().hide();

// After
await getCurrentWindow().close();
```

**Step 2 — Add the missing capability**

`apps/desktop/src-tauri/capabilities/default.json`

```json
"permissions": [
  "core:window:allow-close",
  "core:window:allow-hide",
  ...
]
```

## Why This Works

`.close()` fires `WindowEvent::CloseRequested` in Rust. The registered handler intercepts it, calls `api.prevent_close()` (prevents window destruction), `window.hide()` (removes from screen), then `app.set_activation_policy(tauri::ActivationPolicy::Accessory)`. The Accessory policy is what removes the Dock icon — it signals to macOS that the process no longer owns a standard application window. Without it, the window disappears visually but the Dock icon lingers.

`.hide()` from JS bypasses the Rust event router entirely: it is a direct command to Tauri's hide handler, not a close request.

The capability is required because Tauri v2 denies all IPC calls not explicitly listed in `capabilities/`. `core:window:allow-hide` (present) and `core:window:allow-close` (was absent) are separate entries — one does not imply the other.

## Prevention

- Reserve `window.hide()` from JS for cases where no Rust side effects are needed. When the Rust handler must run (e.g. activation policy, state cleanup), always use `window.close()`.
- After any IPC call change, immediately verify the matching `allow-*` permission is in `capabilities/default.json`. "Does nothing, no error" is the canonical Tauri v2 symptom of a missing capability.
- `core:window:allow-hide` and `core:window:allow-close` are independent permissions.

## Related Issues

- [`tauri-exit-lifecycle-prevent-exit-2026-06-02.md`](tauri-exit-lifecycle-prevent-exit-2026-06-02.md) — paired fix that prevents Cmd+Q from bypassing this same Rust close handler
- [`tauri-opener-custom-url-scheme-2026-06-02.md`](tauri-opener-custom-url-scheme-2026-06-02.md) — same silent-failure pattern from a missing capability scope
