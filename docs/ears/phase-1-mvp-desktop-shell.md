# Phase 1 MVP — Desktop Shell — EARS Specifications

## Unit 1: Application lifecycle

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN the user launches Squirrel for the first time, THE SYSTEM SHALL create the directory `~/.squirrel/` if it does not exist. |
| R-1.2 | WHEN the user launches Squirrel, THE SYSTEM SHALL display an SQ icon in the macOS menu bar within 2 seconds of process start. |
| R-1.3 | IF a Squirrel process is already running and the user launches Squirrel again, THE SYSTEM SHALL focus the existing main window and SHALL NOT spawn a second tray icon or process. |
| R-1.4 | WHEN the user clicks the main window's close button, THE SYSTEM SHALL hide the window and SHALL NOT terminate the process. |
| R-1.5 | WHILE the main window is hidden, THE SYSTEM SHALL keep the SQ menu bar icon visible and the fake watcher running. |
| R-1.6 | WHEN the user selects "Quit Squirrel" from the tray menu, THE SYSTEM SHALL terminate the process, remove the SQ icon from the menu bar, and stop the fake watcher. |
| R-1.7 | WHERE the host operating system is macOS, THE SYSTEM SHALL behave as a menu bar / accessory app (no persistent Dock icon while the window is hidden). |
| R-1.8 | THE SYSTEM SHALL write log entries to `~/.squirrel/logs/squirrel.log` at INFO level for every lifecycle event (start, window-hide, window-show, watcher-on, watcher-off, notification-fired, notification-clicked, quit). |

## Unit 2: Tray icon and tray menu

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL support exactly four SQ icon states: Normal, Notification, Processing, and Error. |
| R-2.2 | WHEN the application starts and no events are pending, THE SYSTEM SHALL set the SQ icon to the Normal state. |
| R-2.3 | WHEN a simulated event is emitted by the fake watcher, THE SYSTEM SHALL set the SQ icon to the Notification state. |
| R-2.4 | WHEN the user opens the main window via the tray menu's "Open Squirrel" item OR via a notification click, THE SYSTEM SHALL reset the SQ icon to the Normal state. |
| R-2.5 | THE SYSTEM SHALL expose a tray menu containing exactly these items, in order: Open Squirrel, Background Watcher (On/Off toggle), Settings, View Logs, Quit Squirrel. |
| R-2.6 | WHEN the user toggles "Background Watcher" in the tray menu to Off, THE SYSTEM SHALL stop emitting simulated events and SHALL set the SQ icon to the Error (gray) state. |
| R-2.7 | WHEN the user toggles "Background Watcher" in the tray menu to On, THE SYSTEM SHALL resume emitting simulated events on the standard 60-second interval and SHALL set the SQ icon to the Normal state. |
| R-2.8 | WHEN the user selects "View Logs" from the tray menu, THE SYSTEM SHALL open `~/.squirrel/logs/squirrel.log` (or its containing directory) in the operating system's default file viewer. |
| R-2.9 | THE SYSTEM SHALL provide a developer-only command to force any of the four icon states for verification purposes, callable from the dashboard. |

## Unit 3: Background watcher (Phase 1 simulated)

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHILE the application is running AND the Background Watcher setting is On, THE SYSTEM SHALL emit one `SimulatedEvent` every 60 seconds (±2 seconds tolerance). |
| R-3.2 | THE `SimulatedEvent` SHALL include a unique identifier and a timestamp. |
| R-3.3 | WHEN a `SimulatedEvent` is emitted, THE SYSTEM SHALL trigger a native notification AND update the SQ icon to the Notification state AND broadcast the event to the React UI. |
| R-3.4 | WHILE the Background Watcher setting is Off, THE SYSTEM SHALL NOT emit `SimulatedEvent`s. |
| R-3.5 | IF the application is launched with the Background Watcher previously toggled Off in the same session lifecycle, THE SYSTEM SHALL default to Background Watcher On at startup (Phase 1 does not persist this toggle across launches). |

