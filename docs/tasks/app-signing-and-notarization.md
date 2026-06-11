# App Signing & Notarization — Tasks

Source of truth: `docs/ears/app-signing-and-notarization.md`. Each story names the EARS requirement IDs it satisfies.

**Two-phase delivery** (per LLD D4):
- **Phase 1** (Units 1–6, 8.1, 8.2) — local build flow signs/notarizes/staples both distribution paths.
- **Phase 2** (Unit 7, 8.3) — GitHub Actions workflow runs the same flow headlessly. Lands as a follow-up change after Phase 1 ships.

**Prerequisite stories (P0)** capture user-owned setup that must complete before any Phase 1 story can be verified. They are not implementation work; they are gates.

---

## Unit 0: Prerequisites (user-owned, off-repo)

- [x] 0.1 Enroll in Apple Developer Program ($99/year) (est: ~30m setup + ~24h Apple approval)
  - acceptance: developer.apple.com membership active; able to access "Certificates, Identifiers & Profiles".
  - verify: log in to https://developer.apple.com/account — membership status shows "Active".
  - note: not in scope to automate; spec stories below assume this is complete (per R-2.6, R-8.4).

- [x] 0.2 Create Developer ID Application certificate, install in login.keychain (deps: 0.1, est: ~10m)
  - acceptance: `security find-identity -v -p codesigning` lists a line like `1) ABCD1234... "Developer ID Application: <Name> (<TEAMID>)"`.
  - verify: copy the 10-char `TEAMID` to a password manager; satisfies R-2.6.

- [x] 0.3 Generate `notarytool` app-specific password (deps: 0.1, est: ~5m)
  - acceptance: app-specific password generated at appleid.apple.com → Sign-In and Security → App-Specific Passwords, labelled `tauri-notarize`.
  - verify: stored in password manager; format `xxxx-xxxx-xxxx-xxxx`; satisfies R-2.7's `APPLE_PASSWORD` env source.

- [x] 0.4 Export envs in shell profile / `.envrc` (deps: 0.2, 0.3, est: ~5m)
  - acceptance: `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_SIGNING_IDENTITY` set in a gitignored shell file (per R-5.2, R-5.3).
  - verify: `echo "$APPLE_TEAM_ID" | wc -c` returns 11 (10 chars + newline); `security find-identity -v -p codesigning | grep -q "$APPLE_TEAM_ID"`.

- [x] 0.5 Install Rust `x86_64-apple-darwin` target + confirm Rosetta on Apple Silicon (est: ~10m)
  - acceptance: `rustup target list --installed | grep -q x86_64-apple-darwin`; on Apple Silicon, `arch -x86_64 /usr/bin/true` exits 0 (Rosetta available).
  - verify: satisfies R-1.6 and R-1.7 prerequisite for universal builds.

---

## Unit 1: Universal binary production

- [x] 1.1 Modify `apps/desktop/scripts/build-backend-sidecar.sh` to produce a universal Mach-O sidecar (deps: 0.5, est: ~60m)
  - acceptance: R-1.1, R-1.2, R-1.5, R-1.6, R-1.7 — script runs PyInstaller twice (arm64 + x86_64 via Rosetta on Apple Silicon), lipos the outputs, runs `xattr -cr` on the result, lands at `apps/desktop/src-tauri/bin/squirrel-backend-<host-triple>`, exits non-zero with the documented messages if Rust x86_64 target or Rosetta is missing.
  - verify: `bash apps/desktop/scripts/build-backend-sidecar.sh && lipo -archs apps/desktop/src-tauri/bin/squirrel-backend-*-apple-darwin` prints `arm64 x86_64`. Manually break preconditions (remove Rust target temporarily) and confirm the documented error appears.

- [x] 1.2 Modify `scripts/build-dmg.sh` to produce universal `squirrel` and `squirrel-backend` (deps: 0.5, est: ~75m)
  - acceptance: R-1.3, R-1.4, R-1.5 — both PyInstaller binaries built twice (arm64 + x86_64) and lipo'd; `xattr -cr` runs on each before any subsequent step.
  - verify: `./scripts/build-dmg.sh` completes; `lipo -archs dmg-staging/bin/squirrel` and `lipo -archs dmg-staging/bin/squirrel-backend` both print `arm64 x86_64`.

---

