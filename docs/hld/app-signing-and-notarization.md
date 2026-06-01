# App Signing & Notarization — High-Level Design

## Overview

Squirrel ships two macOS distribution artifacts today and both are unsigned:

- **Tauri `.app` + `.dmg`** built by `pnpm tauri build` in `apps/desktop/` — bundles the React shell, the Rust binary, and the PyInstaller sidecar declared at `apps/desktop/src-tauri/tauri.conf.json:41`.
- **Full installer DMG** built by `scripts/build-dmg.sh` — bundles two PyInstaller binaries (`squirrel`, `squirrel-backend`), the agent-pack, a launchd plist template, and the user-facing `installer/install.sh` script.

Both are arm64-only Mach-O binaries. End users see a Gatekeeper warning on first launch and must use the right-click → Open bypass documented in `docs/install.md`. The installer script (`installer/install.sh:158-172`) copies binaries into `$HOME/.local/bin/` with no signature verification, so a tampered binary would install silently.

This change wires Apple Developer ID code-signing and notary-service notarization into both build paths, lipos the binaries into universal (arm64 + x86_64) bundles so they run on Intel Macs without architecture failures, adds `codesign -v` gating to `installer/install.sh`, and lands the work in two phases: **Phase 1 — local builds**, **Phase 2 — GitHub Actions**.

The Apple Developer Program enrollment, the Developer ID Application certificate, and the `notarytool` app-specific password are **user-owned prerequisites**. The spec describes the expected end state (`security find-identity -v -p codesigning` lists the cert; `APPLE_ID`/`APPLE_PASSWORD`/`APPLE_TEAM_ID` are exported); it does not automate the enrollment steps themselves.