## Unit 4: Native notifications

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the application starts for the first time on a given user account, THE SYSTEM SHALL request operating-system notification permission. |
| R-4.2 | IF notification permission is granted, THE SYSTEM SHALL fire a native notification for every `SimulatedEvent` and for every user-triggered "Trigger Test Notification" action. |
| R-4.3 | IF notification permission is denied, THE SYSTEM SHALL continue running, SHALL log a warning, and SHALL display a non-blocking banner in the dashboard reading "Notifications disabled — enable in System Settings to receive alerts." |
| R-4.4 | WHEN a native notification is displayed, its title SHALL be "Squirrel" and its body SHALL be "New vault activity detected" for simulated events, OR "Test notification" for user-triggered test notifications. |
| R-4.5 | WHEN the user clicks a Squirrel native notification, THE SYSTEM SHALL show and focus the main window AND reset the SQ icon to the Normal state. |
| R-4.6 | WHERE notification permission is denied, THE SYSTEM SHALL NOT prompt repeatedly on subsequent launches. |

## Unit 5: Dashboard UI

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE dashboard SHALL display a status line reading "Status: Running" while the application is alive. |
| R-5.2 | THE dashboard SHALL display a watcher indicator reading "Watcher: Active" when the Background Watcher is On, and "Watcher: Paused" when Off. |
| R-5.3 | THE dashboard SHALL display a notifications indicator reading "Notifications: Enabled" when permission has been granted, and "Notifications: Disabled" otherwise. |
| R-5.4 | THE dashboard SHALL display "Last Event: <relative time>" where `<relative time>` is the age of the most recent `SimulatedEvent` (e.g. "2 min ago"), updated at least once every 30 seconds. |
| R-5.5 | IF no `SimulatedEvent` has occurred in the current session, THE dashboard SHALL display "Last Event: never". |
| R-5.6 | THE dashboard SHALL provide a "Trigger Test Notification" button. |
| R-5.7 | WHEN the user clicks "Trigger Test Notification", THE SYSTEM SHALL fire a native notification immediately (subject to R-4.2 / R-4.3). |
| R-5.8 | THE dashboard SHALL provide an "Open Logs" button. |
| R-5.9 | WHEN the user clicks "Open Logs", THE SYSTEM SHALL behave identically to the tray menu's "View Logs" item (R-2.8). |
| R-5.10 | THE dashboard SHALL provide a "Quit" button that behaves identically to the tray menu's "Quit Squirrel" item (R-1.6). |

## Unit 6: Auto-start at login

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE SYSTEM SHALL expose an auto-start-at-login preference, defaulting to OFF on a fresh install. |
| R-6.2 | WHEN the user enables auto-start, THE SYSTEM SHALL register itself with the operating system's login-items mechanism AND persist `auto_start_enabled=true` to `~/.squirrel/config.json`. |
| R-6.3 | WHEN the user disables auto-start, THE SYSTEM SHALL deregister itself from the operating system's login-items mechanism AND persist `auto_start_enabled=false` to `~/.squirrel/config.json`. |
| R-6.4 | WHEN the application starts, THE SYSTEM SHALL read `auto_start_enabled` from `~/.squirrel/config.json` and reflect its value in the UI; if the file or key is absent, THE SYSTEM SHALL treat it as `false`. |

## Unit 7: Packaging and install

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL be distributable as a single `Squirrel.dmg` artefact built from the Tauri v2 toolchain. |
| R-7.2 | WHEN the user installs Squirrel from the `.dmg`, THE SYSTEM SHALL be runnable on macOS 12 or later without requiring the user to install any additional runtime. |
| R-7.3 | THE bundled application identifier SHALL be `com.squirrel.app` (or a project-agreed equivalent under a single namespace) and the visible application name SHALL be "Squirrel". |
| R-7.4 | WHERE the host operating system is Windows, THE Tauri project configuration SHALL remain capable of producing an `.msi` build, but Phase 1 SHALL NOT require a tested Windows release artefact. |

## Unit 8: Out-of-scope guards (negative requirements)

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | THE SYSTEM SHALL NOT bundle, launch, or depend on any Flask process, Python interpreter, or other sidecar runtime in Phase 1. |
| R-8.2 | THE SYSTEM SHALL NOT install, register, or expose a `squirrel` CLI binary in Phase 1. |
| R-8.3 | THE SYSTEM SHALL NOT read, write, watch, or otherwise interact with any Obsidian vault, Markdown file, or user-data location outside `~/.squirrel/` in Phase 1. |
| R-8.4 | THE SYSTEM SHALL NOT load or invoke any agent skill, hook, AI model, or LLM API in Phase 1. |
| R-8.5 | THE SYSTEM SHALL NOT implement a real filesystem watcher in Phase 1; only the 60-second simulated timer is permitted as an event source. |