## Unit 2: Tauri-path signing & notarization

- [x] 2.1 Wire `signingIdentity` and universal target into Tauri config (deps: 0.4, 1.1, est: ~45m)
  - acceptance: R-2.1, R-5.4, R-5.5, R-5.6 — `apps/desktop/src-tauri/tauri.conf.json` reads signing identity via Tauri 2 env interpolation (`${APPLE_SIGNING_IDENTITY}`) **or**, if unsupported, a gitignored `tauri.conf.macos.json` overlay carries it; `bundle.macOS.minimumSystemVersion = "12.0"` preserved; no `.entitlements` file added; `pnpm tauri build -- --target universal-apple-darwin` is the documented build command.
  - verify: with envs from 0.4 exported, `pnpm tauri build -- --target universal-apple-darwin` completes; `codesign -dv --verbose=4 apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/macos/Squirrel.app` shows `Authority=Developer ID Application:` and `$APPLE_TEAM_ID`.

- [x] 2.2 Confirm Tauri 2 auto-signs the externalBin sidecar (deps: 2.1, est: ~20m)
  - acceptance: R-2.2 — sidecar inside `Squirrel.app/Contents/Resources/` (Tauri 2 path) carries the same Developer ID Application authority as the parent `.app`.
  - verify: `codesign -dv --verbose=4 Squirrel.app/Contents/Resources/squirrel-backend-*-apple-darwin` shows the same `Authority=Developer ID Application: …(<TEAMID>)` line. If Tauri does not auto-sign (config gap), reopen 2.1.

- [x] 2.3 Confirm Tauri 2 notarizes + staples the `.app` (deps: 2.1, est: ~30m, mostly Apple wait)
  - acceptance: R-2.3, R-2.4 — Tauri's build invokes `notarytool submit --wait` and `stapler staple`; build fails if verdict is not `Accepted` or stapling exits non-zero.
  - verify: build log contains `notarytool` and `stapler` invocations; `xcrun stapler validate Squirrel.app` returns success; `spctl --assess --type execute --verbose Squirrel.app` prints `accepted source=Notarized Developer ID`.

- [x] 2.4 Confirm Tauri 2 produces a signed+stapled universal `.dmg` (deps: 2.3, est: ~15m)
  - acceptance: R-2.5 — `Squirrel_<version>_universal.dmg` exists, is signed, is stapled.
  - verify: `xcrun stapler validate Squirrel_<version>_universal.dmg` returns success; `codesign -dv` against the `.dmg` shows the Developer ID Application authority.

- [x] 2.5 Add missing-cert / missing-env guards around `pnpm tauri build` (deps: 2.1, est: ~30m)
  - acceptance: R-2.6, R-2.7, R-2.8 — a wrapper script (or `package.json` `tauri:build` script) checks the keychain via `security find-identity -v -p codesigning` and the required env vars before invoking `pnpm tauri build`; missing cert / envs exit non-zero with the documented messages; unset `APPLE_SIGNING_IDENTITY` triggers the dev-iteration WARN line and a deliberately unsigned bundle.
  - verify: temporarily unset each env in turn → the documented error appears, no `cargo build` runs. Unset `APPLE_SIGNING_IDENTITY` → build completes with `WARN: APPLE_SIGNING_IDENTITY unset` and the resulting `.app` has no Developer ID signature.

---

## Unit 3: Installer-DMG-path signing & notarization

- [x] 3.1 Sign each PyInstaller binary in `scripts/build-dmg.sh` (deps: 0.4, 1.2, est: ~30m)
  - acceptance: R-3.1, R-3.2 — `codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY"` runs against `dmg-staging/bin/squirrel` and `dmg-staging/bin/squirrel-backend` after staging.
  - verify: build script log shows two `codesign` invocations succeeding; `codesign --verify --strict --deep dmg-staging/bin/squirrel` and same for `squirrel-backend` exit 0.

- [x] 3.2 Add pre-`hdiutil` verification gate in `scripts/build-dmg.sh` (deps: 3.1, est: ~15m)
  - acceptance: R-3.3 — before `hdiutil create`, script verifies both binaries with `codesign --verify --strict --deep`; exits non-zero if either fails.
  - verify: manually corrupt one staged binary (`echo trash >> dmg-staging/bin/squirrel`) and re-run the `hdiutil` block → script aborts with a clear error naming the failing binary.

