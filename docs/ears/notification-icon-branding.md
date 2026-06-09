# Notification Icon Branding — EARS Specifications

Keywords: `THE SYSTEM SHALL` (always-on) · `WHEN <trigger>` (event) ·
`WHILE <state>` (continuous) · `IF <condition>` (conditional/gate) ·
`WHERE <context>` (scoped). Scope: the macOS notification surfaces — the Tauri
desktop app (`apps/desktop`) and the reminders companion
(`agent-pack/companions/macos-reminders/reminder-daemon.sh`). This spec delivers
the `R-1.10` follow-up from `native-notification-banner` and supersedes its
deferral; it flips that spec's `R-1.6` to require `-sender`.

Persistence substrate: a dedicated sentinel file `~/.squirrel/.notif_identity`
(presence ⇒ bootstrap completed). There is **no** `~/.squirrel/config.json` in
this project — the daemon reads `config.toml` and autostart is a
`tauri-plugin-autostart` LaunchAgent; the sentinel avoids any round-trip through
those.

## Unit 1: Notification-identity bootstrap (Tauri)

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN the Tauri app starts AND the `~/.squirrel/.notif_identity` sentinel is absent, THE SYSTEM SHALL query the current notification permission state via `tauri-plugin-notification`, and IF that state is "not determined" THE SYSTEM SHALL request permission. |
| R-1.2 | IF notification permission is **authorized**, THE SYSTEM SHALL emit exactly one notification via `tauri-plugin-notification` (`UNUserNotificationCenter`) to register `com.metuur.squirrel` as a notification source, AND only after that emit is dispatched without error SHALL it create the `~/.squirrel/.notif_identity` sentinel. |
| R-1.3 | WHILE the `~/.squirrel/.notif_identity` sentinel exists, THE SYSTEM SHALL NOT re-query permission, emit the bootstrap notification, or recreate the sentinel on subsequent launches. |
| R-1.4 | IF notification permission is **denied or not granted**, THE SYSTEM SHALL NOT emit the bootstrap notification, SHALL NOT create the sentinel, SHALL log at WARN, AND SHALL NOT block startup — so the bootstrap is retried on the next launch (where the user may have granted permission in System Settings). |
| R-1.5 | THE bootstrap SHALL be the only behavioural addition to startup; it SHALL NOT alter any existing organic notification, tray, supervisor, or cache behaviour. |

## Unit 2: `terminal-notifier` sender branding (daemon)

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHERE the emitter is `terminal-notifier`, THE invocation SHALL include `-sender com.metuur.squirrel` in addition to the existing `-group org.squirrel.reminders`, `-title`, `-subtitle`, `-message`, and `-open <deep-link-url>` flags. THE `<deep-link-url>` is composed per `native-notification-banner` R-1.9 and, where an action applies, carries the `?action=<action>` query appended by `compose_deeplink` (e.g. `squirrel://projects/<id>?action=focus`); `-sender` SHALL NOT alter the URL passed to `-open`. |
| R-2.2 | WHILE the configured sound is not `Silent`, THE `terminal-notifier` invocation SHALL retain `-sound <SOUND>` alongside `-sender`; WHILE the sound is `Silent`, THE invocation SHALL omit `-sound` and retain `-sender`. (Sound selection itself is owned by `notification-sound-selection`; this requirement only asserts `-sender` is orthogonal to it.) |
| R-2.3 | THE `-sender` addition SHALL NOT change the title, subtitle, message, group, deep-link URL (including its `?action=` query), truncation, or sound-selection behaviour of the existing banner. *(Bash-testable: flag presence + unmodified URL.)* |
| R-2.4 | WHEN a `terminal-notifier` banner posted with `-sender com.metuur.squirrel` is displayed on a host whose identity is warmed (Unit 1 complete, permission granted), THE banner SHALL show the Squirrel app icon, AND WHEN it is clicked THE SYSTEM SHALL activate Squirrel and route the `-open` deep-link. *(Manual smoke — not bash-unit-testable.)* |
| R-2.5 | THE branded daemon SHALL take effect on a host only after the daemon is **reinstalled** (re-running `install.sh` / reinstalling the app payload), because the launchd plist references the installed daemon copy by absolute path (`__DAEMON_PATH__` = `${SCRIPT_DIR}/reminder-daemon.sh`); editing the repo `agent-pack/` source alone does not update an already-installed daemon. |

