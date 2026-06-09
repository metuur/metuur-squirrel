# Notification Icon Branding — Tasks

Source specs: `docs/hld/notification-icon-branding.md`, `docs/lld/notification-icon-branding.md`, `docs/ears/notification-icon-branding.md`.
Delivers the `native-notification-banner` `R-1.10` deferral. Touch points: `apps/desktop/src-tauri/src` (Tauri bootstrap), `agent-pack/companions/macos-reminders/reminder-daemon.sh` (daemon `-sender`), `apps/cli/tests/test_emitters.sh` (test inversion), docs, and a release rebuild.

Build sequence: Tauri bootstrap ∥ daemon `-sender` → tests → docs → release rebuild → manual smoke.

---

## Unit 1: Notification-identity bootstrap (Tauri)

- [x] 1.1 Permission-gated one-shot bootstrap module (est: ~50m)
  - acceptance:
    - R-1.1 — on start, if `~/.squirrel/.notif_identity` is absent, query `permission_state()`; if `NotDetermined`, `request_permission()`.
    - R-1.2 — only IF authorized, emit one `tauri-plugin-notification` banner; create the sentinel **only after** `.show()` returns `Ok`.
    - R-1.3 — if the sentinel exists, no-op (no permission query, no emit, no recreate).
    - R-1.4 — if denied/not granted: no emit, no sentinel, log WARN, do not block startup (retried next launch).
  - verify: unit/harness test (R-6.3) — authorized → emit + sentinel created; denied → no sentinel, retried; sentinel present → no-op. `cargo build` clean.
  - note: gating on authorization (not on `.show()` Ok) is the load-bearing fix — `.show()` returns `Ok` even when denied.

- [ ] 1.2 Wire bootstrap into `lib::run()` setup hook (deps: 1.1, est: ~15m)
  - acceptance:
    - R-1.5 — called alongside `tray::setup` / `backend_supervisor::spawn_or_adopt`; best-effort, never blocks startup; no change to any existing organic notification, tray, supervisor, or cache behaviour.
  - verify: `cargo build`; manual — first launch (permission granted) fires exactly one bootstrap banner; relaunch fires none; existing tray/notifications unaffected.

## Unit 2: `terminal-notifier` sender branding (daemon)

- [x] 2.1 Add `-sender com.metuur.squirrel` to both terminal-notifier branches (est: ~15m)
  - acceptance:
    - R-2.1 — `-sender com.metuur.squirrel` added alongside existing `-group/-title/-subtitle/-message/-open <url>`; the `-open` URL (incl. `?action=` from `compose_deeplink`) is unchanged.
    - R-2.2 — sounded branch keeps `-sound <SOUND>` with `-sender`; Silent branch omits `-sound`, keeps `-sender`.
    - R-2.3 — no change to title/subtitle/message/group/url/truncation/sound behaviour.
  - verify: edit `agent-pack/companions/macos-reminders/reminder-daemon.sh` only (not `dmg-staging/`/`pkg-staging/`); `bash -n` clean; covered by 6.1.

## Unit 3: Unbranded fallbacks (unchanged)

- [ ] 3.1 Confirm osascript / dialog fallbacks + emitter order untouched (deps: 2.1, est: ~10m)
  - acceptance:
    - R-3.1 / R-3.2 — `show_notification_osascript()` and the `display dialog` last-resort path are byte-unchanged.
    - R-3.3 — emitter-selection order (terminal-notifier → osascript → dialog) preserved; only the terminal-notifier branch augmented.
  - verify: `git diff agent-pack/.../reminder-daemon.sh` shows changes confined to `show_notification_terminal_notifier()`; existing emitter-order tests still pass.

## Unit 4: Platform constraints & scope (guards)

- [ ] 4.1 Constraint audit — no `-appIcon`, no Tauri per-notification image, scope held (deps: 1.2, 2.1, est: ~10m)
  - acceptance:
    - R-4.1 — no `-appIcon`/`-contentImage` added to terminal-notifier.
    - R-4.2 — no per-notification image set on the Tauri side (banner = app-bundle icon).
    - R-4.3 / R-4.5 — dev-build generic icon and the signed-install cold-identity window are documented as expected, not regressions.
    - R-4.4 — no backend/SQLite/web-UI/copy/cadence/sound/dedup/cooldown changes.
  - verify: `git diff` scoped to `apps/desktop/src-tauri/src`, `agent-pack/...`, `apps/cli/tests/...`, and `docs/`; grep confirms no `-appIcon`.

## Unit 5: Documentation, supersession & release

- [x] 5.2 Update parent `native-notification-banner` R-1.6 / R-1.10 + LLD D-6 (est: ~15m)
  - acceptance:
    - R-5.2 — R-1.6 requires `-sender`, defers sound to `notification-sound-selection`; R-1.10 marked delivered/superseded; LLD D-6 / invocation block reflect `-sender`.
  - verify: done this session — `grep "-sender" docs/ears/native-notification-banner.md` and `grep DELIVERED docs/lld/native-notification-banner.md`.

- [ ] 5.1 Document permission grant + daemon reinstall in `docs/release.md` / companion README (deps: 2.1, est: ~20m)
  - acceptance:
    - R-5.1 — document (a) grant System Settings → Notifications → Squirrel, and (b) reinstall the daemon (R-2.5) for existing installs.
  - verify: `docs/release.md` (or README) contains both steps; cross-links the branding spec.

- [ ] 5.3 Produce branded release via bundle rebuild (deps: 1.2, 2.1, 6.1, est: ~20m)
  - acceptance:
    - R-2.5 / R-5.3 — run `make build-installers-arm64 BUMP=patch` (or `make build-pkg BUMP=patch`); version bumps and `dmg-staging/`/`pkg-staging/` regenerate from `agent-pack/`, so the shipped installer carries the `-sender` daemon at a new version.
  - verify: built DMG/.pkg staged daemon contains `-sender com.metuur.squirrel`; `VERSION`/manifests reflect the bump.

## Unit 6: Testing

- [x] 6.1 Invert `test_emitters.sh` `-sender` assertion (deps: 2.1, est: ~20m)
  - acceptance:
    - R-6.1 / R-6.2 — replace the `assert_not_contains … "-sender"` at `apps/cli/tests/test_emitters.sh:104` with an `assert_contains … "-sender com.metuur.squirrel"` for **both** Silent and sounded branches; assert the `-open` URL (incl. `?action=`) is unchanged.
  - verify: `bash apps/cli/tests/test_emitters.sh` green; the old `R-1.10 NO -sender` case is removed/updated.

- [x] 6.3 Bootstrap unit/harness test (deps: 1.1, est: ~30m)
  - acceptance:
    - R-6.3 — authorized → emit + sentinel created; denied → no sentinel, retried next start; sentinel present → no-op.
  - verify: `cargo test` (src-tauri) green against a temp `$HOME`/sentinel path.

- [ ] 6.4 Manual smoke on a warmed signed install (deps: 5.3, 5.1, est: ~20m)
  - acceptance:
    - R-2.4 / R-6.4 — after reinstall + permission granted, `reminder-daemon.sh --force` shows the Squirrel logo and clicking opens the popup at the project via the `?action=focus` deep-link; a Tauri banner also shows the squirrel.
  - verify: visual confirmation on-device (manual — not automatable).
