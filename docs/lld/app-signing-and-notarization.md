# App Signing & Notarization — Low-Level Design

## Architecture

Five layers, ordered from prerequisite to delivery:

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 0 — Apple credentials (user-owned, off-repo)            │
│   • Developer ID Application cert in login.keychain            │
│   • App-specific password for notarytool                       │
│   • $APPLE_ID, $APPLE_PASSWORD, $APPLE_TEAM_ID env vars        │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 1 — PyInstaller binary production (universal)            │
│   • apps/desktop/scripts/build-backend-sidecar.sh              │
│   • scripts/build-dmg.sh                                       │
│   Produces: arm64 + x86_64 slices, lipo'd into one binary      │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 2 — Tauri path                                           │
│   • tauri.conf.json: signingIdentity                           │
│   • Tauri bundler auto-signs .app + sidecar                    │
│   • Tauri bundler invokes notarytool + stapler                 │
│   Produces: Squirrel_<v>_universal.dmg (signed, notarized)     │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 3 — Installer DMG path                                   │
│   • scripts/build-dmg.sh: codesign each PyInstaller binary     │
│   • hdiutil create → squirrel-installer-macos.dmg              │
│   • codesign the .dmg                                          │
│   • notarytool submit --wait → xcrun stapler staple            │
│   Produces: squirrel-installer-macos.dmg (signed, notarized)   │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 4 — End-user installer gate                              │
│   • installer/install.sh: codesign --verify --strict --deep    │
│   • Refuses to install if any binary fails verification        │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│ Layer 5 — CI (Phase 2)                                         │
│   • .github/workflows/release.yml                              │
│   • Imports cert from APPLE_CERT_BASE64 → temp keychain        │
│   • Runs Layers 1–3 headlessly, uploads to gh release          │
└──────────────────────────────────────────────────────────────┘
```

Data flow per release:

```
Developer's machine (Phase 1) or GH Actions runner (Phase 2)
  │
  ├─→ build-backend-sidecar.sh
  │     PyInstaller (arm64) + PyInstaller (x86_64) → lipo → universal binary
  │     → apps/desktop/src-tauri/bin/squirrel-backend-<TARGET_TRIPLE>
  │
  ├─→ pnpm tauri build
  │     cargo build (universal) → Tauri bundler
  │     → codesign Squirrel.app + sidecar (Developer ID)
  │     → notarytool submit --wait
  │     → xcrun stapler staple Squirrel.app
  │     → hdiutil create Squirrel_<v>_universal.dmg
  │     → codesign the .dmg
  │     → notarytool submit --wait the .dmg
  │     → xcrun stapler staple the .dmg
  │
  └─→ scripts/build-dmg.sh
        PyInstaller squirrel (universal) + PyInstaller squirrel-backend (universal)
        → codesign each (Developer ID + --options runtime + --timestamp)
        → stage into dmg-staging/
        → hdiutil create squirrel-installer-macos.dmg
        → codesign the .dmg
        → notarytool submit --wait
        → xcrun stapler staple squirrel-installer-macos.dmg
```

### Component contracts

**`apps/desktop/scripts/build-backend-sidecar.sh`** (modified)
- Input: env (none required for signing; cert handled later by Tauri bundler)
- Behaviour: build PyInstaller binary twice (once for arm64, once for x86_64), then `lipo -create` into one universal output. Strip extended attributes (`xattr -cr`) to avoid the "resource fork detritus" codesign error documented at `docs/release.md:167-173`.
- Output: `apps/desktop/src-tauri/bin/squirrel-backend-universal-apple-darwin` (renamed from triple-specific naming) **or** keep `<TARGET_TRIPLE>` naming and produce one universal binary per recognised triple — see Key Decisions below.

**`apps/desktop/src-tauri/tauri.conf.json`** (modified)
- Add `bundle.macOS.signingIdentity` (read from env via `${APPLE_SIGNING_IDENTITY}` if Tauri 2 supports it; otherwise hardcode the cert name with the team-id placeholder documented).
- Set `bundle.targets` to include the universal `.dmg` variant (Tauri 2: `"all"` already covers DMG; universal-ness is driven by Rust target list, not Tauri bundle target).

**`apps/desktop/src-tauri/Cargo.toml`** (unchanged for signing; reviewed for universal)
- No new dependencies. `cargo build --target aarch64-apple-darwin` and `cargo build --target x86_64-apple-darwin` produce two binaries; Tauri bundler lipos them when both targets are specified.

**`scripts/build-dmg.sh`** (modified)
- Add `--target` loop around `pyinstaller --onefile` to produce arm64 and x86_64 binaries, then `lipo -create` into one universal binary per logical name (`squirrel`, `squirrel-backend`).
- Add `codesign --force --options runtime --timestamp --sign "$APPLE_SIGNING_IDENTITY"` against each binary before staging.
- After `hdiutil create`, sign the `.dmg` itself with `codesign --sign "$APPLE_SIGNING_IDENTITY"`.
- Add `xcrun notarytool submit --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_PASSWORD" --wait` against the `.dmg`.
- Add `xcrun stapler staple squirrel-installer-macos.dmg`.
- Guard the entire signing block behind `if [[ -n "${APPLE_SIGNING_IDENTITY:-}" ]]`; if unset, log a clear warning and continue to produce an unsigned `.dmg` (developer iteration mode).

