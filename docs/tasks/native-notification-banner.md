# Native Notification Banner (with Deep-Link to Tauri Popup) — Tasks

Source specs: `docs/hld/native-notification-banner.md`, `docs/lld/native-notification-banner.md`, `docs/ears/native-notification-banner.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Dependency layers:
```
1.1 → 1.2 → 1.3 → 1.4 → 1.5                  (bash daemon, serial — single file)
 │
2.1 → 3.1 → 3.2 → 3.3                        (tauri bundle + rust deep-link handler)
                    │
                    ├─ 4.1 ↘
                    │       4.4 → 4.5         (react side; 4.2/4.3 independent feed 4.4)
                    ├─ 4.2 ↗
                    └─ 4.3 ↗
                              │
5.1 (any time)               5.2  ← needs 1.4, 3.3, 4.4
                              5.3  ← needs 1.4
```

## Unit 1: Bash daemon — banner emission and fallback chain

- [x] **1.1** Add `compose_deeplink(project, task)` helper to `agent-pack/companions/macos-reminders/reminder-daemon.sh` (mutex: daemon-script, est: ~20m)
  - acceptance:
    - R-1.9 — Returns `squirrel://projects/<proyecto>/<id>` when both present and `id != proyecto`; `squirrel://projects/<proyecto>` when only `proyecto` present; `squirrel://projects/<id>` legacy fallback when `proyecto` is empty.
  - verify:
    - Bash unit test: source the helper, call with `("FOO","BAR")` → `squirrel://projects/FOO/BAR`; `("FOO","FOO")` → `squirrel://projects/FOO`; `("FOO","")` → `squirrel://projects/FOO`; `("","BAR")` → `squirrel://projects/BAR`.

