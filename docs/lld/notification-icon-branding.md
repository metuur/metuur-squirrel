# Notification Icon Branding — Low-Level Design

## Architecture

Two cooperating touch points plus docs, across the Tauri app and the macOS reminders companion.

```
[first launch]  apps/desktop/src-tauri/src/lib.rs (setup hook)
   └─ notif_identity::bootstrap_once(app)
        ├─ ~/.squirrel/.notif_identity sentinel present?
        │     yes → no-op
        │     no  → query permission_state()
        │            ├─ NotDetermined → request_permission()
        │            ├─ Granted/Authorized → emit ONE tauri-plugin-notification
        │            │     banner (registers com.metuur.squirrel with
        │            │     UNUserNotificationCenter); on Ok → create sentinel
        │            └─ Denied/NotGranted → WARN, NO sentinel, retry next launch
        ▼
   macOS now honors `-sender com.metuur.squirrel`  (cold-identity window until here)
        ▼
[deadline reminder]  installed daemon copy (path baked into launchd plist)
   └─ show_notification_terminal_notifier()
        terminal-notifier -group … -sender com.metuur.squirrel
                          -title … -subtitle … -message … -open <url>  [+ -sound <SOUND>]
        ▼
   banner shows the Squirrel logo; click activates Squirrel + routes the deep-link
   (takes effect only after the daemon is REINSTALLED — see §2)
```

### 1. Tauri identity bootstrap — `apps/desktop/src-tauri/src`

A small one-shot run from the existing `lib::run()` setup hook (alongside `tray::setup` / `backend_supervisor::spawn_or_adopt`). Behaviour:

- **Substrate:** a dedicated sentinel file `~/.squirrel/.notif_identity` — its *presence* means bootstrap completed. There is **no** `~/.squirrel/config.json` in this project (the daemon reads `config.toml`; autostart is a `tauri-plugin-autostart` LaunchAgent). A sentinel avoids parsing/round-tripping either of those just to store one bit, and drops any "preserve other keys" concern.
- If the sentinel exists → return immediately (no permission query, no banner).
- Else **gate on authorization, not on `.show()` returning Ok** (R-1.1/R-1.2): call `app.notification().permission_state()`; if `NotDetermined`, call `request_permission()`. Only if the resulting state is authorized, emit a single `app.notification().builder().title("Squirrel").body("Notifications are on 🐿️").show()`; on `Ok`, create the sentinel (`std::fs::File::create`).
- If permission is denied/not granted → log WARN, **do not** create the sentinel, do not block startup; the bootstrap is retried on the next launch (R-1.4). This is the crucial fix: `tauri-plugin-notification`'s `.show()` returns `Ok` even when permission is denied, so gating the sentinel on `.show()` alone would set it on a denied first launch and never warm the identity.
- All IO is best-effort: errors are logged at WARN and never block startup.

The single *authorized* emit through `UNUserNotificationCenter` is what registers the bundle so that `terminal-notifier -sender` is honored thereafter (the macOS rule documented in `native-notification-banner` R-1.10).

### 2. Daemon sender branding — `agent-pack/companions/macos-reminders/reminder-daemon.sh`

In `show_notification_terminal_notifier()` add `-sender com.metuur.squirrel` to **both** branches (Silent and sounded). Nothing else in the invocation changes:

```sh
# Silent branch
terminal-notifier \
    -group org.squirrel.reminders \
    -sender com.metuur.squirrel \
    -title "$title" -subtitle "$subtitle" -message "$body" -open "$url"

# Sounded branch
terminal-notifier \
    -group org.squirrel.reminders \
    -sender com.metuur.squirrel \
    -title "$title" -subtitle "$subtitle" -message "$body" -open "$url" \
    -sound "$SOUND"
```

The `show_notification_osascript()` and `show_dialog_fallback()` paths are left **unchanged** — neither can carry a custom icon, and they remain the fallbacks when `terminal-notifier` is unavailable or permission is denied.

> **Source vs runtime (R-2.5).** `agent-pack/…/reminder-daemon.sh` is the edit source of truth. `dmg-staging/…` and `pkg-staging/…` are build-regenerated and not read at runtime — do not hand-edit them. The **runtime** daemon is the *installed* copy: `install.sh` sets `DAEMON_SCRIPT="${SCRIPT_DIR}/reminder-daemon.sh"` and bakes that absolute path into the launchd plist via `__DAEMON_PATH__`. Therefore editing `agent-pack/` updates only future installs; an **existing install stays unbranded until the daemon is reinstalled** (re-run `install.sh` / reinstall the app payload). This reinstall step is a documented user action (R-5.1).

