# Notification Sound Selection — Low-Level Design

## Architecture

The Python backend is the single writer; both notification surfaces are independent readers of `~/.squirrel/config.toml`. The React settings page POSTs to the existing notifications endpoint, which now also persists an optional `sound` field. The Tauri Rust process picks up the configured sound on each notification via a lazy `GET /api/me` and spawns `afplay`. The reminders daemon already reads the same config file via its `read_config` helper; it gains a `sound` lookup and forwards the value to its existing `-sound` / `sound name "..."` flags.

```
[React SettingsPage]  apps/backend/app/src/pages/SettingsPage.tsx
   └ <select> Glass | Funk | Silent (with 🔊 Preview per option)
     └ api.setNotificationSettings({in_app, os_popups, sound})
       └ POST /api/settings/notifications
         └ config_loader.save_notifications_settings(path, in_app, os_popups, sound)
           └ ~/.squirrel/config.toml
               [notifications]
               in_app = true
               os_popups = false
               sound = "Glass"
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
[Rust tray_alerts.rs]        [reminder-daemon.sh]
update_badge_and_emit():     SOUND=$(read_config "sound" "Glass")
  after emit, if count > 0:    if [ "$SOUND" = "Silent" ]; then
    GET /api/me → sound          # omit -sound / sound name clause
    if sound != Silent:        else
      Command::new("afplay")     terminal-notifier ... -sound "$SOUND"
        .arg(file_for(sound))    osascript ... sound name "$SOUND"
        .spawn()               fi
```

### Sound representation per layer

- **Python** (`config_loader.py`): plain string `"Glass" | "Funk" | "Silent"`; unknown / missing → `"Glass"`.
- **TypeScript** (`apps/backend/app/src/api/client.ts`): `sound: 'Glass' | 'Funk' | 'Silent'` extending the existing `notifications` shape.
- **Rust** (new `apps/desktop/src-tauri/src/notification_sound.rs`):
  ```rust
  #[derive(serde::Serialize, serde::Deserialize, Clone, Copy, PartialEq, Eq, Debug)]
  pub enum NotificationSound { Glass, Funk, Silent }

  impl NotificationSound {
      pub fn to_sound_file(self) -> Option<&'static str> {
          match self {
              Self::Glass  => Some("/System/Library/Sounds/Glass.aiff"),
              Self::Funk   => Some("/System/Library/Sounds/Funk.aiff"),
              Self::Silent => None,
          }
      }
  }
  ```
  Unknown JSON values from `/api/me` deserialize to `Glass` (custom `Deserialize` impl or post-parse fallback).
- **Shell** (`reminder-daemon.sh`): plain `$SOUND` variable; validated against the three names with `Glass` fallback.

### Backend changes

`apps/cli/lib/config_loader.py`:
- `load_notifications_settings(...)` returns the dict with an added `"sound"` key; default `"Glass"`; unknown value coerced to `"Glass"`.
- `save_notifications_settings(config_path, *, in_app, os_popups, sound)` — add a keyword-only `sound: str` parameter; write `sound = "<name>"` into the `[notifications]` block. Backward-compat: callers that omit `sound` (e.g. existing CLI tests) — see note below.
- The function currently rewrites the entire `[notifications]` block. To preserve `sound` when a legacy 2-key caller writes, either (a) split into separate setters per field, or (b) change `sound` to a required keyword internally and force the HTTP handler to merge with previously loaded settings before calling `save`. Option **b** is simpler — keep the lib API explicit, do the merge in the HTTP layer.

`apps/backend/server.py` `api_settings_notifications`:
- Accept optional `sound` in JSON payload.
- If `sound` is present and not in {`Glass`, `Funk`, `Silent`}, return HTTP 400 without mutating config.
- Before calling the loader, fetch current settings; if `sound` is absent in the payload, reuse the existing value (preserve-on-missing).
- Existing 400 on missing `in_app` / `os_popups` is retained.

`/api/me` builder (wherever `notifications` is composed):
- Include `"sound": "<value>"` in the `notifications` object.

### Frontend changes

`apps/backend/app/src/api/client.ts`:
- Extend `Me.notifications` to `{ in_app: boolean; os_popups: boolean; sound: 'Glass' | 'Funk' | 'Silent' }`.
- Extend `setNotificationSettings` payload type with `sound: 'Glass' | 'Funk' | 'Silent'`.

`apps/backend/app/src/pages/SettingsPage.tsx`:
- Extend `localNotif` state to include `sound`.
- Add a `<select>` (or radio group) inside the existing `SettingsSection icon="notifications"` block, after the two existing toggles.
- Each option has a 🔊 preview button that invokes Tauri command `preview_notification_sound(name)`.
- On change: optimistic local update + POST via `api.setNotificationSettings({...localNotif, sound: next})`; revert + toast on failure (mirrors existing toggle pattern at line 19–31).

### Rust changes

All Rust changes live inline in `apps/desktop/src-tauri/src/tray_alerts.rs`, reusing the existing `fetch_notif_settings` function (which already calls `GET /api/me` once per 30s poll cycle and caches the result in a `NotifSettings` struct):