**`installer/install.sh`** (modified)
- Before each `cp` at lines 158–172, run `codesign --verify --strict --deep "$BIN_DIR/<name>"`. If exit non-zero, print `error: codesign verification failed for <name> — refusing to install. Re-download the DMG.` and exit 1.
- No fallback, no `--force` flag exposed to end users. The signed-binary path is the only supported install path post-Phase-1.

**`.github/workflows/release.yml`** (new, Phase 2 only)
- Trigger: `push.tags: ['v*']`.
- Single job, `runs-on: macos-latest`.
- Steps:
  1. Checkout, install pnpm + Rust + PyInstaller.
  2. Decode `${{ secrets.APPLE_CERT_BASE64 }}` to a `.p12` file in `$RUNNER_TEMP`. Import into a temporary keychain with `security create-keychain` + `security import` + `security set-key-partition-list`.
  3. Export `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_SIGNING_IDENTITY` from secrets.
  4. Run `pnpm tauri build` (Tauri DMG path).
  5. Run `scripts/build-dmg.sh` (installer DMG path).
  6. `gh release create` or `gh release upload` with both `.dmg` files.
- Cert is in the keychain only for the duration of the job; the temp keychain is deleted at the end.

## Constraints

- **macOS-only signing.** No Linux or Windows code-signing in this change. The codebase's Windows/Linux builds (if any) remain unaffected.
- **Universal builds use lipo, not Rosetta.** Both arm64 and x86_64 native slices must be present in every Mach-O binary that ships. The Rust toolchain must have both `aarch64-apple-darwin` and `x86_64-apple-darwin` targets installed (`rustup target add x86_64-apple-darwin`).
- **PyInstaller cannot cross-compile.** Each `pyinstaller --onefile` invocation produces a binary for the host architecture. To get a universal binary, run PyInstaller twice (once per target, using `arch -arm64` and `arch -x86_64` prefixes on the host's Python, or with separate venvs), then `lipo -create`. Phase 1 assumes the developer's machine is Apple Silicon with Rosetta installed so it can run an `x86_64` Python under Rosetta to produce the x86_64 PyInstaller slice. Phase 2 (`macos-latest` runner — currently arm64) makes the same assumption.
- **Hardened runtime is mandatory for notarization.** `codesign --options runtime` must be passed; Tauri sets this by default for `.app`s but `scripts/build-dmg.sh` must pass it explicitly when signing the standalone PyInstaller binaries.
- **`codesign --timestamp` is mandatory for notarization.** Apple's notary service rejects bundles without a secure timestamp signature.
- **PyInstaller adds extended attributes that codesign refuses.** `xattr -cr <binary>` must run after PyInstaller and before `codesign`, per the known gotcha at `docs/release.md:167-173`.
- **Tauri auto-re-signs `externalBin` sidecars.** Per `docs/release.md:128`, Tauri's bundler signs the sidecar with the Developer ID identity even if PyInstaller already ad-hoc-signed it. The Tauri path does not need explicit `codesign` against the sidecar inside `build-backend-sidecar.sh` — Tauri handles it. The installer DMG path (Layer 3) **does** need explicit `codesign` because there is no Tauri bundler in that path.
- **Notarization is online and bounded but not instant.** `notarytool submit --wait` typically returns in 1–5 min (`docs/release.md:132`). Local Phase 1 builds tolerate this; CI Phase 2 must set a step timeout > 15 min and surface a clear failure if the verdict is `Invalid`.
- **`spctl --assess --type execute` is the canonical Gatekeeper check.** The success criteria in HLD reference this exact command; LLD honours it as the verification gate.
- **Apple notary service ingests one universal bundle per submission.** Per `.uncle-dev/research/2026-06-01-aarch64-bundle-intel-mac-install.md:191`, universal is not "two separate notarizations stitched together"; it is one bundle with two slices and one notary ticket.
- **No keychain unlock prompts mid-build.** Local Phase 1: developer's login keychain must be unlocked for the duration of the build, or the cert must be in a keychain accessed via `security unlock-keychain` before `codesign` runs. CI Phase 2: the temp keychain is created unlocked and stays unlocked for the job.
- **Secrets never enter the repo.** No `APPLE_*` values, no cert bytes, no app-specific password text in any tracked file. Local: `.envrc` or shell profile (already gitignored). CI: GitHub Actions secrets.
- **No `.entitlements` file.** Current capabilities at `apps/desktop/src-tauri/capabilities/default.json:23-32` do not require any. Tauri's default hardened runtime is sufficient.
- **Cannot test Phase 2 without first landing Phase 1 successfully.** The workflow's signing block is a direct translation of the local commands; if local doesn't work, CI won't.

## Key Decisions

### D1 — Tauri sidecar naming after universal: keep `<TARGET_TRIPLE>` or rename to `universal-apple-darwin`?

**Decision: keep `squirrel-backend-<TARGET_TRIPLE>` naming, but produce a universal binary per name Tauri requests.**

**Rejected alternative:** rename to `squirrel-backend-universal-apple-darwin`.

**Reason:** Tauri 2's `externalBin` mechanism expects per-triple naming and resolves `bin/squirrel-backend` to `bin/squirrel-backend-<host-triple>` at bundle time (`apps/desktop/scripts/build-backend-sidecar.sh:67-119`). Renaming the file requires patching Tauri's resolver or shipping multiple identical files. Producing a universal binary that lives at the triple-named path (e.g., `bin/squirrel-backend-aarch64-apple-darwin` containing both arm64 and x86_64 slices) is invisible to Tauri's resolver but correct at runtime — the kernel picks the matching slice. Caveat: Tauri may need both `squirrel-backend-aarch64-apple-darwin` and `squirrel-backend-x86_64-apple-darwin` as symlinks pointing at the same universal binary so resolution works on either host architecture during dev builds. The build script handles this.

### D2 — Where the Tauri-path notarization happens

**Decision: rely on Tauri 2's built-in notarization driven by `APPLE_*` env vars.**

**Rejected alternative:** manual `notarytool submit` in a post-build script.

**Reason:** Tauri 2 (`tauri-cli >= 2.0`) reads `APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID` and runs `notarytool submit --wait` + `stapler staple` against both `.app` and `.dmg` automatically when `signingIdentity` is set. Adding a manual post-step duplicates work and creates two places to maintain. The full installer DMG path (`scripts/build-dmg.sh`) gets manual `notarytool` invocations because there is no Tauri bundler in that path — that's its only reason for being explicit.

### D3 — Universal-build production for PyInstaller

**Decision: run PyInstaller twice (once per architecture, via `arch -arm64` and `arch -x86_64` prefixes against per-arch Pythons) and `lipo -create` the outputs.**

**Rejected alternatives:**
- **`pyinstaller --target-architecture universal2`**: not supported (PyInstaller does not cross-compile). The `--target-architecture` flag exists but only selects which slice of an existing universal Python to bake in; it requires a universal Python interpreter, which complicates the dev-machine setup.
- **Ship two separate binaries (arm64 + x86_64) and have the installer pick the right one**: doubles the DMG size, doubles the install logic complexity, and breaks the single-binary contract that `dmg-staging/bin/squirrel` currently assumes.

**Reason:** `lipo -create` is the canonical macOS universal-binary tool. It works on any Mach-O including PyInstaller's frozen Python interpreter + zipapp shim. The cost is doubled PyInstaller runtime per build (one arm64 pass + one x86_64 pass under Rosetta). For local Phase 1 on Apple Silicon, the x86_64 PyInstaller pass runs under Rosetta — assumed installed. For CI Phase 2 on `macos-latest` (currently arm64), same. If `macos-latest` ever switches to x86_64, the build script's arch detection adapts.

### D4 — Phase 1 (local) vs Phase 2 (CI) split

**Decision: land Phase 1 first as one deliverable, then Phase 2 as a follow-up change.**

**Rejected alternative:** land both phases in one mega-change.

**Reason:** Phase 1 is the substrate. Without a working local signing flow we cannot validate that the env vars, cert, app-specific password, and Tauri config interact correctly. CI just translates working local commands into a YAML workflow plus the secrets/keychain dance. Splitting also keeps blast radius small: if Phase 1 ships and we find issues, Phase 2 doesn't need to be reverted in lockstep. The EARS spec defines both phases; the implementation plan delivers them in two task batches.

### D5 — `installer/install.sh` failure mode on verification

**Decision: exit non-zero with a clear error; no `--force` escape hatch.**

**Rejected alternatives:**
- Warn and continue: defeats the purpose of the verification gate.
- Add `--force` flag: encourages users to bypass when something is wrong, which is exactly the scenario this gate exists to catch.

**Reason:** A user encountering this error has one of three states: (1) a tampered DMG (re-download), (2) a bug in the build pipeline (file an issue), or (3) a legacy unsigned DMG (use the older install path documented separately). None of those are addressed by a `--force` flag. Keeping the failure terminal keeps the security guarantee straightforward.

### D6 — Where the signing identity name lives

**Decision: read `APPLE_SIGNING_IDENTITY` from environment in both build scripts.** Tauri config also reads it via `${APPLE_SIGNING_IDENTITY}` env interpolation if Tauri 2 supports it; otherwise the `signingIdentity` field is set to a documented placeholder pattern (`Developer ID Application: <Your Name> (<TEAMID>)`) and the team-id-with-name string is composed at build time.

**Rejected alternative:** hardcode the identity string in `tauri.conf.json`.

**Reason:** The identity string contains the developer's name and team ID, which are user-specific. Hardcoding makes the repo unable to be built by anyone else. Reading from env keeps the config user-agnostic. If Tauri 2's `signingIdentity` field does not accept env interpolation, the LLD updates accordingly and the field is set in a `tauri.conf.macos.json` overlay that's gitignored (rather than the tracked `tauri.conf.json`).

### D7 — Universal Rust binary production for Tauri

**Decision: pass `--target aarch64-apple-darwin --target x86_64-apple-darwin` to `cargo build` via Tauri 2's `--target universal-apple-darwin` flag.**

**Rejected alternative:** manual two-target build + lipo of the Rust binary outside Tauri.

**Reason:** Tauri 2 supports `tauri build --target universal-apple-darwin` natively, which handles the dual cargo build + lipo step internally and produces a universal `.app`. The build script wires this through `pnpm tauri build -- --target universal-apple-darwin`.

## Out of Scope

- **Auto-updates / Tauri updater plugin.** Tracked separately; success criterion Goal 1 in HLD names it explicitly.
- **Windows / Linux signing.** Not in this change.
- **Mac App Store distribution.** Different cert tier, different review process.
- **Sparkle, custom DMG window layouts, install backgrounds.** Cosmetic.
- **Pre-release / TestFlight-style channels.** No staged rollout in this change.
- **Sigstore / cosign / non-Apple signing.** Apple Developer ID + notary service only.
- **Re-signing of historical releases.** Old `.dmg`s on existing releases stay as-is; users on old artifacts continue to use the right-click bypass documented in `docs/install.md`.
- **Local-keychain provisioning automation.** The developer manually creates / imports their Developer ID Application cert into login.keychain. No script automates this.
- **`.entitlements` file authoring.** Current capabilities do not require any. If a future feature adds camera/mic/network-server etc., that feature authors the entitlements.
- **CI for builds other than release tags.** Phase 2's workflow triggers on `push.tags: ['v*']` only. PR builds, branch builds, scheduled builds are out of scope.
- **Signing of the per-PR Tauri dev `.app` produced by `tauri dev`.** Dev builds run unsigned locally.
- **Replacing `docs/install.md`'s right-click bypass section entirely.** That section becomes a "legacy builds" subsection; the main path becomes the no-bypass path.
- **Adding `productsign` / `.pkg` installer support.** `.dmg` is the only distribution container.
