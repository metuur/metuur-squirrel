# Notification Sound Selection — Tasks

## Unit 1: Python backend — config loader & API contract

- [x] 1.1 Extend `config_loader.load_notifications_settings` to return a `sound` key (default `"Glass"`, unknown → `"Glass"`) (est: ~15m)
  - acceptance: R-1.1, R-1.3 — three values supported; missing/invalid → Glass
  - verify: Add unit tests in `apps/cli/tests/test_notifications_settings.py` covering missing key, each of the three valid values, and an unknown value

- [x] 1.2 Extend `config_loader.save_notifications_settings` with a keyword-only `sound: str` parameter; write `sound = "<name>"` inside the `[notifications]` block (deps: 1.1, est: ~20m)
  - acceptance: R-1.2 — sound persisted in the existing section
  - verify: Unit test confirms the `[notifications]` block contains all three keys after a save; reading back yields the persisted value

- [x] 1.3 Update `server.py:api_settings_notifications` to accept optional `sound`, validate against the three values, and preserve the existing value when omitted (deps: 1.2, est: ~25m)
  - acceptance: R-4.1, R-4.2, R-4.3, R-1.4 — optional, preserve-on-missing, 400 on invalid, no clobber of in_app/os_popups
  - verify: Three HTTP tests — (a) POST with `sound=Funk` persists Funk; (b) POST with only `{in_app, os_popups}` preserves the prior sound; (c) POST with `sound="Bogus"` returns 400 and config is unchanged

- [x] 1.4 Include `sound` in the `notifications` object returned by `/api/me` (deps: 1.1, est: ~10m)
  - acceptance: R-4.4 — `me.notifications.sound` populated
  - verify: GET `/api/me` against a config with `sound = "Funk"` → response has `notifications.sound == "Funk"`; with missing key → `"Glass"`

## Unit 2: TypeScript API client + Settings UI

- [x] 2.1 Extend `Me.notifications` interface and `setNotificationSettings` payload type with `sound: 'Glass' | 'Funk' | 'Silent'` in `apps/backend/app/src/api/client.ts` (deps: 1.4, est: ~10m)
  - acceptance: R-3.3 — types align with backend payload
  - verify: `tsc --noEmit` passes; SettingsPage type-checks against the new shape

- [x] 2.2 Add Python backend endpoint `POST /api/notifications/preview` that plays the requested sound via `afplay` without touching config (est: ~25m)
  - acceptance: R-3.2, R-4.5 — preview without save; invalid sound → 400; Silent → 200 + no audio
  - verify: HTTP tests — (a) POST `{"sound":"Funk"}` returns 200 and triggers afplay (mock or process check); (b) POST `{"sound":"Silent"}` returns 200 with no afplay spawned; (c) POST `{"sound":"Bogus"}` returns 400; (d) `~/.squirrel/config.toml` is unchanged after each preview

- [x] 2.3 Extend the existing Notifications section in `SettingsPage.tsx` (line ~102) with a sound control showing the current selection (deps: 2.1, 2.2, est: ~30m)
  - acceptance: R-3.1 — control visible; current selection indicated; existing in_app/os_popups toggles still function
  - verify: Open settings, observe current selection highlighted; toggle in_app/os_popups still works exactly as before

- [x] 2.4 Wire the sound control to POST via `setNotificationSettings`, using the existing optimistic-update + revert-on-failure pattern (deps: 2.3, est: ~20m)
  - acceptance: R-3.3 — persists within 1s; failure reverts + shows toast
  - verify: Change selection → config updates within 1s; simulate API failure (kill backend) → UI reverts, toast appears

- [x] 2.5 Add 🔊 preview button per option that calls `api.previewNotificationSound(name)` (new API client method that POSTs to `/api/notifications/preview`) (deps: 2.2, 2.3, est: ~15m)
  - acceptance: R-3.2 — preview plays each option without committing
  - verify: Click each preview button → corresponding sound plays from the backend; saved selection unchanged

## Unit 3: Rust tray_alerts integration

**Implementation note:** the existing `fetch_notif_settings` in `tray_alerts.rs:164` already calls `GET /api/me` once per 30s poll cycle and caches the result in a `NotifSettings` struct. Rather than create a new `notification_sound.rs` module with its own per-notification HTTP roundtrip, the sound type, helper, and playback wiring were added inline in `tray_alerts.rs`. This collapses tasks 3.1–3.4 into one cohesive change and removes the need for a second HTTP call.

