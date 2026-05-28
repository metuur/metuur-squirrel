# Phase 1 MVP — Desktop Shell — Low-Level Design

## Architecture

```
Squirrel MVP (single Tauri v2 process)
│
├── Tauri main (Rust)
│   ├── App lifecycle controller
│   │   ├── Window hide-on-close handler
│   │   ├── Single-instance guard
│   │   └── Explicit quit path (tray-only)
│   ├── Tray controller
│   │   ├── Owns SQ icon resource (4 state variants)
│   │   ├── Builds tray menu
│   │   └── Routes tray events to commands
│   ├── Notification controller
│   │   ├── Wraps tauri-plugin-notification
│   │   ├── Requests permission on first run
│   │   └── Maps notification-click → focus dashboard + clear alert
│   ├── Fake watcher (Rust async task, tokio)
│   │   ├── 60s interval
│   │   ├── Emits SimulatedEvent on event bus
│   │   └── Honours watcher_enabled flag
│   └── Internal event bus
│       ├── tauri::Emitter for Rust → JS
│       └── #[tauri::command] for JS → Rust
│
└── React UI (TypeScript, embedded in Tauri webview)
    ├── DashboardView
    │   ├── Status line, watcher indicator, "last event" age
    │   ├── Trigger Test Notification button
    │   ├── Open Logs button
    │   └── Quit button
    └── Event listener (subscribes to `squirrel://event/simulated`)
```

### Process model

One process. One window (initially hidden or shown depending on first-run flow). One async runtime (tokio, via Tauri). One tray icon. No subprocesses, no sidecars, no IPC sockets in Phase 1.

### Data flow — happy path

1. Fake watcher tick (every 60s) → emits `SimulatedEvent { id, ts }` on the internal bus.
2. Notification controller receives event → calls `tauri-plugin-notification` to fire a native notification.
3. Tray controller receives the same event → swaps the icon to the Notification state.
4. React DashboardView (if open) receives `squirrel://event/simulated` via `tauri::Emitter` → updates "last event" timestamp.
5. User clicks notification → Tauri's notification-click handler fires → focuses the window (showing it if hidden) → tray icon resets to Normal.
6. User clicks "Quit Squirrel" → Tauri exits cleanly → tray icon disappears.

### Window close handler

The main window's close button intercepts `WindowEvent::CloseRequested`, calls `api.prevent_close()`, and hides the window. The window can be re-shown via the tray menu's "Open Squirrel" item or via the notification-click handler.

### Icon state machine

```
Normal ──(event fires)──→ Notification
Normal ──(processing flag set)──→ Processing
Normal ──(backend disconnected)──→ Error
Notification ──(window focused OR Open Squirrel clicked)──→ Normal
Processing ──(processing flag cleared)──→ Normal
Error ──(connection restored)──→ Normal
```

In Phase 1, only Normal ↔ Notification transitions are driven by real logic (the fake watcher). Processing and Error states must be **implemented and switchable** (via a debug command exposed to the dashboard or a hidden hotkey) but are not driven by any production code path yet.

### Auto-start persistence

The single boolean `auto_start_enabled` is the only setting persisted in Phase 1. It is stored via `tauri-plugin-store` (or equivalent) in `~/.squirrel/config.json`. The directory `~/.squirrel/` is created on first run if absent.

## Constraints

| Constraint | Source | Implication |
|---|---|---|
| Tauri v2, not v1 | User input ("Tauri v2") | Use v2 APIs (tray, plugin-notification, window event model differ from v1) |
| React + TypeScript front-end | User input | No alternative UI stack; vanilla JS not acceptable |
| `tauri-plugin-notification` | User input | Do not roll a custom notification path |
| Tauri tray API for menu bar | User input | Do not use a third-party tray crate |
| Background worker = Rust async task | Chosen for MVP per user input | No Python sidecar, no separate process |
| Config folder = `~/.squirrel/` | User input ("Config folder: ~/.squirrel/") | All Phase 1 persistence goes here |
| Branding: name=Squirrel, icon=SQ, CLI=squirrel | User input | Bundle identifier, app name, icon resources must reflect this |
| macOS notification permission | macOS platform requirement | App must call `requestPermission()` on first launch; gracefully degrade if denied (log + continue) |
| Phase 1 ships `.dmg` only | User input ("Deliverables for Phase 1: Installer Squirrel.dmg") | Windows build configuration may be present but is not a release blocker |
| Single instance | Implicit (tray app sanity) | Use Tauri single-instance plugin to prevent double-tray-icon on second launch |

