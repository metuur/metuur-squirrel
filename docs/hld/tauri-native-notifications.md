# Tauri Native Notifications — High-Level Design

## Overview

Squirrel's Tauri menubar app gains the ability to send macOS notification banners directly, replacing the bash daemon's notification role for machines where the app is running. The existing 30-second tray-alerts polling loop is extended with a 2-minute notification guard: every 2 minutes it examines the pressing-items list, applies per-item and daily throttles, and fires `UNUserNotificationCenter`-based banners via `tauri-plugin-notification`. Clicking a banner opens the browser at the task's web-UI URL. The bash reminder daemon acquires a `pgrep` guard and skips notification sending when the Tauri app is already running — keeping it as a cold-start / no-Tauri fallback.

## Stakeholders & Impact

| Stakeholder | Today's pain | After this ships |
|-------------|-------------|-----------------|
| Squirrel users (Tauri running) | Notification clicks depend on terminal-notifier being installed; osascript fallback has no click action | Reliable click-to-browser from a Tauri-native UNUserNotificationCenter banner; no external tools required |
| Squirrel users (Tauri not running) | Daemon notification behaviour unchanged | Daemon still fires; no regression |
| Daemon maintainers | Daemon and Tauri notifications could double-fire | Daemon skips when Tauri is detected via pgrep; clean ownership boundary |

## Goals

- macOS notification banners appear every 2 minutes while pressing items exist and the daily cap is not exceeded
- Clicking a banner opens `http://127.0.0.1:3939/notes/<id>` in the default browser
- If the backend is offline at click time, a secondary notification says "Backend offline" instead of opening a broken browser tab
- System sleep/hibernation does not cause a burst of notifications on wake; one full 2-minute interval is observed first
- `tauri-plugin-notification` (already registered) is the sole new code path; no new Cargo dependencies

## Non-Goals

- The Tauri popup scroll/highlight on notification click is not part of this feature (browser-only, per I2)
- The bash daemon's workday window, cadence, cap, and state-file logic are not modified
- Notification branding (custom icon via `-sender`) is deferred (same deferral as native-notification-banner R-1.10)
- Configurable polling interval or per-item cooldown (hard-coded in v1)
- Android / Windows notification paths

## Success Criteria

1. Running `pgrep -x "Squirrel"` inside the daemon exits 0 → daemon logs `tauri-app-running` and skips notifications
2. A pressing item that has not been notified in the past hour causes a banner to appear within 2 minutes of the poll cycle
3. Clicking the banner opens the browser at `http://127.0.0.1:3939/notes/<id>`
4. If the backend is offline, clicking the banner shows a secondary "Backend offline" notification instead of a broken browser page
5. Putting the machine to sleep and waking it does not cause a notification within < 2 minutes of wake time
6. After 8 banners in one calendar day, no further banners fire until midnight
