# Native Notification Banner (with Deep-Link to Tauri Popup) — EARS Specifications

## Unit 1: Banner emission contract

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN `reminder-daemon.sh` reaches the "show items" stage with N critical/urgent items selected (N ≤ 3 per run), THE SYSTEM SHALL emit one macOS notification banner per item. |
| R-1.2 | THE SYSTEM SHALL NOT emit an `osascript display dialog` in the happy path (only as the permission-denied fallback, see Unit 2). |
| R-1.3 | THE banner SHALL include: title = `⏰ squirrel: <PROJECT-ID>`, subtitle = the human-readable due-status line, body = the note title. |
| R-1.4 | IF an item's `next_action` field is non-empty, THE body SHALL append ` · → <next_action>` after the note title. |
| R-1.5 | THE banner SHALL play the system `Submarine` sound by default. |
| R-1.6 | IF the emitter is `terminal-notifier`, THE invocation SHALL include `-group org.squirrel.reminders`, `-title`, `-subtitle`, `-message`, `-open <deep-link-url>`, and `-sound Submarine`. THE `<deep-link-url>` SHALL be composed per R-1.9. THE invocation SHALL NOT pass `-sender com.metuur.squirrel` in v1 — see R-1.10. |
| R-1.10 | v1 banner branding deferral: THE banner SHALL ship with the default `terminal-notifier` icon (generic Terminal icon). Squirrel-icon branding via `-sender com.metuur.squirrel` is deferred to a follow-up change because it requires `com.metuur.squirrel` to have previously emitted at least one notification via `UNUserNotificationCenter` (modern Apple API) before macOS will honor it for `terminal-notifier`'s deprecated `NSUserNotificationCenter` path. The follow-up change SHALL (a) add a one-shot Tauri-side bootstrap that emits via `tauri-plugin-notification` on first launch, (b) restore `-sender com.metuur.squirrel` to R-1.6's SHALL clause, (c) document the System Settings → Notifications → Squirrel permission grant step. |
| R-1.9 | WHEN composing the deep-link URL for an item, THE SYSTEM SHALL use `squirrel://projects/<proyecto>/<id>` IF `proyecto` is non-empty AND `id != proyecto`; ELSE THE SYSTEM SHALL use `squirrel://projects/<proyecto>` IF `proyecto` is non-empty; ELSE THE SYSTEM SHALL use `squirrel://projects/<id>` (legacy fallback when an item lacks a `proyecto` field). |
| R-1.7 | THE banner body SHALL be at most 240 UTF-8 codepoints; longer note titles or next-actions SHALL be truncated with a trailing `…`. |
| R-1.8 | THE banner SHALL NOT carry any action buttons (Snooze / Open / Dismiss). |

## Unit 2: Emitter selection and fallback chain

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN deciding the emitter for a given item, THE SYSTEM SHALL evaluate, in order: (1) `terminal-notifier` on `PATH`, (2) `osascript display notification`, (3) `osascript display dialog`. |
| R-2.2 | IF `command -v terminal-notifier` succeeds, THE SYSTEM SHALL use `terminal-notifier` as the emitter for the entire daemon run. |
| R-2.3 | IF `command -v terminal-notifier` fails, THE SYSTEM SHALL log tag `terminal-notifier-missing` once per run (not per item) AND fall back to `osascript display notification` for every item in that run. |
| R-2.4 | IF an `osascript display notification` invocation exits non-zero, THE SYSTEM SHALL log tag `permission-denied` once for that run AND emit `osascript display dialog` as a last-resort fallback for the remaining items in that run AND for every subsequent item that run encounters. |
| R-2.5 | IF the fallback chain reaches `display dialog`, THE dialog body SHALL begin with `⚠️ Notifications are disabled — fallback to dialog.` followed by two newlines then the normal banner body. |
| R-2.6 | THE fallback `display dialog` SHALL show a single `OK` button (no Snooze, no Open, no Dismiss). |
| R-2.7 | THE SYSTEM SHALL log the selected emitter for each banner with exactly one of: `banner` (terminal-notifier), `banner-fallback-osascript`, or `banner-fallback-dialog`. |