## Key Decisions

### D1. Rust async task vs. Python sidecar for the fake watcher
**Decision**: Rust async task (tokio interval).
**Rationale**: User explicitly recommended "lightweight internal Rust timer first." Avoids bundling a Python runtime in Phase 1. The watcher is throwaway code anyway — its only job is to prove the event-fires-notification-icon-updates pipeline.
**Rejected**: Python sidecar — adds packaging complexity, IPC, and a second runtime for zero Phase 1 value.

### D2. Hide-on-close vs. minimise-to-tray
**Decision**: Hide-on-close (window vanishes, no taskbar/Dock entry while hidden on macOS).
**Rationale**: User input says "Close window → app hides → tray icon remains active." A hidden window with the menu bar icon as the sole UI affordance matches the "menu bar app" UX convention on macOS.
**Rejected**: Minimise — leaves a Dock icon, conflicts with the "tray-only background" model.

### D3. Notification-click target
**Decision**: Notification click always focuses the dashboard window (showing it if hidden) and resets the icon to Normal.
**Rationale**: Phase 1 has no per-event detail view, so a single deterministic target keeps the surface area small.
**Rejected**: Per-event deep-linking — premature; no real events exist yet.

### D4. Icon state transitions
**Decision**: All four states implemented and reachable from a debug control, but only Normal ↔ Notification driven by production logic in Phase 1.
**Rationale**: Implementing all four now prevents painful retrofit when Phase 2's Flask sidecar disconnect (Error) and Phase 3's indexing (Processing) need them. Cost is one extra icon resource per state and a `set_icon_state(state)` command.
**Rejected**: Only build Normal + Notification — risks needing to revisit icon-loading and resource bundling later.

### D5. Settings persistence scope
**Decision**: Only persist `auto_start_enabled`. Everything else (vault path, etc.) is Phase 2+.
**Rationale**: Auto-start is the one user-visible toggle in Phase 1, and forgetting it across launches would be a visible bug. No other setting has any meaning yet.

### D6. Logs
**Decision**: "Open Logs" opens the OS file browser to `~/.squirrel/logs/squirrel.log`. Logging uses `tracing` or `log` crate, file appender, daily rotation off (single file is fine for MVP), level=INFO.
**Rationale**: Diagnosability is cheap to add now and expensive to bolt on later, especially when chasing macOS notification permission and tray quirks.

### D7. Single-instance enforcement
**Decision**: Use `tauri-plugin-single-instance`. Second launch focuses the existing window instead of spawning a duplicate tray icon.
**Rationale**: A duplicate tray icon is the most obvious "this is broken" signal to a user. Cheap to prevent.

### D8. First-run notification permission flow
**Decision**: On first launch, immediately request notification permission. If denied, log a warning, show a non-blocking dashboard banner ("Notifications disabled — enable in System Settings to receive alerts"), and continue running. Do not block startup, do not nag.
**Rationale**: macOS gives one shot at the system prompt; missing it forces users into System Settings. But hard-blocking on denial would make the app useless for users who simply want to see the dashboard.

## Out of Scope

The following are deferred and must not appear in Phase 1 implementation:

- Flask sidecar process; Python runtime of any kind
- CLI binary `squirrel`
- Vault detection / vault picker
- Real filesystem watcher (`notify` crate, fsevents, etc.) — only the fake 60s timer exists
- Obsidian plugin or any Obsidian integration
- Agent skills, hooks, agent pack bundling
- AI / LLM integration
- Settings UI beyond the single auto-start toggle
- Multi-vault, multi-profile, multi-user concepts
- Sync, cloud, account, login
- Windows `.msi` as a release artefact
- Code signing for distribution (Phase 1 may use ad-hoc signing for local install; production notarisation is a release-prep concern, tracked separately)
- Telemetry, analytics, crash reporting
- Localisation; Phase 1 is English-only
- Dark mode handling beyond whatever Tauri/React give for free
