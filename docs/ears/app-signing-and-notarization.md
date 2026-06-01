# App Signing & Notarization — EARS Specifications

EARS keywords used:
- `THE SYSTEM SHALL` — always-on
- `WHEN <trigger>, THE SYSTEM SHALL` — event-driven
- `IF <condition>, THE SYSTEM SHALL` — conditional / gate
- `WHERE <context>, THE SYSTEM SHALL` — environment / location scoped

`THE SYSTEM` in this document means the Squirrel macOS build and install pipeline — specifically the modified `apps/desktop/scripts/build-backend-sidecar.sh`, `scripts/build-dmg.sh`, `installer/install.sh`, the `pnpm tauri build` invocation, and (Phase 2) `.github/workflows/release.yml`.

---

## Unit 1: Universal binary production

| ID | EARS statement |
|---|---|
| R-1.1 | WHEN `apps/desktop/scripts/build-backend-sidecar.sh` runs and the host is `aarch64-apple-darwin`, THE SYSTEM SHALL produce a Mach-O binary at `apps/desktop/src-tauri/bin/squirrel-backend-aarch64-apple-darwin` whose `lipo -archs` output equals exactly `arm64 x86_64`. |
| R-1.2 | WHEN `apps/desktop/scripts/build-backend-sidecar.sh` runs and the host is `x86_64-apple-darwin`, THE SYSTEM SHALL produce a Mach-O binary at `apps/desktop/src-tauri/bin/squirrel-backend-x86_64-apple-darwin` whose `lipo -archs` output equals exactly `arm64 x86_64`. |
| R-1.3 | WHEN `scripts/build-dmg.sh` runs to completion, THE SYSTEM SHALL produce `dmg-staging/bin/squirrel` whose `lipo -archs` output equals exactly `arm64 x86_64`. |
| R-1.4 | WHEN `scripts/build-dmg.sh` runs to completion, THE SYSTEM SHALL produce `dmg-staging/bin/squirrel-backend` whose `lipo -archs` output equals exactly `arm64 x86_64`. |
| R-1.5 | WHEN any PyInstaller binary is produced, THE SYSTEM SHALL strip extended attributes from it (`xattr -cr`) before any subsequent `codesign` invocation. |
| R-1.6 | IF Rust's `x86_64-apple-darwin` target is not installed on the host (per `rustup target list --installed`), THE SYSTEM SHALL exit non-zero with the message `error: x86_64-apple-darwin Rust target not installed — run 'rustup target add x86_64-apple-darwin'` and SHALL NOT produce a partial bundle. |
| R-1.7 | IF Rosetta is not available on an Apple Silicon host attempting to produce the x86_64 PyInstaller slice, THE SYSTEM SHALL exit non-zero with a message naming Rosetta and pointing at `softwareupdate --install-rosetta`. |

---

## Unit 2: Tauri-path signing & notarization