- [x] **1.2** Add the three emitter functions `show_notification_terminal_notifier`, `show_notification_osascript`, `show_dialog_fallback` to `reminder-daemon.sh` (deps: 1.1, mutex: daemon-script, est: ~45m)
  - acceptance:
    - R-1.5 / R-1.6 — `terminal-notifier` invocation includes `-group org.squirrel.reminders`, `-title`, `-subtitle`, `-message`, `-open <url>`, `-sound Submarine`. (R-1.10: `-sender com.metuur.squirrel` is intentionally NOT included in v1 — branding follow-up.)
    - R-2.3 — `osascript display notification` fallback uses title/subtitle/message but does NOT pass the deep-link URL (osascript can't open it).
    - R-2.5 — `show_dialog_fallback` body begins with `⚠️ Notifications are disabled — fallback to dialog.\n\n` followed by the normal banner body.
    - R-2.6 — Fallback dialog declares a single `OK` button (no Snooze, Open, Dismiss).
  - verify:
    - Bash unit test (PATH-isolated): stub `terminal-notifier` with a recorder that echoes argv to a tmpfile; call `show_notification_terminal_notifier` with known args; assert the tmpfile contains `-title`, `-subtitle`, `-message`, `-open`, `-group org.squirrel.reminders`, `-sound Submarine`; assert the tmpfile does NOT contain `-sender` (v1 invariant).
    - Bash unit test: stub `osascript` similarly; call `show_dialog_fallback "PROJ" "subtitle" "body"`; assert the script passed to osascript contains the `⚠️ Notifications are disabled` prefix and `buttons {"OK"} default button "OK"`.

- [x] **1.3** Add `emit_banner(project, title, subtitle, body)` orchestrator + truncation + tagged logging to `reminder-daemon.sh` (deps: 1.2, mutex: daemon-script, est: ~45m)
  - acceptance:
    - R-1.1 — Called once per selected item (N ≤ 3 per run); produces one banner per item.
    - R-1.3 — Title = `⏰ squirrel: <PROJECT-ID>`, subtitle = due-status, body = note title.
    - R-1.4 — When `next_action` is non-empty, body has ` · → <next_action>` appended.
    - R-1.7 — Body truncated to 240 UTF-8 codepoints with trailing `…` when longer.
    - R-1.8 — No action buttons attached on the banner path.
    - R-2.1 / R-2.2 — Emitter chosen once per daemon run: prefer `terminal-notifier` if on PATH, else `osascript display notification`.
    - R-2.7 / R-7.1 / R-7.2 — Logs exactly one of `banner`, `banner-fallback-osascript`, `banner-fallback-dialog` per emission to `~/.squirrel/reminders-daemon.log` with timestamp + project ID.
  - verify:
    - Bash unit test: stub `terminal-notifier` on PATH; call `emit_banner "PROJ" "title" "subtitle" "body"`; assert the recorder shows one invocation with composed title `⏰ squirrel: PROJ`.
    - Bash unit test: pass a body with `next_action` value of "fix X"; assert the recorder's `-message` arg ends with ` · → fix X`.
    - Bash unit test: pass a 300-char body; assert the recorder's `-message` is exactly 240 codepoints ending with `…`.
    - Bash unit test: after one emission via terminal-notifier, assert `~/.squirrel/reminders-daemon.log` last line matches `*banner*PROJ*` (tag + project).

- [x] **1.4** Wire the fallback chain into `emit_banner` and retire legacy `show_dialog` / `open_in_web_ui` / rename `update_state_after_dialog → update_state_after_emit` (deps: 1.3, mutex: daemon-script, est: ~30m)
  - acceptance:
    - R-1.2 — No `osascript display dialog` invocation appears in the happy path (only the permission-denied fallback).
    - R-2.4 — When `osascript display notification` exits non-zero once, the daemon logs `permission-denied` once for the run and uses `show_dialog_fallback` for the remaining items in that run AND subsequent items.
    - R-2.7 — Each fallback path logs the right tag (`banner-fallback-osascript`, `banner-fallback-dialog`).
    - R-6.1–R-6.9 — Existing daemon invariants preserved: launchd `StartInterval=7200`, `is_within_workday`, `max_dialogs_per_day`, per-run cap of 3, `is_due`, state-file keys, `dialogs_today` increments once per banner (any path), banner emitter never writes `snoozed_until` and never deletes a pre-existing one, multi-vault `tomllib` fallback for `vault_path` continues to resolve.
    - LLD-aligned: `show_dialog`, `open_in_web_ui` functions removed; `update_state_after_dialog` renamed to `update_state_after_emit` with the choice-branch logic gone.
  - verify:
    - `grep -n 'display dialog' agent-pack/companions/macos-reminders/reminder-daemon.sh` returns exactly the `show_dialog_fallback` call site — no other matches.
    - `grep -nE 'show_dialog\b|open_in_web_ui|update_state_after_dialog' …/reminder-daemon.sh` returns nothing.
    - Bash unit test: stub `osascript` to exit non-zero on the `display notification` call; run `emit_banner` twice in sequence; assert second call routed through `show_dialog_fallback` and log shows one `permission-denied` line for the run.
    - State-file regression: pre-seed `~/.squirrel/reminders-state.json` with `snoozed_until = "2099-01-01T00:00:00Z"`; run `reminder-daemon.sh --force` with one item; assert post-run state has `snoozed_until` still set to the same value and `dialogs_today` incremented by exactly 1.

- [x] **1.5** Add the bash unit-test harness for emitter selection via PATH manipulation (deps: 1.4, est: ~30m)
  - acceptance:
    - R-9.1 — Test verifies `emit_banner` picks `terminal-notifier` when on PATH; `osascript display notification` when not; `osascript display dialog` when both unavailable (forced via non-zero exit on the osascript notification call).
  - verify:
    - Test runs via the existing CLI test harness (or a new `apps/cli/tests/test_reminder_daemon.sh` invoked from `make test-cli`); three scenarios produce the three log tags `banner`, `banner-fallback-osascript`, `banner-fallback-dialog` respectively.

## Unit 2: Tauri bundle — deep-link plugin and capability

- [x] **2.1** Register `tauri-plugin-deep-link` in `apps/desktop/src-tauri/{Cargo.toml,tauri.conf.json,capabilities/default.json}` (est: ~30m)
  - acceptance:
    - R-8.1 — `Cargo.toml` `[dependencies]` includes `tauri-plugin-deep-link = "2"`.
    - R-8.2 — `tauri.conf.json` declares `plugins.deep-link.desktop.schemes = ["squirrel"]`.
    - R-8.3 — `capabilities/default.json` includes the `deep-link:default` capability.
    - R-8.5 — `tauri.conf.json` `identifier` remains `com.metuur.squirrel` (no change).
    - R-3.1 / R-3.2 / R-3.3 — Scheme is registered both in `npm run tauri dev` AND production; no dev-mode guard.
  - verify:
    - `cargo build --manifest-path apps/desktop/src-tauri/Cargo.toml` succeeds.
    - `pnpm tauri dev` launches without plugin-registration errors.
    - macOS: after `npm run tauri build` and one launch of the produced `.app`, `defaults read com.apple.LaunchServices/com.apple.launchservices.secure | grep -A1 squirrel` shows `com.metuur.squirrel` as a candidate handler.

## Unit 3: Rust deep-link handler

- [x] **3.1** Create `apps/desktop/src-tauri/src/deep_link.rs` module with `pub struct Target { project_id, task_id }` and `fn validate(&Url) -> Result<Target, DeepLinkError>` (est: ~45m)
  - acceptance:
    - R-3.4 — Scheme must be exactly `squirrel` (lowercase); other schemes rejected.
    - R-3.5 — Host must be exactly `projects`; other hosts rejected with `DeepLinkError::UnknownHost`.
    - R-3.6 — Path is 1 OR 2 segments, each matching `[A-Za-z0-9_-]+`; empty, 0, 3+, or illegal characters rejected with `DeepLinkError::BadPath`.
    - Module is `mod deep_link;` declared in `lib.rs` but `on_open_url` wiring is deferred to 3.3.
  - verify:
    - `cargo build` succeeds.
    - `cargo check` shows no warnings in the new module beyond pre-existing project baseline.

- [x] **3.2** Add `#[cfg(test)] mod tests` block to `deep_link.rs` covering the EARS accept/reject set (deps: 3.1, est: ~30m)
  - acceptance:
    - R-9.2 — Accepts `squirrel://projects/FOO` → `Target { project_id: "FOO", task_id: None }`; `squirrel://projects/FOO/BAR` → `Target { project_id: "FOO", task_id: Some("BAR") }`. Rejects each of: `http://projects/FOO`, `squirrel://focus/FOO`, `squirrel://projects/`, `squirrel://projects/FOO/BAR/BAZ`, `squirrel://projects/FO O`, `squirrel://projects/FOO/B R`.
  - verify:
    - `cargo test --manifest-path apps/desktop/src-tauri/Cargo.toml deep_link::` runs and all eight assertions pass.

- [x] **3.3** Implement `deep_link::handle<R: Runtime>(app, url)` + wire `tauri::Builder::on_open_url` in `lib.rs` (deps: 2.1, 3.2, est: ~75m)
  - acceptance:
    - R-4.1 — On `squirrel://projects/<p>` or `squirrel://projects/<p>/<t>`: foreground the menubar popup window AND emit Tauri event `deep-link://focus-project` with payload `{ projectId, taskId }`.
    - R-4.2 — If the popup window is not currently open, open it BEFORE emitting the event.
    - R-4.3 — If the popup is already open, focus it AND emit the event (no recreate).
    - R-4.4 — Event payload contains ONLY `projectId` and `taskId`; `taskId` is JSON `null` for 1-segment URLs.
    - R-4.5 / R-7.3 / R-7.5 — Logs via `tracing::info` on success (`deep-link-handled`) or `tracing::warn` on validation failure (`deep-link-dropped` plus sub-tag `deep-link-unknown-host` or `deep-link-bad-path`).
    - R-4.6 — Second activation while the popup is open re-focuses + re-emits, never recreates the window.
    - R-4.7 — `validate` + `handle` complete in ≤ 50 ms from URL receipt to event emission, exclusive of OS-side foregrounding latency.
  - verify:
    - Manual: `open squirrel://projects/CASA-CONTABILIDAD-TAXES-2025` from Terminal → popup foregrounds and React side receives the event (inspect via dev console listener stub).
    - Manual: same URL invoked twice within 2 seconds → only one window exists (verify via `osascript -e 'tell app "System Events" to count windows of process "squirrel"'` or `tauri::WebviewWindow::is_visible` log line); two log lines `deep-link-handled` present.
    - Manual: `open squirrel://focus/FOO` → Tauri log shows `deep-link-dropped` + `deep-link-unknown-host`; no event emitted.
    - Manual: add `tracing::info!(elapsed_ms = ?)` around the handler; observe ≤ 50 ms in logs across 10 activations.

## Unit 4: React popup deep-link consumer

- [x] **4.1** Create `apps/desktop/src/hooks/useDeepLink.ts` with monotonic-key subscription (deps: 3.3, est: ~30m)
  - acceptance:
    - R-5.1 — Subscribes to Tauri event `deep-link://focus-project` on mount.
    - R-5.2 — Cleanup tears down the listener on unmount AND on HMR (no listener leak across hot reloads).
    - R-5.3 — Returns `{ projectId: string, taskId: string | null, key: number } | null`; `key` is strictly monotonic and increments on every event, even when the payload repeats.
  - verify:
    - Vitest unit test: mock `@tauri-apps/api/event.listen`; render hook; fire two events with identical payload `{ projectId: "FOO", taskId: null }`; assert `key` differs between the two snapshots.
    - Vitest unit test: render hook then unmount; assert the unlisten callback returned from `listen()` was called exactly once.

- [x] **4.2** Extend `DeadlinesWidget.tsx` with `scrollTarget` prop + per-card data attributes + scroll-and-highlight effect (deps: 4.1, est: ~45m)
  - acceptance:
    - R-5.4 — Accepts optional prop `scrollTarget: { projectId: string; taskId: string | null; key: number } | null`.
    - R-5.5 — Each card rendered with `id="deadline-card-<task-id>"`, `data-task-id="<task-id>"`, `data-project-id="<project-slug>"`.
    - R-5.6 — On `scrollTarget.key` change: resolve target by `taskId` first (`document.getElementById` or ref map); fallback to first rendered card whose `data-project-id` matches `scrollTarget.projectId`.
    - R-5.7 — Resolved element gets `scrollIntoView({ block: "center", behavior: "smooth" })` and `data-highlight="on"` for 1500 ms.
    - R-5.8 — When no element resolves, `console.debug` logs the miss and the effect exits cleanly.
    - R-5.10 — Repeat target with same `projectId` + `taskId` but incremented `key` re-runs the effect (re-scroll + re-highlight).
  - verify:
    - Vitest component test: render with fixtures for three cards across two projects; set `scrollTarget = { projectId: "P1", taskId: "T2", key: 1 }`; assert `scrollIntoView` called on the `data-task-id="T2"` ref and that element receives `data-highlight="on"`.
    - Vitest component test: set `scrollTarget` with only `projectId` (taskId null) for project `P1`; assert highlight lands on the first card whose `data-project-id="P1"`.

- [x] **4.3** Add `apps/desktop/src/components/DeadlinesWidget.module.css` with `squirrel-highlight` keyframe animation (deps: 4.2, est: ~15m)
  - acceptance:
    - R-5.9 — `[data-highlight="on"]` selector triggers a 1.5s CSS keyframe animation that auto-reverts on attribute removal (no JS-driven style mutation beyond the attribute).
    - R-5.11 — Highlight color is `rgba(253, 224, 71, …)` with peak alpha 0.55 at ~15%, decaying to 0 by 100%.
  - verify:
    - Manual: in DevTools, toggle `data-highlight="on"` on a card; observe the yellow pulse runs once over 1500 ms and the element returns to normal background when attribute is removed.
    - Inspect: `grep -E "0\.55|rgba\(253, 224, 71" apps/desktop/src/components/DeadlinesWidget.module.css` finds the peak-alpha rule.

- [x] **4.4** Wire `useDeepLink()` into `App.tsx` and pass `scrollTarget` down to `DeadlinesWidget` (deps: 4.2, 4.3, est: ~15m)
  - acceptance:
    - `App` mounts `useDeepLink()` once and passes its return value as `scrollTarget` prop to `DeadlinesWidget`.
    - No regression to other widgets — `FocusWidget`, `ParakeetWidget`, `BackendStatusBanner` unaffected.
  - verify:
    - `pnpm tsc --noEmit` passes.
    - Manual: launch popup; trigger `open squirrel://projects/<known-project>` from Terminal; popup foregrounds and the matching card scrolls into view with the yellow pulse.

- [x] **4.5** Vitest tests for scroll target matching AND repeat-key re-trigger (deps: 4.4, est: ~45m)
  - acceptance:
    - R-9.3 — Test (a): target with `taskId` matching a rendered card → `scrollIntoView` called AND `data-highlight="on"` applied to that specific card.
    - R-9.3 — Test (b): target with only `projectId` (taskId null) → falls back to first card whose `data-project-id` matches.
    - R-9.4 — Repeat event with identical `{ projectId, taskId }` but incremented `key` re-triggers the effect (re-call of `scrollIntoView`).
  - verify:
    - `pnpm test -- DeadlinesWidget` runs and the three new assertions pass.

## Unit 5: Docs and manual integration checks

- [x] **5.1** Add a README note documenting the optional `brew install terminal-notifier` AND the v1 generic-icon caveat (est: ~10m)
  - acceptance:
    - R-8.4 — README (or equivalent docs surface) mentions `terminal-notifier` is optional, click-to-Tauri is lost without it, and the daemon falls back to a no-click banner. No bundling references.
    - R-1.10 — Same docs surface notes: v1 banners use the generic Terminal icon (no Squirrel branding) because `-sender com.metuur.squirrel` requires a Tauri-side `UNUserNotificationCenter` bootstrap that is tracked as a follow-up change.
  - verify:
    - `grep -in 'terminal-notifier' README.md` (or the docs file modified) returns the new section.
    - `grep -inE 'icon|branding|sender' README.md` returns the v1 caveat paragraph.

- [ ] **5.2** Manual integration check: both deep-link URL shapes end-to-end (deps: 1.4, 3.3, 4.4, est: ~20m)
  - acceptance:
    - R-9.5 — `open squirrel://projects/CASA-CONTABILIDAD-TAXES-2025` scrolls to the project's first card with highlight. `open squirrel://projects/CASA-CONTABILIDAD-TAXES-2025/test-deadline` scrolls to the specific task card with highlight.
  - verify:
    - Capture two screenshots into `.devlocal/<user>/native-notification-banner/e2e-deeplink/` showing the highlighted card for each URL shape; note observed round-trip wall time (target ≤ 1 s per HLD success criterion #4).

- [ ] **5.3** Manual integration check: permission-denied fallback (deps: 1.4, est: ~20m)
  - acceptance:
    - R-9.6 — With `terminal-notifier` uninstalled AND Script Editor's notification permission disallowed, `reminder-daemon.sh --force` produces a modal `display dialog` whose body begins with `⚠️ Notifications are disabled — fallback to dialog.`; `~/.squirrel/reminders-daemon.log` contains `permission-denied` and `banner-fallback-dialog` lines.
  - verify:
    - `brew uninstall terminal-notifier` (if present) → re-run `reminder-daemon.sh --force` with the permission revoked → observe the modal and the log tags; capture the log snippet into `.devlocal/<user>/native-notification-banner/e2e-permission-denied/`.