## Unit 3: Unbranded fallbacks (unchanged)

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL leave `show_notification_osascript()` unchanged; `osascript display notification` cannot carry a custom icon and SHALL remain the unbranded fallback used only when `terminal-notifier` is unavailable. |
| R-3.2 | THE SYSTEM SHALL leave the `display dialog` last-resort path unchanged. |
| R-3.3 | THE SYSTEM SHALL preserve the existing emitter-selection order (terminal-notifier → osascript → dialog) and only augment the `terminal-notifier` branch. |

## Unit 4: Platform constraints & scope

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL NOT pass `-appIcon`/`-contentImage` to `terminal-notifier` for branding; macOS ignores them since Big Sur and `-sender` is the only honored lever. |
| R-4.2 | THE SYSTEM SHALL NOT attempt to set a per-notification image on the Tauri side; the Tauri banner icon SHALL remain the app-bundle icon (`icon.icns`). |
| R-4.3 | WHERE the running build is an unsigned `tauri dev`/`cargo run` process, THE SYSTEM MAY show a generic notification icon; this SHALL NOT be treated as a regression. |
| R-4.4 | THE SYSTEM SHALL NOT modify any backend, SQLite, web-UI, notification copy, cadence, sound, dedup, or cooldown behaviour. |
| R-4.5 | WHILE `com.metuur.squirrel` has not yet emitted ≥1 notification via `UNUserNotificationCenter` with permission granted (bootstrap not yet completed — Unit 1), THE daemon's `-sender` SHALL be a no-op and banners MAY render the generic icon; this is the expected **cold-identity window**, not a regression. Branding becomes reliable only after the one-shot bootstrap succeeds. |

## Unit 5: Documentation & supersession

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL document, in `docs/release.md` or the companion README, the one-time user actions required for branding: (a) grant **System Settings → Notifications → Squirrel**, and (b) **reinstall the daemon** (per R-2.5) for an existing install. |
| R-5.2 | THE `native-notification-banner` spec `R-1.6` SHALL be updated to require `-sender com.metuur.squirrel` and SHALL defer sound behaviour to `notification-sound-selection` (not re-pin `Submarine`); `R-1.10` SHALL be marked delivered/superseded by this spec; the `native-notification-banner` LLD D-6 / external-emitter block SHALL be updated to reflect `-sender` is now included. |
| R-5.3 | THE branded daemon SHALL reach end users only via a **rebuilt bundle installer**: after editing the `agent-pack/` source (R-2.1), the release SHALL be produced with `make build-installers-arm64 BUMP=patch` (or `make build-pkg BUMP=patch`), which bumps the version and regenerates the `dmg-staging/` / `pkg-staging/` payloads from `agent-pack/` so the shipped installer carries the `-sender` daemon. A `BUMP`-less rebuild SHALL NOT be relied upon to signal the change (the version must move so the installed payload is identifiably new). |

## Unit 6: Testing

| ID    | EARS statement | Vehicle |
|-------|----------------|---------|
| R-6.1 | THE existing bash unit test `apps/cli/tests/test_emitters.sh` (currently asserting **no** `-sender` at line ~104) SHALL be updated to assert the `terminal-notifier` invocation **contains** `-sender com.metuur.squirrel` in **both** the Silent and sounded branches, and that the `-open` URL (including any `?action=` query) is unchanged. | automated |
| R-6.2 | R-2.1 / R-2.2 / R-2.3 (flag presence + URL/sound orthogonality) SHALL be covered by `test_emitters.sh`. | automated |
| R-6.3 | R-1.1–R-1.4 (permission-gated one-shot, sentinel created only when authorized, retried when denied) SHALL be covered by a Rust/unit or harness test asserting: authorized → emit + sentinel created; denied → no sentinel, retried next start; sentinel present → no-op. | automated |
| R-6.4 | R-2.4 (Squirrel icon renders + click activates Squirrel + deep-link routes) and R-4.3/R-4.5 (generic icon in dev / cold-identity window) SHALL be verified by **manual smoke** on a warmed, signed install: run `reminder-daemon.sh --force`, confirm the Squirrel logo and that clicking opens the popup at the project via the `?action=focus` deep-link. | manual |