- **Extend `NotifSettings`** (currently `{in_app, os_popups}`) with `sound: NotificationSound`.
- **Extend `MeNotifSection`** (the JSON deserialize struct) with `sound: NotificationSound` (defaulting via `#[serde(default)]`).
- **Add `NotificationSound` enum**: `Glass | Funk | Silent` with `Default = Glass` and a `sound_file(&self) -> Option<&'static str>` helper.
- **Add `play_notification_sound(sound)`** helper: `#[cfg(target_os = "macos")]` spawns detached `afplay`; non-macOS is a no-op; spawn failure logs a warning.
- **Wire into the polling loop**: at the two existing `Ok(true) => update_badge_and_emit(...)` sites (one for pressing alerts, one for active reminders), also call `play_notification_sound(settings.sound)`. The `settings` variable is already in scope and reflects the fresh `/api/me` response.

This is simpler than the originally-planned `notification_sound.rs` module: no per-notification HTTP round-trip (settings are already fetched once per poll cycle), no new `tauri::async_runtime::spawn`, and the sound enum lives next to the existing notification structs.

(Note: preview is handled by the Python backend over HTTP — see "Preview endpoint" below — not by a Tauri command, to keep the React app's invocation model consistent with the rest of the SPA.)

### Preview endpoint (Python backend)

`apps/backend/server.py`:
- New route `POST /api/notifications/preview` mapped to `api_notifications_preview`.
- Reads `{"sound": "<name>"}` from the body; validates against `config_loader.VALID_NOTIFICATION_SOUNDS` (HTTP 400 on invalid).
- For `Silent`: returns 200 immediately, plays nothing.
- For `Glass` / `Funk`: spawns `subprocess.Popen(["afplay", "/System/Library/Sounds/<name>.aiff"])` detached. Does not wait. Logs and returns 200 on spawn failure (fail-soft per R-2.4).
- Sound plays from the backend process on the user's machine — same speakers as Tauri's `afplay`. Does not persist anything to config.

### Daemon changes

`agent-pack/companions/macos-reminders/reminder-daemon.sh`:
- After the existing `read_config` block (around line 215), add:
  ```bash
  SOUND=$(read_config "sound" "Glass")
  case "$SOUND" in Glass|Funk|Silent) ;; *) log "invalid sound '$SOUND', defaulting to Glass"; SOUND="Glass";; esac
  ```
- Modify `show_notification_terminal_notifier` (line 78) and `show_notification_osascript` (line 92) to accept `$SOUND` as a parameter:
  - If `Silent`: omit the `-sound <name>` flag for terminal-notifier; omit the ` sound name "<name>"` clause for osascript.
  - Else: substitute `$SOUND` for the previously hardcoded `Submarine`.
- Update `show_notification` (line 352) the same way.
- Update `emit_banner` (line 134) to pass `$SOUND` through to the helpers.

`dmg-staging/agent-pack/companions/macos-reminders/reminder-daemon.sh`:
- Mirror the same changes (this is the packaged copy shipped in the DMG).

## Constraints

- macOS-only: all playback paths assume macOS APIs. Non-macOS builds compile but the Rust `play()` is a no-op; the daemon is not installed on non-macOS to begin with.
- Audio failure must never block notification delivery: spawn detached, ignore exit codes, warn on spawn error only.
- `POST /api/settings/notifications` MUST remain backward-compatible: clients posting `{in_app, os_popups}` without `sound` succeed and the previously persisted sound value is preserved.
- The daemon reads config on each run — no `launchctl unload/load` required after a setting change.
- Reusing the existing backend HTTP client from Rust requires it to be available before tray_alerts fires. It already is — the supervisor is set up earlier in `lib.rs:setup` than the tray-alerts poller.

## Key Decisions

- **Backend is the single writer; both surfaces read independently** — reuses the existing settings flow (React → backend → TOML) without introducing a second writer. The daemon reads the TOML directly because it cannot depend on the backend being up.
- **Lazy `GET /api/me` from Rust on each notification (option A)** — minimal code, automatic propagation when the user changes the sound, no manual cache or invalidation. Per-notification HTTP roundtrip is local and sub-ms.
- **No helper script** — the daemon already plays sound natively via `terminal-notifier -sound` / `osascript sound name`; we only need to substitute the value. The Rust side uses `afplay` directly. A wrapper script would be dead weight given both readers already have native mechanisms.
- **Three sounds (Glass / Funk / Silent), nothing more** — focus-friendly default + alternative + off. Decision fatigue is the enemy; no file picker, no per-surface sound.
- **Optional `sound` in API payload with preserve-on-missing** — protects existing tests in `apps/cli/tests/test_notifications_settings.py` and any CLI / scripted clients that still post the 2-key payload. Required-everywhere would break compatibility.
- **Silent omits the sound flag entirely in the daemon** (rather than passing an empty string) — terminal-notifier and osascript both treat omission as "no sound", but treat an empty string as an invalid argument.

## Out of Scope

- User-supplied custom sound files.
- Per-surface sound configuration (different sound for tray vs. daemon).
- Volume control inside the app.
- Cross-platform audio (Windows/Linux are no-op in v1).
- Refactoring `save_notifications_settings` to a per-field setter API (preserve-on-missing is handled in the HTTP layer instead).