- [x] 3.1 Add `NotificationSound` enum (`Glass`, `Funk`, `Silent`) with `Default = Glass` and `sound_file() -> Option<&'static str>`; extend `NotifSettings` + `MeNotifSection` with a `sound` field (inline in `tray_alerts.rs`) (est: ~15m)
  - acceptance: R-1.1 — three variants exist with mappings
  - verify: `cargo test` covers each variant returning the expected `Option<&'static str>` + `Default == Glass`

- [x] 3.2 ~~Implement `fetch_configured_sound(app)`~~ — not needed; reused existing `fetch_notif_settings` by adding `sound` to `MeNotifSection` and `NotifSettings`. Fail-soft behavior is inherited from the existing function (errors → `NotifSettings::default()` with `sound = Glass`). (deps: 3.1, est: ~5m)
  - acceptance: R-2.4 (HTTP-error branch) — backend down → returns Glass + warn (existing behavior of `fetch_notif_settings`)
  - verify: Covered by `test_notif_settings_default_uses_glass`

- [x] 3.3 Implement `play_notification_sound(sound)` — `#[cfg(target_os = "macos")]` spawns detached `afplay`; non-macOS is a no-op; spawn failure → `tracing::warn!` (est: ~15m)
  - acceptance: R-2.3 (Silent), R-2.4 (spawn error)
  - verify: Code review of fail-soft path; manual: rename `/usr/bin/afplay` away → call returns within ms, warning logged, no panic

- [x] 3.4 Wire `play_notification_sound(settings.sound)` into the two `Ok(true) => update_badge_and_emit(...)` branches in the polling loop (pressing alerts + active reminders) — `settings` is already in scope from the existing `fetch_notif_settings` call (est: ~10m)
  - acceptance: R-2.1 — sound plays once per new notification
  - verify: Trigger a backend notification insert → tray flips AND sound plays once (manual, audible); cargo test green

## Unit 4: Reminders daemon

- [x] 4.1 Add `SOUND=$(read_config "sound" "Glass")` to `agent-pack/companions/macos-reminders/reminder-daemon.sh` with validation against the three values (Glass fallback on invalid) (est: ~15m)
  - acceptance: R-2.2 — daemon reads configured sound
  - verify: Set `sound = "Funk"` in config, run `reminder-daemon.sh --force` against a vault with a critical item → banner plays Funk

- [x] 4.2 Update `show_notification_terminal_notifier` (line 78), `show_notification_osascript` (line 92), `show_notification` (line 352), and `emit_banner` (line 134) to take `$SOUND` and omit the sound flag entirely when `Silent` (deps: 4.1, est: ~25m)
  - acceptance: R-2.2, R-2.3 — sound passes through; Silent → no audio, banner still appears
  - verify: With `sound = "Silent"`, manual daemon run → banner appears with no audio; with `sound = "Funk"` → banner plays Funk; previously hardcoded `Submarine` no longer appears in any branch

- [x] 4.3 Mirror the same changes in `dmg-staging/agent-pack/companions/macos-reminders/reminder-daemon.sh` (deps: 4.2, est: ~5m)
  - acceptance: packaged daemon stays in sync
  - verify: `diff agent-pack/companions/macos-reminders/reminder-daemon.sh dmg-staging/agent-pack/companions/macos-reminders/reminder-daemon.sh` shows no sound-related discrepancies

## Unit 5: End-to-end verification

- [ ] 5.1 End-to-end hot-apply across both surfaces (deps: 2.4, 3.4, 4.2, est: ~15m)
  - acceptance: R-3.4 — change reflects in both surfaces without restart/reload
  - verify: With app running and daemon installed, change selection from Glass to Funk in settings; trigger a tray notification (Funk plays) and run `reminder-daemon.sh --force` (Funk plays); no `launchctl unload/load` performed; no app restart

- [x] 5.2 Backward-compat smoke test against legacy clients (deps: 1.3, est: ~10m)
  - acceptance: R-4.2 — legacy 2-key POST preserves sound
  - verify: Covered by `TestSettingsNotificationsSound::test_post_without_sound_preserves_current` in `apps/cli/tests/test_web_ui_json_api.py` — seeds `sound=Funk`, POSTs 2-key payload, asserts Funk survives