- [x] 3.3 Sign the installer `.dmg` after `hdiutil create` (deps: 3.2, est: ~15m)
  - acceptance: R-3.4 — `codesign --sign "$APPLE_SIGNING_IDENTITY" squirrel-installer-macos.dmg` runs after `hdiutil create` and before any subsequent step.
  - verify: `codesign -dv --verbose=4 squirrel-installer-macos.dmg` shows the Developer ID Application authority.

- [x] 3.4 Notarize and staple the installer `.dmg` (deps: 3.3, est: ~30m, mostly Apple wait)
  - acceptance: R-3.5, R-3.6 — `xcrun notarytool submit "$DMG" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD" --wait` runs and succeeds; `xcrun stapler staple squirrel-installer-macos.dmg` runs and succeeds; script aborts on any non-`Accepted` verdict.
  - verify: build log shows notarytool returning `status: Accepted`; `xcrun stapler validate squirrel-installer-macos.dmg` returns success.

- [x] 3.5 Bake `spctl` final-state assertion into `scripts/build-dmg.sh` (deps: 3.4, est: ~15m)
  - acceptance: R-3.7 — `spctl --assess --type open --context context:primary-signature squirrel-installer-macos.dmg` is invoked at end of build; script aborts if the output does not contain `source=Notarized Developer ID`.
  - verify: final build log contains an `spctl --assess` line returning `accepted source=Notarized Developer ID`.

- [x] 3.6 Unset-`APPLE_SIGNING_IDENTITY` dev fallback in `scripts/build-dmg.sh` (deps: 3.5, est: ~15m)
  - acceptance: R-3.8 — when `APPLE_SIGNING_IDENTITY` is unset, the script skips all signing/notarization/stapling steps and emits `WARN: APPLE_SIGNING_IDENTITY unset — producing unsigned installer (dev iteration mode)`.
  - verify: `APPLE_SIGNING_IDENTITY= ./scripts/build-dmg.sh` produces an unsigned `.dmg` with the warning in the log; no `codesign` or `notarytool` invocations occur.

---

## Unit 4: End-user installer verification gate

- [x] 4.1 Add `codesign --verify` calls before each `cp` in `installer/install.sh` (deps: 3.4, est: ~30m)
  - acceptance: R-4.1, R-4.2, R-4.4 — verify runs against `$BIN_DIR/squirrel` and `$BIN_DIR/squirrel-backend` before each copy; success path logs `codesign verified: <name>`.
  - verify: mount a signed DMG produced by 3.4 → run `Install Squirrel` → log shows two `codesign verified:` lines; `~/.local/bin/squirrel` and `~/.local/bin/squirrel-backend` exist.

- [x] 4.2 Implement refusal path in `installer/install.sh` (deps: 4.1, est: ~20m)
  - acceptance: R-4.3, R-4.5, R-4.6 — verification failure prints `error: codesign verification failed for <name> — refusing to install. Re-download the DMG from <release URL>.` to stderr; exits 1; no `cp`, no `launchctl`, no `~/.squirrel/` writes; no `--force` / `--skip-codesign-check` flag.
  - verify: edit a binary on the mounted DMG (`sudo dd if=/dev/random of=/Volumes/Squirrel/bin/squirrel bs=1 count=1 seek=100 conv=notrunc`) → run `Install Squirrel` → script exits 1, no files in `~/.local/bin/` touched, no launchd job created.

---

## Unit 5: Verification & observability

- [x] 5.1 Add per-artifact signed/stapled summary log line (deps: 2.4, 3.5, est: ~20m)
  - acceptance: R-6.1 — each successful build emits one `signed: <path> identity=<authority> stapled=yes` line per artifact (`Squirrel.app`, `Squirrel_<v>_universal.dmg`, `squirrel-installer-macos.dmg`).
  - verify: full build output contains exactly the expected `signed: …` lines in order; grep-able for release-script consumption.

- [x] 5.2 Verbatim stderr passthrough on signing/notarization failures (deps: 2.5, 3.6, est: ~15m)
  - acceptance: R-6.2 — on failure, the failing tool's stderr appears in the build log followed by `failed: <path-name> path, step: <step>, exit=<code>`.
  - verify: deliberately set `APPLE_PASSWORD=wrong` → notarytool fails → build log contains both Apple's verbatim error and the `failed:` summary line.