## Unit 3: URL scheme registration

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE Tauri desktop app SHALL register the URL scheme `squirrel://` via `tauri-plugin-deep-link` and `plugins.deep-link.desktop.schemes = ["squirrel"]` in `tauri.conf.json`. |
| R-3.2 | THE scheme SHALL be registered in production AND in `npm run tauri dev` mode (no dev-mode guard). |
| R-3.3 | IF the user has another app already registered for `squirrel://`, THE SYSTEM SHALL still install Squirrel as a candidate. Conflict resolution is left to macOS Launch Services. |
| R-3.4 | THE scheme name SHALL be `squirrel`, all-lowercase. THE SYSTEM SHALL drop any URL whose scheme is not exactly `squirrel`. |
| R-3.5 | THE only host segment recognized SHALL be `projects`. URLs with any other host (e.g. `squirrel://focus/...`) SHALL be logged with tag `deep-link-unknown-host` and dropped. |
| R-3.6 | THE valid path SHALL be exactly 1 OR 2 segments after the host, each segment matching `[A-Za-z0-9_-]+`. THE 1-segment form `squirrel://projects/<project-id>` SHALL be interpreted as a project landing. THE 2-segment form `squirrel://projects/<project-id>/<task-id>` SHALL be interpreted as a specific task within the project. Empty path, 0 segments, 3+ segments, or characters outside the allowed set SHALL be logged with tag `deep-link-bad-path` and dropped. |

## Unit 4: Deep-link handler (Rust)

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the Tauri app receives a `squirrel://projects/<project-id>` OR `squirrel://projects/<project-id>/<task-id>` activation, THE SYSTEM SHALL (a) bring the menubar popup window to the foreground; (b) emit a Tauri event named `deep-link://focus-project` with payload `{ projectId: "<project-id>", taskId: "<task-id>" | null }`. |
| R-4.2 | IF the popup window is not currently open, THE SYSTEM SHALL open it BEFORE emitting the event. |
| R-4.3 | IF the popup window is already open, THE SYSTEM SHALL focus it AND emit the event (no re-create). |
| R-4.4 | THE event payload SHALL contain ONLY the `projectId` AND `taskId` fields — no URL, no scheme, no host segment. THE `taskId` field SHALL be `null` (JSON `null`) when the URL had only 1 path segment. |
| R-4.5 | THE Rust handler SHALL log every URL activation with tag `deep-link-handled` (on success) or `deep-link-dropped` (any validation failure, with sub-tag `deep-link-unknown-host` or `deep-link-bad-path`). |
| R-4.6 | A second activation of the same URL while the popup is open SHALL NOT recreate the window. THE handler SHALL only re-focus the existing window AND re-emit the event so the React side can re-highlight. |
| R-4.7 | THE Rust handler SHALL complete its work in ≤ 50 ms from receiving the URL to emitting the event, exclusive of OS-side window-foreground latency. |

## Unit 5: React popup deep-link consumer

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | WHEN the React `App` component mounts, THE SYSTEM SHALL subscribe to the Tauri event `deep-link://focus-project`. |
| R-5.2 | THE subscription SHALL be torn down on `App` unmount AND on HMR cycles (no listener leak). |
| R-5.3 | THE hook SHALL store the latest event payload as `{ projectId: string, taskId: string \| null, key: number }`, where `key` is a strictly-monotonic integer incremented on every event so consumers can detect repeat events with the same target. |
| R-5.4 | THE `DeadlinesWidget` SHALL accept an optional prop `scrollTarget: { projectId: string; taskId: string \| null; key: number } \| null`. |
| R-5.5 | THE widget SHALL render each deadline card with attributes `id="deadline-card-<task-id>"`, `data-task-id="<task-id>"`, AND `data-project-id="<project-slug>"`. |
| R-5.6 | WHEN `scrollTarget.key` changes (initial mount or repeat click), THE widget SHALL resolve the target element in this order: (1) IF `scrollTarget.taskId` is non-null, look up the DOM element by ID `deadline-card-<scrollTarget.taskId>`; (2) IF (1) does not yield an element, find the first rendered card whose `data-project-id` equals `scrollTarget.projectId`. |
| R-5.7 | IF a target element is resolved by R-5.6, THE widget SHALL call `scrollIntoView({ block: "center", behavior: "smooth" })` AND apply attribute `data-highlight="on"` to that element for 1500 ms. |
| R-5.8 | IF no target element is resolved by R-5.6 (e.g. neither the specific task nor any card for the project is currently in the pressing list), THE widget SHALL log to console at `debug` level AND take no further action. |
| R-5.9 | THE 1500 ms highlight SHALL be implemented as a CSS keyframe animation `squirrel-highlight` triggered by the `[data-highlight="on"]` selector. THE element SHALL revert to normal styling automatically when the attribute is removed. |
| R-5.10 | A repeat deep-link with the same `projectId` AND `taskId` SHALL re-trigger the scroll-and-highlight from the start (the monotonic `key` guarantees the React effect re-runs). |
| R-5.11 | THE highlight color SHALL be `rgba(253, 224, 71, …)` (Tailwind `yellow-300` family) with peak alpha 0.55, decaying to 0 over 1500 ms. |