Auto-updates (Tauri's updater plugin, currently absent — see `docs/release.md:178-183`) remain explicitly out of scope.

## Stakeholders & Impact

| Stakeholder | Today's pain | After this ships |
|---|---|---|
| **Non-technical end users (Tauri `.app` path)** | First launch shows "Squirrel cannot be opened because the developer cannot be verified". User must right-click → Open and confirm a second dialog (`docs/install.md:1-122`). Many users abandon at this step. | Double-click opens the app with no Gatekeeper warning. `spctl --assess --type execute` prints `accepted source=Notarized Developer ID`. |
| **Intel Mac users (both paths)** | arm64-only Mach-O binaries fail with `bad CPU type in executable` or silent dyld load failure on Intel hardware (`.uncle-dev/research/2026-06-01-aarch64-bundle-intel-mac-install.md:124`). The right-click bypass cannot fix this — it is an architecture failure, not a signature failure. | Universal binaries (`lipo -archs` shows `arm64 x86_64`) run on both Apple Silicon and Intel. Apple's notary service ingests a single universal bundle per submission. |
| **CLI / agent-pack users (full installer DMG path)** | DMG opens with Gatekeeper warning. Once inside, `installer/install.sh` `cp`s the two binaries to `$HOME/.local/bin/` with no signature check — a tampered or replaced DMG would install silently. | DMG opens clean. `installer/install.sh` verifies each binary with `codesign --verify --strict --deep` before copying; refuses the install with an explicit error if verification fails. |
| **Release authors (you)** | Each release requires manually telling users about the bypass, fielding "is this safe?" questions, and shipping unsigned arm64-only binaries that break on Intel hardware. | `pnpm tauri build` and `scripts/build-dmg.sh` produce signed, notarized, stapled, universal artifacts in one command locally. Phase 2 runs the same on GitHub Actions on every tag push. |
| **Future auto-update consumers** | Tauri's updater plugin requires signed bundles (`docs/release.md:180-183`); cannot enable today. | Prerequisite met (signed bundles exist). Auto-updater itself is **not** added in this change — tracked as a separate follow-up. |

## Goals

When this ships, the following are observable and true:

1. **Tauri path produces a signed, notarized, stapled, universal `.app` and `.dmg`.** `codesign -dv --verbose=4 Squirrel.app` shows the Developer ID Application identity; `xcrun stapler validate Squirrel.app` returns success; `spctl --assess --type execute --verbose Squirrel.app` prints `accepted source=Notarized Developer ID`; `lipo -archs Squirrel.app/Contents/MacOS/squirrel` prints `arm64 x86_64`.
2. **The PyInstaller sidecar inside `Squirrel.app/Contents/Resources/` is signed with the same identity.** `codesign -dv` on the inner binary returns the same Developer ID. (Tauri's bundler does this automatically because the sidecar is declared via `externalBin` at `tauri.conf.json:41`.)
3. **Full installer DMG (`squirrel-installer-macos.dmg`) is signed, notarized, and stapled.** Both inner PyInstaller binaries (`dmg-staging/bin/squirrel`, `dmg-staging/bin/squirrel-backend`) are individually signed with the Developer ID Application identity before `hdiutil create` runs. The resulting `.dmg` is then signed with `codesign`, submitted to `notarytool`, and stapled with `xcrun stapler staple`.
4. **Both PyInstaller binaries inside the installer DMG are universal.** `lipo -archs dmg-staging/bin/squirrel` and `lipo -archs dmg-staging/bin/squirrel-backend` both print `arm64 x86_64`.
5. **`installer/install.sh` verifies signatures before copying.** `codesign --verify --strict --deep` runs against `$BIN_DIR/squirrel` and `$BIN_DIR/squirrel-backend`. If either fails, the script exits non-zero with a user-facing error that names the failing binary; no `cp` runs.
6. **Phase 1 — local builds succeed.** With `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID` exported and the cert in the keychain, `pnpm tauri build` and `scripts/build-dmg.sh` each produce signed+notarized+stapled artifacts end-to-end with no manual `codesign` invocation by the user.
7. **Phase 2 — CI builds succeed.** A `.github/workflows/release.yml` workflow imports the Developer ID cert from base64-encoded secrets into a temporary keychain, runs the same two build paths, and uploads the resulting `.dmg` files as release assets.
8. **No credentials in the repo.** No `APPLE_*` env var values, no certificates, no passwords are committed. CI reads them from GitHub Actions secrets; local builds read them from the developer's shell profile or `.envrc` (gitignored).

## Non-Goals

- **No Apple Developer Program enrollment automation.** The $99/year enrollment, the Developer ID Application certificate generation, and the `notarytool` app-specific password are user-owned prerequisites the human performs once. The spec documents the expected end state, not the enrollment steps themselves.
- **No Mac App Store distribution.** Developer ID Application is the outside-the-App-Store cert type (`docs/release.md:75-91`). Mac App Store requires separate cert types and review process.
- **No auto-update mechanism.** Tauri's updater plugin is not installed in this change. `docs/release.md:180-183` calls it out as a separate follow-up once signed bundles exist.
- **No `.entitlements` file beyond hardened-runtime defaults.** Tauri's bundler sets `--options=runtime` by default. The current capability set (sidecar shell exec, notification, store, autostart, deep-link, process, global-shortcut per `apps/desktop/src-tauri/capabilities/default.json:23-32`) does not require additional entitlements. If a future change needs camera/microphone/etc., that change authors the `.entitlements` file.
- **No revocation of the existing right-click → Open documentation in `docs/install.md`.** That doc is updated to describe the post-signing UX, but the bypass instructions remain for users on builds older than this change.
- **No `productsign`-style installer-package (`.pkg`) distribution.** Squirrel ships `.dmg`s, not `.pkg`s. `codesign` and notarization of the `.dmg` is sufficient.
- **No CI for the Tauri path beyond GitHub Actions self-hosted or `macos-latest` runner.** Universal builds and Apple's notary service both work on Apple-provided runners.
- **No Sparkle, no DMG-mounted background images / install-folder window layout customization.** Cosmetic DMG enhancements are not in scope.
- **No protection against attackers with the user's keychain unlocked.** Standard macOS keychain ACLs apply; the cert and app-specific password live in the keychain or env vars. If those leak, separate revocation is the user's responsibility.

## Success Criteria

Done when the following are observable on a fresh macOS install:

1. **Tauri path — clean install on a Mac that has never built Squirrel.**
   - Download the signed `Squirrel_<version>_universal.dmg` from a fresh release.
   - Double-click. Mount. Drag Squirrel.app into `/Applications/`.
   - Double-click `Squirrel.app` in `/Applications/`. No Gatekeeper dialog appears.
   - `codesign -dv --verbose=4 /Applications/Squirrel.app` shows `Authority=Developer ID Application: <Your Name> (<TEAMID>)`.
   - `xcrun stapler validate /Applications/Squirrel.app` prints `The validate action worked!`.
   - `spctl --assess --type execute --verbose /Applications/Squirrel.app` prints `accepted source=Notarized Developer ID`.
   - `codesign -dv --verbose=4 /Applications/Squirrel.app/Contents/Resources/squirrel-backend-<TARGET_TRIPLE>` shows the **same** Developer ID Application authority. (Confirms the sidecar inherited the signature.)
   - `lipo -archs /Applications/Squirrel.app/Contents/MacOS/squirrel` prints `arm64 x86_64`.

2. **Installer DMG path — clean install on the same Mac.**
   - Download the signed `squirrel-installer-macos.dmg` from the same release.
   - Double-click. Mount. No Gatekeeper warning.
   - Run `Install Squirrel` (the in-DMG installer entry point).
   - `~/.local/bin/squirrel` and `~/.local/bin/squirrel-backend` exist; both pass `codesign --verify --strict --deep`.
   - The installer script logged a `codesign verified` line before each `cp`.
   - `lipo -archs ~/.local/bin/squirrel` prints `arm64 x86_64`. Same for `squirrel-backend`.
   - `launchctl list | grep org.squirrel` shows the service running.

3. **Tampered binary refusal.**
   - Mount the DMG. Edit one of the binaries (`echo trash >> /Volumes/Squirrel/bin/squirrel`).
   - Run `Install Squirrel`. The script exits non-zero with `error: codesign verification failed for bin/squirrel — refusing to install`. No file is copied to `~/.local/bin/`.

4. **Intel-Mac install.**
   - On an Intel Mac (or via Rosetta verification on Apple Silicon: `arch -x86_64 ~/.local/bin/squirrel --version`), both binaries run and print the version.
   - `lipo -info` confirms each binary contains an `x86_64` slice.

5. **Phase 1 — local end-to-end build.**
   - With `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID` exported, run `pnpm tauri build`. Output `.dmg` passes the Goal 1 checks above without any manual `codesign` or `notarytool` invocation.
   - With the same envs exported, run `scripts/build-dmg.sh`. Output `.dmg` passes the Goal 2 checks above.
   - Both runs are reproducible: a second run of each produces a signed bundle without prompting for keychain unlock more than once per session.

6. **Phase 2 — CI end-to-end build.**
   - Push a tag (`git tag v0.x.0 && git push --tags`). The `release.yml` workflow runs.
   - Workflow imports the Developer ID Application certificate from a `APPLE_CERT_BASE64` secret into a temp keychain at the start of the macOS job.
   - Both build paths run inside the workflow. Both upload signed+notarized+stapled `.dmg` artifacts to the GitHub Release.
   - Download both `.dmg`s from the release. They pass the Goal 1 and Goal 2 checks above on a fresh Mac.

7. **No secrets leaked.**
   - `git log -p` and `git grep` find zero occurrences of the `APPLE_PASSWORD` value, the cert bytes, or the team ID outside of CI workflow secret references (`${{ secrets.APPLE_* }}`).
   - The `.envrc` / shell profile path is documented in `docs/release.md` and explicitly gitignored.

8. **Documentation updated.**
   - `docs/release.md` reflects the post-signing release flow (the current "Future" section becomes the operational instructions).
   - `docs/install.md` describes the new no-bypass UX as the primary path; the right-click → Open bypass is moved to a legacy-builds section for users on old artifacts.
