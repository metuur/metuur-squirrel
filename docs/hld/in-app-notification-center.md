# In-App Notification Center — High-Level Design

## System Overview

```
 Vault Notes (.md files)
       │  contain reminders & pressing alerts
       ▼
 ┌──────────────────────────────────────────────────────────┐
 │              Squirrel Background Daemon                  │
 │      polls vault every 30 s — detects what is due        │
 └───────────────────┬──────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
 ┌─────────────────┐   ┌───────────────────────────────┐
 │  Alert History  │   │  macOS System Notification    │
 │  (persistent)   │   │  (optional — off by default)  │
 └────────┬────────┘   └───────────────────────────────┘
          │
          ▼
 ┌──────────────────────────────────────────────────────────┐
 │                  Squirrel Tray App                       │
 │                                                          │
 │   ●  Menu bar icon  ← badge lights up when alerts wait   │
 │   │                                                      │
 │   ▼ click                                                │
 │  ┌─────────────────────────────┐                         │
 │  │ Tray Menu                   │                         │
 │  │ ─────────────────────────── │                         │
 │  │ Open Squirrel               │                         │
 │  │ Open Web UI                 │                         │
 │  │ ─────────────────────────── │                         │
 │  │ PRESSING NOW                │                         │
 │  │   45d overdue · TASK-001  → │──── opens note in       │
 │  │   5d overdue  · TASK-002  → │     browser             │
 │  │ ─────────────────────────── │                         │
 │  │ REMINDERS DUE               │                         │
 │  │   VISA-001 · Due today    → │──── opens note in       │
 │  │ ─────────────────────────── │     browser             │
 │  │ Notifications (3)         → │──── opens popup ↓       │
 │  │ ─────────────────────────── │                         │
 │  │ Quit Squirrel               │                         │
 │  └─────────────────────────────┘                         │
 │   │                                                      │
 │   ▼ "Open Squirrel" or "Notifications (N)"               │
 │  ┌─────────────────────────────┐                         │
 │  │ Popup — Notification Center │                         │
 │  │ ─────────────────────────── │                         │
 │  │ ● TASK-001  45d overdue     │                         │
 │  │   [Go to →]    [✕ Dismiss]  │                         │
 │  │                             │                         │
 │  │ ● VISA-001  Due today       │                         │
 │  │   [Go to →]    [✕ Dismiss]  │                         │
 │  │                             │                         │
 │  │ ── showing 2 of 5 ──        │                         │
 │  │ [View all]  [Mark all read] │                         │
 │  └─────────────────────────────┘                         │
 └──────────────────────────────────────────────────────────┘

 ┌──────────────────────────────────────────┐
 │ Web UI → Settings → Notifications        │
 │                                          │
 │  In-app notifications    [●  ON  ]       │  ← master
 │  OS notifications        [○  OFF ]       │  ← opt-in
 └──────────────────────────────────────────┘
       changes take effect within one poll cycle (≤ 30 s)
```

## Overview

Squirrel's daemon already detects pressing alerts and overdue reminders every 30 seconds. Today it surfaces these exclusively through macOS system notifications — a mechanism that feels foreign for a tray-resident app and offers no history, no read/unread state, and no in-app navigation. This feature migrates the user-facing notification experience entirely into the Tauri app: a notification center panel inside the tray popup, a tray icon badge when unread alerts exist, clickable tray menu items that navigate to the relevant project/note, and a Settings toggle to optionally re-enable OS popups as a secondary channel.

## Stakeholders & Impact

**Primary user:** The single Squirrel user running the macOS tray app.

| Current pain | After this ships |
|---|---|
| macOS notifications appear and disappear — no history | Notification center in the tray popup retains all alerts |
| No way to navigate to a task directly from a notification | Every alert has a "Go to →" link that opens the note in the web UI |
| No visual indicator that alerts are waiting | Tray icon switches to the `Notification` state icon when unread > 0 |
| OS notifications fire even when the app is open and visible | In-app center is always visible; OS popups are opt-in |
| Reminder tray menu items are disabled (no click action) | Reminder items are clickable and navigate to the note |
| No control over notification behavior | Settings page toggle for in-app and OS notifications independently |

## Goals

- Notification center panel renders inside the tray popup, showing the last 3 unread alerts by default with a "View all" option
- Tray icon badge (icon state swap to `Notification`) activates when unread count > 0 and clears when all are read
- Tray menu gains a "View Notifications (N)" item when unread alerts exist
- Every notification (tray menu item, in-app center row) has a navigable URL to the source project or note
- Reminder tray menu items are re-enabled and clickable
- A new `notifications` table in the existing SQLite database persists alert history, fired timestamp, and read/unread state
- Daemon writes to SQLite and emits a Tauri event; frontend listens and re-fetches
- Settings page (Web UI) exposes two toggles: `in_app` (master) and `os_popups` (opt-in secondary)
- OS notifications (`tauri_plugin_notification`) remain available but default to OFF

## Non-Goals

- No multi-user or multi-profile notification state
- No push notifications or remote delivery
- No rich HTML or image content inside notifications
- No notification sound or vibration
- No Windows or Linux support in this iteration (macOS desktop only)
- No approaching reminders in the notification center (they stay in the tray menu only)
- No per-notification snooze from the in-app center (snooze stays in the Web UI RemindersWidget)
- No changes to how the CLI scanner or reminder writer work

## Success Criteria

- Opening the tray popup shows a notification center panel when unread alerts exist
- Clicking "Go to →" on any alert opens the correct note URL in the browser
- Tray icon shows the `Notification` icon when at least one unread alert exists; reverts to `Normal` when all are read or dismissed
- Toggling "OS notifications" in Settings stops or starts macOS system popups without restarting the app
- Disabling "In-app notifications" in Settings stops all alert activity (no badge, no center, no OS popups)
- All fired alerts persist in SQLite across app restarts