- [x] 5.3 Secret-leak audit pass on logs (deps: 5.1, 5.2, est: ~15m)
  - acceptance: R-6.5 — full build log (Tauri + installer-DMG path) contains zero occurrences of `$APPLE_PASSWORD`, the cert bytes, or any partial credential. Any tool output that would emit these is filtered or redirected.
  - verify: `pnpm tauri build 2>&1 | tee /tmp/tauri-build.log` and `./scripts/build-dmg.sh 2>&1 | tee /tmp/dmg-build.log`; `grep -F "$APPLE_PASSWORD" /tmp/*-build.log` returns no matches.

---

## Unit 6: Documentation (Phase 1)

- [x] 6.1 Rewrite `docs/release.md` "Future" section as current operational instructions (deps: 5.1, est: ~45m)
  - acceptance: R-8.1, R-5.1, R-5.3 — the section at `docs/release.md:63-183` becomes present-tense operational instructions; documents the env-var layout and the gitignored `.envrc` / shell-profile location.
  - verify: read the diff — no "Future —" language remains; the section reads as a runbook; a new contributor could reproduce a signed build from the doc alone.

- [x] 6.2 Restructure `docs/install.md` so the no-bypass UX is the primary path (deps: 5.1, est: ~30m)
  - acceptance: R-8.2 — primary install instructions describe the signed-build UX (double-click, drag to Applications); the right-click → Open Gatekeeper bypass moves to a "Installing legacy unsigned builds" subsection labelled as applicable only to builds older than this release.
  - verify: read the diff — the first H2 / H3 user encounters when reading the doc top-down is the no-bypass path; the legacy section is reachable but no longer the default.

---

## Unit 7: CI — Phase 2 (deferred to follow-up change)

Per LLD D4 and R-7.8, Phase 2 lands as a separate change after Phase 1 verifies end-to-end locally. Stories below are listed here for traceability against EARS Unit 7 but **not delivered in this change**.

- [ ] 7.1 Create `.github/workflows/release.yml` triggered on `push.tags: ['v*']` (deferred)
  - acceptance: R-7.1, R-7.4, R-7.5 — workflow runs on tag push, executes both build paths on `macos-latest`, uploads both `.dmg`s to the GitHub Release.

- [ ] 7.2 Temporary-keychain cert import + cleanup (deferred)
  - acceptance: R-7.2, R-7.3 — decode `APPLE_CERT_BASE64` to `.p12` in `$RUNNER_TEMP`; `security create-keychain`, `security import`, `security set-key-partition-list`; cleanup via `if: always()` step.

- [ ] 7.3 Workflow secret-leak controls (deferred)
  - acceptance: R-7.6, R-7.7 — no `echo` of `APPLE_*` secrets; rely on GitHub's automatic masking; operational requirement to rotate on leak.

- [x] 7.4 Phase-2 documentation in `docs/release.md`
  - acceptance: R-8.3 — document the workflow, the required secrets (`APPLE_CERT_BASE64`, `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_SIGNING_IDENTITY`), and rotation procedure.

---

## Coordination notes

- **0.1–0.5 block everything.** No Phase 1 story can be verified end-to-end without the cert + envs.
- **1.1 and 1.2 are independent** (different scripts, different binaries). Can run in parallel.
- **2.x depends on 1.1.** Tauri's bundler picks up the universal sidecar from `src-tauri/bin/`.
- **3.x depends on 1.2.** `scripts/build-dmg.sh` signs the binaries it itself produces.
- **4.x depends on 3.4** (need a real signed installer DMG to exercise the verification path).
- **Unit 5 and Unit 6 are after-the-fact** — observability hooks and docs. Can interleave with 2.x/3.x but acceptance verification needs 2.4 + 3.5 done.
- **Unit 7 is a separate change.** Do not start until Phase 1 has shipped and a release has actually gone out with signed `.dmg`s.

## Verification budget per build

Each clean Phase 1 verification pass:
- Tauri path: ~5–10 min (cargo universal build is the long pole, then 1–5 min notary wait).
- Installer DMG path: ~3–5 min (two PyInstaller passes per binary, then 1–5 min notary wait).
- Plan for ~20–30 min per end-to-end signed-build round-trip when iterating on 2.x/3.x.
