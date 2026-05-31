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

- [ ] 2.3 Extend the existing Notifications section in `SettingsPage.tsx` (line ~102) with a sound control showing the current selection (deps: 2.1, 2.2, est: ~30m)
  - acceptance: R-3.1 — control visible; current selection indicated; existing in_app/os_popups toggles still function
  - verify: Open settings, observe current selection highlighted; toggle in_app/os_popups still works exactly as before

- [ ] 2.4 Wire the sound control to POST via `setNotificationSettings`, using the existing optimistic-update + revert-on-failure pattern (deps: 2.3, est: ~20m)
  - acceptance: R-3.3 — persists within 1s; failure reverts + shows toast
  - verify: Change selection → config updates within 1s; simulate API failure (kill backend) → UI reverts, toast appears

- [ ] 2.5 Add 🔊 preview button per option that calls `api.previewNotificationSound(name)` (new API client method that POSTs to `/api/notifications/preview`) (deps: 2.2, 2.3, est: ~15m)
  - acceptance: R-3.2 — preview plays each option without committing
  - verify: Click each preview button → corresponding sound plays from the backend; saved selection unchanged

## Unit 3: Rust tray_alerts integration

- [ ] 3.1 Create `apps/desktop/src-tauri/src/notification_sound.rs` with `NotificationSound` enum and `to_sound_file()` helper (est: ~15m)
  - acceptance: R-1.1 — three variants exist with mappings
  - verify: `cargo test` covers each variant returning the expected `Option<&'static str>`

- [ ] 3.2 Implement `fetch_configured_sound(app)` — lazy `GET /api/me`, parses `notifications.sound`, fail-soft to `Glass` (deps: 3.1, est: ~25m)
  - acceptance: R-2.4 (HTTP-error branch) — backend down → returns Glass + warn
  - verify: Unit test against a mock HTTP server; backend offline → returns `Glass` and logs warning

- [ ] 3.3 Implement `play(sound)` — `#[cfg(target_os = "macos")]` spawns detached `afplay`; no-op for Silent and non-macOS (deps: 3.1, est: ~15m)
  - acceptance: R-2.3 (Silent), R-2.4 (spawn error)
  - verify: Rename `/usr/bin/afplay` away → `play()` returns within ms, warning logged, no panic; `play(Silent)` is a no-op (no `afplay` process spawned, observable via `ps`)

- [ ] 3.4 Wire sound playback into `tray_alerts::update_badge_and_emit` after the existing emit, only when `count > 0`, using `async_runtime::spawn` so the badge path stays non-blocking (deps: 3.2, 3.3, est: ~20m)
  - acceptance: R-2.1 — sound plays once per notification with count > 0
  - verify: Trigger a backend notification insert → tray flips AND sound plays once (manual, audible); rapid back-to-back inserts each produce a sound

## Unit 4: Reminders daemon

- [ ] 4.1 Add `SOUND=$(read_config "sound" "Glass")` to `agent-pack/companions/macos-reminders/reminder-daemon.sh` with validation against the three values (Glass fallback on invalid) (est: ~15m)
  - acceptance: R-2.2 — daemon reads configured sound
  - verify: Set `sound = "Funk"` in config, run `reminder-daemon.sh --force` against a vault with a critical item → banner plays Funk

- [ ] 4.2 Update `show_notification_terminal_notifier` (line 78), `show_notification_osascript` (line 92), `show_notification` (line 352), and `emit_banner` (line 134) to take `$SOUND` and omit the sound flag entirely when `Silent` (deps: 4.1, est: ~25m)
  - acceptance: R-2.2, R-2.3 — sound passes through; Silent → no audio, banner still appears
  - verify: With `sound = "Silent"`, manual daemon run → banner appears with no audio; with `sound = "Funk"` → banner plays Funk; previously hardcoded `Submarine` no longer appears in any branch

- [ ] 4.3 Mirror the same changes in `dmg-staging/agent-pack/companions/macos-reminders/reminder-daemon.sh` (deps: 4.2, est: ~5m)
  - acceptance: packaged daemon stays in sync
  - verify: `diff agent-pack/companions/macos-reminders/reminder-daemon.sh dmg-staging/agent-pack/companions/macos-reminders/reminder-daemon.sh` shows no sound-related discrepancies

## Unit 5: End-to-end verification

- [ ] 5.1 End-to-end hot-apply across both surfaces (deps: 2.4, 3.4, 4.2, est: ~15m)
  - acceptance: R-3.4 — change reflects in both surfaces without restart/reload
  - verify: With app running and daemon installed, change selection from Glass to Funk in settings; trigger a tray notification (Funk plays) and run `reminder-daemon.sh --force` (Funk plays); no `launchctl unload/load` performed; no app restart

- [ ] 5.2 Backward-compat smoke test against legacy clients (deps: 1.3, est: ~10m)
  - acceptance: R-4.2 — legacy 2-key POST preserves sound
  - verify: With `sound = "Funk"` persisted, send a 2-key POST via `curl` (`{"in_app": true, "os_popups": false}`) → response 200; `~/.squirrel/config.toml` still contains `sound = "Funk"`
