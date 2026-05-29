# Native Notification Banner (with Deep-Link to Tauri Popup) — High-Level Design

## Overview

Today, the macOS reminder daemon (`agent-pack/companions/macos-reminders/reminder-daemon.sh`, mirrored to `~/others/ai-agents/adhd-context-bridge/companions/macos-reminders/reminder-daemon.sh` for the launchd-installed copy) surfaces critical and urgent deadlines via AppleScript modal dialogs (`display dialog`). Each fired deadline blocks the screen and the user's focus until they click a button. For an ADHD-targeted tool whose entire premise is "reduce the friction between awareness and action," modal dialogs are an actively counterproductive surface: they hijack attention, can't be reviewed later, queue and pile up if several items fire in the same launchd interval, and bypass macOS Focus / Do Not Disturb.

This change replaces the modal dialog with **native macOS Notification Center banners** emitted via `terminal-notifier`. The banner is non-blocking, stacks in the Notification Center for asynchronous review, and respects system Focus settings. Clicking the banner does not just dismiss it — it triggers a custom URL scheme (`squirrel://projects/<id>`) that the Tauri desktop app handles by surfacing the menubar popup AND scrolling the matching deadline card into view with a brief highlight pulse. The web-UI browser-open path remains available as a separate affordance (the `↗` button on each `DeadlinesWidget` card) but is no longer the notification's primary click target.

Design commitments:

- **Vault remains the source of truth.** The daemon still scans deadlines with `deadline_scanner.py` and obeys cadence / cap / workday-window state.
- **Existing tray surfaces unchanged.** The Phase-2 tray menu, `FocusWidget`, and `DeadlinesWidget` keep their current rendering. Deep-link only adds a one-shot scroll-and-highlight on top.
- **No new always-on processes.** `terminal-notifier` is invoked per banner; the URL-scheme handler runs only when activated; the React listener mounts with the popup.
- **Graceful degradation.** When `terminal-notifier` isn't installed, the daemon falls back to plain `osascript display notification` (visible banner, no click handler). When notification permission has been denied entirely, the daemon falls back to the legacy modal `display dialog` so the user is still informed.

## Stakeholders & Impact

| Stakeholder | Today's pain | After this ships |
|---|---|---|
| Primary user (Javier) | Modal `display dialog` blocks the screen mid-task; multiple deadlines fire as a serial modal queue; alerts can't be reviewed once dismissed; bypasses Focus modes; the `Open` button only ever opened the web UI in the browser. | Non-blocking banner appears in Notification Center; multiple deadlines stack and stay reviewable; system Focus modes silence them; clicking the banner surfaces the Tauri menubar popup AND scrolls to the matching deadline card with a 1.5 s highlight pulse. |
| macOS reminder daemon (`reminder-daemon.sh`) | Hard dependency on `osascript` synchronous dialogs; per-choice state machine (`Snooze`/`Open`/`Dismiss`); multi-line message escaping fragility; `set -euo pipefail` interactions with `while read` loops (cause of the recent silent-exit bug). | Emits via `terminal-notifier` (or fallback osascript banner); no choice/state machine since banners are buttonless; simpler escaping (terminal-notifier accepts plain UTF-8 args); existing cadence / cap / workday-window logic untouched. |
| Tauri desktop popup | No deep-link surface; popup-open is triggered only by tray-menu click. | Registers `squirrel://` URL scheme via `tauri-plugin-deep-link`; surfaces the popup on URL activation; emits a Tauri event with the project ID that the React side consumes to scroll-and-highlight the matching deadline card. |
| Browser SPA (`apps/backend/app/`) | Unchanged. The web UI is no longer the daemon's click target but remains reachable via each `DeadlinesWidget` card's `↗` button and via the menubar `Open Squirrel` menu item. | Unchanged. |
| Obsidian-only sessions | Modal dialog disrupts whatever Obsidian-side work is in flight. | Banner is non-blocking; the user keeps writing/editing without a flow break. |
| Future LLM agents or scripts | No machine-readable "the daemon currently considers these items pressing" signal beyond the existing `~/.squirrel/reminders-state.json`. | Unchanged — this change does not introduce a new state file or event log beyond log lines in `reminders-daemon.log`. |