## Unit 6: Existing daemon invariants preserved

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE daemon's launchd schedule (`StartInterval = 7200` seconds) SHALL remain unchanged. |
| R-6.2 | THE workday-window check (`is_within_workday`) SHALL continue to gate non-`--force` runs. |
| R-6.3 | THE per-day cap (`max_dialogs_per_day`) AND the per-run cap (3 items) SHALL continue to throttle emission. THE counter `dialogs_today` SHALL count BANNERS (the field name is preserved for state-file backward compatibility). |
| R-6.4 | THE cadence check (`is_due`) SHALL continue to read `last_shown` AND honor `snoozed_until` IF it is present AND in the future. |
| R-6.5 | THE state file `~/.squirrel/reminders-state.json` SHALL retain the same top-level keys: `last_shown`, `dialogs_date`, `dialogs_today`, optional `snoozed_until`. |
| R-6.6 | THE banner emitter SHALL NOT write `snoozed_until` (there is no Snooze button on the banner). |
| R-6.7 | THE banner emitter SHALL NOT delete `snoozed_until` if it pre-exists (forward-compat). |
| R-6.8 | THE banner emitter SHALL increment `dialogs_today` exactly once per banner emitted, regardless of which emitter path (terminal-notifier, osascript, dialog-fallback) was used. |
| R-6.9 | THE multi-vault `tomllib` fallback for `vault_path` (added earlier this session) SHALL continue to resolve the default vault. |

## Unit 7: Logging and observability

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL log a single-line entry per banner emission to `~/.squirrel/reminders-daemon.log` with timestamp, tag, and project ID. |
| R-7.2 | Tags emitted by `reminder-daemon.sh` SHALL be exactly one of: `banner`, `banner-fallback-osascript`, `banner-fallback-dialog`, `terminal-notifier-missing`, `permission-denied`. |
| R-7.3 | Tags emitted by the Rust deep-link handler (logged via `tracing` to the Tauri logs) SHALL be exactly one of: `deep-link-handled`, `deep-link-dropped`, `deep-link-unknown-host`, `deep-link-bad-path`. |
| R-7.4 | THE existing log-rotation cap (`MAX_LOG_LINES = 500`) for `reminders-daemon.log` SHALL remain unchanged. |
| R-7.5 | THE Tauri Rust side SHALL log via `tracing::info` (success path) or `tracing::warn` (validation failure) — same conventions as `tray.rs` and `tray_alerts.rs`. |

## Unit 8: Bundle and capability changes

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | `apps/desktop/src-tauri/Cargo.toml` SHALL add `tauri-plugin-deep-link = "2"` to `[dependencies]`. |
| R-8.2 | `apps/desktop/src-tauri/tauri.conf.json` SHALL declare `plugins.deep-link.desktop.schemes = ["squirrel"]`. |
| R-8.3 | `apps/desktop/src-tauri/capabilities/default.json` SHALL include the `deep-link:default` capability. |
| R-8.4 | THE SYSTEM SHALL NOT bundle `terminal-notifier`. THE README / docs SHALL note the optional Homebrew install (`brew install terminal-notifier`). |
| R-8.5 | THE bundle identifier `com.metuur.squirrel` SHALL remain unchanged. |

## Unit 9: Testing

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | A bash unit test SHALL verify that `emit_banner` selects `terminal-notifier` when present on `PATH`, `osascript display notification` when not, AND `osascript display dialog` when both are unavailable. PATH manipulation in the test SHALL be the mocking mechanism. |
| R-9.2 | A Rust unit test SHALL verify that `deep_link::validate` accepts `squirrel://projects/FOO` (yields `{ project_id: "FOO", task_id: None }`) AND `squirrel://projects/FOO/BAR` (yields `{ project_id: "FOO", task_id: Some("BAR") }`) AND rejects each of: `http://projects/FOO`, `squirrel://focus/FOO`, `squirrel://projects/`, `squirrel://projects/FOO/BAR/BAZ`, `squirrel://projects/FO O`, `squirrel://projects/FOO/B R`. |
| R-9.3 | A React unit test (Vitest) SHALL verify that `DeadlinesWidget` calls `scrollIntoView` AND adds `data-highlight="on"` to the correct card when `scrollTarget.key` changes for both: (a) a target with `taskId` matching a rendered card, (b) a target with only `projectId` falling back to the first matching project card. |
| R-9.4 | A React unit test SHALL verify that a repeat `scrollTarget` event with the same `projectId` AND `taskId` but incremented `key` re-triggers the effect. |
| R-9.5 | A manual integration check SHALL verify both deep-link shapes: `open squirrel://projects/CASA-CONTABILIDAD-TAXES-2025` scrolls to the project's first card; `open squirrel://projects/CASA-CONTABILIDAD-TAXES-2025/test-deadline` scrolls to the specific task card. |
| R-9.6 | A manual integration check SHALL verify the permission-denied fallback: with `terminal-notifier` uninstalled AND notification permission disallowed for Script Editor, running `reminder-daemon.sh --force` produces a modal `display dialog` with the warning prefix. |