> **Packaging the branded daemon (R-5.3).** The edit reaches a shippable installer only by **rebuilding the bundle**: `make build-installers-arm64 BUMP=patch` runs `_maybe-bump` (→ `scripts/bump_version.py patch`) then `scripts/build-dmg.sh --arm64-only`, which regenerates `dmg-staging/`/`pkg-staging/` from `agent-pack/` — so the shipped DMG/.pkg carries the `-sender` daemon at a new version. Use `make build-pkg BUMP=patch` for the guided `.pkg`. The `BUMP` is required so the installed payload version moves with the behaviour change (do not ship the daemon edit under the same version).

### 3. Spec + docs

- `docs/ears/native-notification-banner.md`: `R-1.6` — remove the "SHALL NOT pass `-sender`" clause, require `-sender com.metuur.squirrel`, and defer sound to `notification-sound-selection` (do **not** re-pin `Submarine`, which would conflict with branding R-2.2); `R-1.10` — replace the deferral with a delivered/superseded note pointing to this spec.
- `docs/lld/native-notification-banner.md`: update the D-6 / external `terminal-notifier` block (the "v1 — no `-sender`" comment) to reflect `-sender` is now included.
- **Test inversion (R-6.1):** `apps/cli/tests/test_emitters.sh` currently asserts `assert_not_contains … "-sender"` (~line 104). This must be inverted to assert the invocation **contains** `-sender com.metuur.squirrel` in both the Silent and sounded branches, with the `-open` URL (incl. `?action=`) unchanged. Shipping the daemon edit without this turns an existing green test red.
- Document the one-time user actions in `docs/release.md` (or the companion README): (a) grant **System Settings → Notifications → Squirrel**, and (b) **reinstall the daemon** for existing installs (R-2.5).

## Constraints

- **macOS branding rule:** `-sender` is honored only after `com.metuur.squirrel` has emitted ≥1 notification via `UNUserNotificationCenter`. The first-launch bootstrap is the mechanism that satisfies this precondition; without it, the daemon's `-sender` is a no-op until the app happens to post its first organic banner.
- **No per-notification image:** `tauri-plugin-notification` v2 has no macOS banner-image API; the Tauri banner icon is the app-bundle icon (`icon.icns`, already the Squirrel logo). `terminal-notifier -appIcon` is **not** used — Apple ignores it since Big Sur; only `-sender` reliably controls the icon.
- **`osascript` cannot be branded** — its banner always shows Script Editor. It stays the unbranded fallback.
- **Idempotent, non-blocking bootstrap:** the flag persists across launches; a failed/denied emit must not set the flag and must not block startup.
- **Signed-bundle dependency:** branding only manifests for the installed, signed `/Applications/Squirrel.app` with notification permission granted; a `cargo run`/`tauri dev` build will still show a generic icon (different/again identity) — expected, not a regression.
- No new dependencies on either side; `tauri-plugin-notification` and `terminal-notifier` are already present.

## Key Decisions

- **First-launch one-shot via a `~/.squirrel/.notif_identity` sentinel file**, not an in-memory guard and not a JSON/TOML key — survives restarts so the identity is established exactly once, and a presence-only marker needs no parser or key-preservation logic. (Rejected: `config.json` — does not exist in this project; rejected: a key in `config.toml` — forces a TOML round-trip for one bit; rejected: emit on every launch — noisy; rejected: rely on organic notifications only — leaves a window where daemon reminders are unbranded.)
- **Gate the sentinel on permission *authorization*, not on `.show()` returning Ok** — `tauri-plugin-notification`'s `.show()` returns `Ok` even when permission is denied, so an Ok-gated flag would be set on a denied first launch and the identity would never warm. Querying/requesting permission first and only creating the sentinel when authorized makes the bootstrap retry until it actually registers. (This is the load-bearing correctness decision.)
- **`-sender`, not `-appIcon`** — `-sender` posts as the real app (correct icon + click activates Squirrel) and is the only lever modern macOS honors; `-appIcon` is silently ignored post-Big-Sur. (Rejected: `-appIcon`/`-contentImage` branding.)
- **Leave `osascript` unbranded** rather than shelling a fake app — there is no supported way to brand `osascript`; the daemon already prefers `terminal-notifier`, so the unbranded path is rare. (Rejected: replacing `osascript` with an AppleScript that targets Squirrel — unsupported, fragile.)
- **Edit the source `agent-pack/` daemon only**, not the `dmg-staging/` copy — staging is regenerated by packaging.

## Out of Scope

- Branding the `osascript` fallback or the `display dialog` last-resort path.
- Per-notification custom images / rich attachments on either surface.
- Click-to-action on Tauri banners (still unsupported on macOS — routed via the tray, unchanged).
- Linux/Windows notification icons.
- Any change to notification copy, cadence, sound, dedup, or cooldown logic.