| ID | EARS statement |
|---|---|
| R-2.1 | WHEN `pnpm tauri build -- --target universal-apple-darwin` runs with `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`, and `APPLE_SIGNING_IDENTITY` exported and a Developer ID Application cert present in the keychain, THE SYSTEM SHALL produce a `.app` at `apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/macos/Squirrel.app` whose `codesign -dv --verbose=4` output contains `Authority=Developer ID Application:` and the configured team ID. |
| R-2.2 | WHEN `pnpm tauri build` produces a `.app`, THE SYSTEM SHALL ensure the embedded `squirrel-backend-<TARGET_TRIPLE>` Mach-O inside `Squirrel.app/Contents/Resources/` (or wherever Tauri 2 lands sidecars) carries the same `Authority=Developer ID Application:` signature as the parent `.app`. |
| R-2.3 | WHEN `pnpm tauri build` produces a `.app`, THE SYSTEM SHALL submit the bundle to Apple's notary service via `notarytool submit --wait` and SHALL fail the build (exit non-zero) if the verdict is anything other than `status: Accepted`. |
| R-2.4 | WHEN notarization is accepted for the Tauri `.app`, THE SYSTEM SHALL staple the ticket to the `.app` via `xcrun stapler staple` and SHALL fail the build if stapling exits non-zero. |
| R-2.5 | WHEN `pnpm tauri build` produces a `.dmg`, THE SYSTEM SHALL produce a `Squirrel_<version>_universal.dmg` (or Tauri 2's equivalent universal-target name) and SHALL ensure that `.dmg` itself is signed and stapled — `xcrun stapler validate` against the `.dmg` returns success. |
| R-2.6 | WHERE the host has no Developer ID Application cert in any keychain (per `security find-identity -v -p codesigning` returning no matching identity), THE SYSTEM SHALL exit non-zero before invoking `cargo build` with the message `error: no Developer ID Application identity in keychain — see docs/release.md for enrollment` and SHALL NOT produce a partial bundle. |
| R-2.7 | IF `APPLE_ID` or `APPLE_PASSWORD` or `APPLE_TEAM_ID` is unset when a signing build is requested, THE SYSTEM SHALL exit non-zero with a message naming the missing env var and SHALL NOT submit anything to the notary service. |
| R-2.8 | IF `APPLE_SIGNING_IDENTITY` is unset, THE SYSTEM SHALL fall back to producing an unsigned bundle and SHALL log a single line `WARN: APPLE_SIGNING_IDENTITY unset — producing unsigned bundle (dev iteration mode)`. This is the only path that produces an unsigned artifact post-Phase-1. |

---

## Unit 3: Installer-DMG-path signing & notarization

| ID | EARS statement |
|---|---|
| R-3.1 | WHEN `scripts/build-dmg.sh` produces a PyInstaller binary at `dmg-staging/bin/squirrel`, THE SYSTEM SHALL sign it with `codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY"` before any subsequent step. |
| R-3.2 | WHEN `scripts/build-dmg.sh` produces a PyInstaller binary at `dmg-staging/bin/squirrel-backend`, THE SYSTEM SHALL sign it with `codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY"` before any subsequent step. |
| R-3.3 | WHEN `scripts/build-dmg.sh` invokes `hdiutil create`, THE SYSTEM SHALL ensure both `dmg-staging/bin/squirrel` and `dmg-staging/bin/squirrel-backend` have valid `codesign --verify --strict --deep` signatures, and SHALL fail with exit non-zero if either does not. |
| R-3.4 | WHEN `hdiutil create` produces `squirrel-installer-macos.dmg`, THE SYSTEM SHALL sign the resulting `.dmg` with `codesign --sign "$APPLE_SIGNING_IDENTITY"`. |
| R-3.5 | WHEN the signed `squirrel-installer-macos.dmg` exists, THE SYSTEM SHALL submit it to Apple's notary service via `xcrun notarytool submit "$DMG" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD" --wait` and SHALL fail the build if the verdict is not `Accepted`. |
| R-3.6 | WHEN notarization of `squirrel-installer-macos.dmg` is accepted, THE SYSTEM SHALL run `xcrun stapler staple squirrel-installer-macos.dmg` and SHALL fail the build if stapling exits non-zero. |
| R-3.7 | WHEN `scripts/build-dmg.sh` completes successfully, THE SYSTEM SHALL ensure `xcrun stapler validate squirrel-installer-macos.dmg` returns success and `spctl --assess --type open --context context:primary-signature squirrel-installer-macos.dmg` reports `accepted source=Notarized Developer ID`. |
| R-3.8 | WHERE `APPLE_SIGNING_IDENTITY` is unset, THE SYSTEM SHALL skip every signing/notarization/stapling step in `scripts/build-dmg.sh` and SHALL log `WARN: APPLE_SIGNING_IDENTITY unset — producing unsigned installer (dev iteration mode)`. The unsigned `.dmg` still produces; the installer-side gate (Unit 4) will refuse to install it. |

---

## Unit 4: End-user installer verification gate

| ID | EARS statement |
|---|---|
| R-4.1 | WHEN `installer/install.sh` runs and reaches the step that copies `$BIN_DIR/squirrel` to `$HOME/.local/bin/squirrel`, THE SYSTEM SHALL first run `codesign --verify --strict --deep "$BIN_DIR/squirrel"` and SHALL NOT proceed with the copy if the verification exits non-zero. |
| R-4.2 | WHEN `installer/install.sh` runs and reaches the step that copies `$BIN_DIR/squirrel-backend` to `$HOME/.local/bin/squirrel-backend`, THE SYSTEM SHALL first run `codesign --verify --strict --deep "$BIN_DIR/squirrel-backend"` and SHALL NOT proceed with the copy if the verification exits non-zero. |
| R-4.3 | IF `codesign --verify` exits non-zero for any binary in step R-4.1 or R-4.2, THE SYSTEM SHALL print `error: codesign verification failed for <name> — refusing to install. Re-download the DMG from <release URL>.` to stderr and SHALL exit 1 without modifying `~/.local/bin/`, `~/.squirrel/`, or `launchctl` state. |
| R-4.4 | WHEN `installer/install.sh` verifies a binary successfully, THE SYSTEM SHALL log `codesign verified: <name>` to stdout before the corresponding `cp`. |
| R-4.5 | THE SYSTEM SHALL NOT expose a `--force` or `--skip-codesign-check` flag in `installer/install.sh`. |
| R-4.6 | WHERE the binaries inside the mounted DMG are unsigned (e.g., a legacy build predating this change, or a dev build with `APPLE_SIGNING_IDENTITY` unset), THE SYSTEM SHALL exit non-zero per R-4.3. There is no signed-or-unsigned heuristic — verification is mandatory. |

---

## Unit 5: Configuration & environment

| ID | EARS statement |
|---|---|
| R-5.1 | THE SYSTEM SHALL read `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`, and `APPLE_SIGNING_IDENTITY` from the process environment in all signing-aware scripts (`apps/desktop/scripts/build-backend-sidecar.sh`, `scripts/build-dmg.sh`, and Tauri's bundler invocation). |
| R-5.2 | THE SYSTEM SHALL NOT commit any value of `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_SIGNING_IDENTITY`, or the certificate bytes to any tracked file in the repository. |
| R-5.3 | THE SYSTEM SHALL document the expected env-var layout in `docs/release.md` (updated content) and SHALL reference a developer-managed `.envrc` or shell profile that is gitignored. |
| R-5.4 | WHERE `apps/desktop/src-tauri/tauri.conf.json` contains a `bundle.macOS.signingIdentity` field, THE SYSTEM SHALL either set it via Tauri 2's env-interpolation syntax (if supported) or place the user-specific identity string in a gitignored overlay file (e.g., `tauri.conf.macos.json`) rather than the tracked config. |
| R-5.5 | THE SYSTEM SHALL preserve the existing `tauri.conf.json` field `bundle.macOS.minimumSystemVersion = "12.0"` unchanged. |
| R-5.6 | THE SYSTEM SHALL NOT introduce a `.entitlements` file in this change. The hardened-runtime defaults applied by Tauri's bundler and by `codesign --options runtime` in `scripts/build-dmg.sh` are sufficient given the current capability set at `apps/desktop/src-tauri/capabilities/default.json:23-32`. |

---

## Unit 6: Verification & observability

| ID | EARS statement |
|---|---|
| R-6.1 | WHEN any build path completes successfully, THE SYSTEM SHALL log a single summary line per signed artifact in the form `signed: <path> identity=<authority> stapled=yes` to stdout. |
| R-6.2 | WHEN any signing/notarization step fails, THE SYSTEM SHALL print the failing tool's stderr verbatim followed by a line identifying which build path and which step failed (e.g., `failed: installer-dmg path, step: notarytool submit, exit=1`). |
| R-6.3 | WHEN the build completes, THE SYSTEM SHALL produce a freshly-built artifact where `spctl --assess --type execute --verbose <Squirrel.app>` returns `accepted source=Notarized Developer ID` for the Tauri `.app`. |
| R-6.4 | WHEN the build completes, THE SYSTEM SHALL produce a freshly-built artifact where `spctl --assess --type open --context context:primary-signature <squirrel-installer-macos.dmg>` returns `accepted source=Notarized Developer ID` for the installer DMG. |
| R-6.5 | THE SYSTEM SHALL NOT print any value of `APPLE_PASSWORD`, the cert bytes, or any partial credential to stdout, stderr, or any log file. Tool output that would expose them SHALL be filtered or redirected to /dev/null. |

---

## Unit 7: CI (Phase 2)

| ID | EARS statement |
|---|---|
| R-7.1 | WHERE `.github/workflows/release.yml` exists, THE SYSTEM SHALL trigger only on `push.tags: ['v*']` events. |
| R-7.2 | WHEN the workflow runs, THE SYSTEM SHALL decode the `APPLE_CERT_BASE64` secret to a `.p12` file inside `$RUNNER_TEMP`, import it into a temporary keychain created with `security create-keychain`, and SHALL delete that keychain at the end of the job (including on failure, via a `cleanup` step that uses `if: always()`). |
| R-7.3 | WHEN the workflow imports the cert, THE SYSTEM SHALL set `security set-key-partition-list` so that `codesign` can use the cert without an interactive prompt. |
| R-7.4 | WHEN the workflow runs, THE SYSTEM SHALL execute both build paths — `pnpm tauri build -- --target universal-apple-darwin` and `scripts/build-dmg.sh` — and SHALL fail the entire workflow if either path fails. |
| R-7.5 | WHEN both build paths complete successfully, THE SYSTEM SHALL upload both `.dmg` files to the GitHub Release for the tag via `gh release upload` (or `gh release create` if the release does not yet exist). |
| R-7.6 | THE SYSTEM SHALL NOT log the value of any `APPLE_*` secret in the workflow output. GitHub Actions automatic masking is relied upon, but the workflow SHALL NOT echo secrets in any step. |
| R-7.7 | IF any step in the workflow leaks a secret (detected by GitHub's secret-scanning post-mortem or by a developer review), THE SYSTEM SHALL be patched within the same PR cycle and the leaked credential rotated. (Operational requirement, not a build-time check.) |
| R-7.8 | WHERE the workflow file does not yet exist (Phase 1 only), the rest of this Unit SHALL NOT block delivery of Phase 1. Phase 2 lands as a separate change. |

---

## Unit 8: Documentation

| ID | EARS statement |
|---|---|
| R-8.1 | WHEN Phase 1 ships, THE SYSTEM SHALL update `docs/release.md` so that lines currently in the "Future — adding Developer ID signing + notarization" section (lines 63–183) become operational instructions, not future-tense planning. |
| R-8.2 | WHEN Phase 1 ships, THE SYSTEM SHALL update `docs/install.md` so the primary install path describes the no-Gatekeeper-warning UX. The current right-click → Open instructions SHALL move to a "Installing legacy unsigned builds" subsection. |
| R-8.3 | WHEN Phase 2 ships, THE SYSTEM SHALL update `docs/release.md` to document the GitHub Actions workflow, the required secrets (`APPLE_CERT_BASE64`, `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_SIGNING_IDENTITY`), and how to rotate them. |
| R-8.4 | THE SYSTEM SHALL NOT publish step-by-step Apple Developer Program enrollment instructions in this repo beyond what already exists in `docs/release.md:69-103`. That enrollment is the user's responsibility; the docs reference Apple's URLs and stop there. |