Out-of-scope consumers (CLI `sq-*` commands, `deadline_scanner.py`, backend REST API, `tray_alerts.rs`) are listed only to confirm they are not affected by this change.

## Goals

When this ships, the following are observable and true:

1. **Banner surface, not modal.** When the daemon fires inside the workday window with critical/urgent deadlines available, each of the (up to 3) selected items produces a non-blocking macOS Notification Center banner. No `display dialog` appears in the happy path.
2. **Rich body.** Each banner shows project as title (`⏰ squirrel: <PROJECT-ID>`), due-status as subtitle (`⚠️ Overdue 43d (was 2026-04-15)` or `Due tomorrow (2026-05-29)` etc.), and note title + optional next-action as body. The text content is at least as rich as the prior modal dialog's content.
3. **Banners stack and persist.** Multiple banners fired in the same daemon run remain in Notification Center until the user clears them, and survive across reboots per system retention policy.
4. **Click-to-Tauri.** Clicking a banner triggers a `squirrel://` URL — either `squirrel://projects/<project-id>` for the whole project or `squirrel://projects/<project-id>/<task-id>` for a specific task within a project — which (a) brings the Tauri menubar popup to the foreground, (b) emits a Tauri event with `{ projectId, taskId? }`, (c) causes the React side to scroll the matching `DeadlinesWidget` card into view (by task when `taskId` is set, by first-matching project when only `projectId` is set) and apply a 1.5 s highlight pulse.
5. **Focus mode respected.** macOS Focus / Do Not Disturb silences the banners (system-handled) without any daemon-side change.
6. **Cadence and cap preserved.** `cadence_minutes`, `max_dialogs_per_day`, the workday window, and the snooze-until logic continue to throttle banner emission exactly as they previously throttled dialogs.
7. **Permission-deny fallback.** When notification permission is denied entirely (Script Editor / `terminal-notifier` both blocked in System Settings → Notifications), the daemon emits the legacy modal `display dialog` for that run so the user is still informed. The fallback is logged so the user can diagnose the permission issue.
8. **Optional Homebrew dep.** `terminal-notifier` is the preferred emitter. When it isn't on `PATH`, the daemon falls back to `osascript display notification` (visible banner, no click target). The user can choose to keep no-Homebrew and accept the loss of click-to-Tauri.
9. **State schema compatible.** `~/.squirrel/reminders-state.json` keeps its existing keys (`last_shown`, `dialogs_date`, `dialogs_today`, optional `snoozed_until`). The Snooze write path is retired (no Snooze button on the banner) but the field stays as forward-compat for any future button-bearing emitter (Tauri-plugin path).
10. **Deep-link round-trip ≤ 1 s.** From the moment the user clicks the banner to the moment the Tauri popup is foregrounded and the matching deadline card is scrolled-and-highlighted, total wall time is ≤ 1 second on an M-series Mac.
11. **No legacy `Snooze`/`Open`/`Dismiss` plumbing left.** All call sites in `reminder-daemon.sh` that previously read `choice` from the dialog and branched on it are removed; the only "after emission" work is the state-update.
12. **Observability.** Every banner emission and every fallback path is logged to `~/.squirrel/reminders-daemon.log` with one of the canonical tags listed in EARS Unit 7.

## Non-Goals

Out of scope for this change:

- **Action buttons on the banner** (`Snooze` / `Open` / `Dismiss`). Native `display notification` doesn't support them and `terminal-notifier`'s `-actions` flag was deprecated upstream and unreliable on modern macOS. A future migration to `tauri-plugin-notification` would unlock buttons; that is explicitly a separate change.
- **Migration to `tauri-plugin-notification`.** Deferred until the daemon→Tauri IPC story is designed. Today's flow stays daemon-emits-OS-notification.
- **Banner grouping / threading** (e.g. "X more from Squirrel"). Not exposed via `terminal-notifier`; out of scope.
- **Per-vault notification opt-out.** Notifications are global across the active vault.
- **Linux / Windows banners.** The daemon is macOS-only; no cross-platform abstraction is added.
- **Persistent click history / analytics.** No record of which banner was clicked beyond a single log line.
- **Re-firing on missed clicks.** If the user dismisses a banner without clicking, the daemon's `cadence_minutes` prevents the same item from re-firing within the window. No escalation logic.
- **Sound customization.** Default to the system `Submarine` sound via `-sound Submarine`.
- **Banner content image** (Big-Sur+'s `contentImage` field). Plain text only.
- **Replacing the tray-menu's "PRESSING NOW" surface.** That surface continues to be populated by `tray_alerts.rs` polling `/api/home`.
- **Touching `tray_alerts.rs`.** The deep-link plumbing is added next to it (in a new `deep_link.rs` module), not inside it.
- **Filtering or detail-view UI in the popup on deep-link arrival.** Scroll-and-highlight only; the rest of the dashboard stays visible.

## Success Criteria

This is done when:

1. Running `reminder-daemon.sh --force` with 3 critical/urgent items in the vault produces 3 macOS Notification Center banners, observable in the Notification Center widget. No `display dialog` appears in the happy path.
2. Each banner shows: title = `⏰ squirrel: <PROJECT-ID>`, subtitle = the due-status line, body = note title (plus `· → <next_action>` when a `next_action` is present).
3. Clicking any banner brings the menubar squirrel popup to the foreground within 1 s. The `DeadlinesWidget` is scrolled so the matching deadline card is visible. The matching card carries a 1.5 s yellow highlight pulse, then returns to normal styling.
4. With `terminal-notifier` uninstalled (`brew uninstall terminal-notifier`), `reminder-daemon.sh --force` still produces banners — using the `osascript display notification` fallback — visible in Notification Center but with no click handler. The log shows `banner-fallback-osascript`.
5. With both `terminal-notifier` uninstalled AND Script Editor's notification permission disallowed, `reminder-daemon.sh --force` falls back to a `display dialog` modal. The dialog body begins with `⚠️ Notifications are disabled — fallback to dialog.` The log shows `permission-denied` and `banner-fallback-dialog`.
6. Manually pasting `open squirrel://projects/CASA-CONTABILIDAD-TAXES-2025` into Terminal produces scroll-and-highlight on the project's first card. Pasting `open squirrel://projects/CASA-CONTABILIDAD-TAXES-2025/test-deadline` produces scroll-and-highlight on the specific task card. Both shapes are exercised, proving the URL scheme is the single source of truth for the deep-link path.
7. With macOS Focus mode `Do Not Disturb` active, no banner appears on screen (system-silenced). The banner still lands in Notification Center and is reviewable when the Focus mode ends. The daemon log shows `banner` (emission succeeded; visibility is OS-handled).
8. The state file `~/.squirrel/reminders-state.json` after a `--force` run shows `dialogs_today` incremented by the number of banners emitted, `last_shown` updated, and `snoozed_until` absent (since no Snooze button was clicked). Schema is byte-identical to a state-file snapshot the existing daemon would have produced (modulo the omitted `snoozed_until`).
9. The legacy `show_dialog` function and choice-handling block in `reminder-daemon.sh` are gone; only `emit_banner`, `show_notification_terminal_notifier`, `show_notification_osascript`, and `show_dialog_fallback` remain. `grep -n 'display dialog' reminder-daemon.sh` finds exactly the fallback call site and nothing else.
10. The Tauri Rust handler is registered for `squirrel://`. A second invocation of the URL scheme while the popup is already open does not re-create the window — it only re-focuses and re-emits the event so the React side can re-highlight.
11. Running the existing test suite stays green; new tests cover the daemon's emitter-selection logic (bash test with `PATH` manipulation), the Rust URL parser (`deep_link::handle` accept/reject cases), and the React scroll-and-highlight (Vitest).

If all eleven pass, the feature ships.
