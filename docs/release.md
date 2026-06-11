# Release & distribution

Squirrel has two distribution paths today. Pick the right one for your
audience:

| Path | Audience | Ships | Command |
|---|---|---|---|
| **Tauri `.app`** | End users who want the desktop popup | Squirrel.app + bundled `squirrel-backend` sidecar (PyInstaller, wired via `bundle.externalBin` in `tauri.conf.json`) | `cd apps/desktop && pnpm tauri build` |
| **Full installer DMG** | Power users who want CLI + agent-pack (Claude/Codex skills) | `squirrel` CLI + `squirrel-backend` + `agent-pack/` + launchd setup | `./scripts/build-dmg.sh` |

Both produce a `.dmg`. The two backends bind `127.0.0.1:3939` so only one
can run at a time on a given machine — the supervisor's port probe will
adopt whichever started first.

## First-time dev-machine setup

Required once per machine for either build path:

```bash
# Python backend bundler
pip install pyinstaller

# Node deps
pnpm install
```

For the Tauri path you also need Rust + `xcode-select --install` (for the
`codesign` and `hdiutil` CLIs used by Tauri's bundler).

## Building the Tauri `.app` (signed universal)

Export your signing credentials in your shell profile or a gitignored `.envrc`
(never commit these values):

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export APPLE_ID="your-apple-id@example.com"
export APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx"   # app-specific password
export APPLE_TEAM_ID="TEAMID"                  # 10-char team ID
```

Then build from `apps/desktop/`:

```bash
cd apps/desktop
pnpm tauri:build
```

`pnpm tauri:build` is a wrapper (`apps/desktop/scripts/tauri-build.sh`) that:
1. Checks the keychain for a Developer ID Application cert
2. Checks the required env vars (`APPLE_ID`, `APPLE_PASSWORD`, `APPLE_TEAM_ID`)
3. Invokes `pnpm tauri build -- --target universal-apple-darwin`

Tauri then runs in this order:
1. `pnpm build` (desktop SPA → `dist/`)
2. `pnpm tauri:prebuild-backend` — PyInstaller builds arm64 + x86_64 slices,
   strips extended attributes, lipo's them into a universal Mach-O, places it
   at `src-tauri/bin/squirrel-backend-<host-triple>`
3. `cargo build --release` (universal Rust binary)
4. Bundle: sign `.app` (including the sidecar) → notarize → staple → package `.dmg`

Artifacts land at:
- `apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/macos/Squirrel.app`
- `apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/dmg/Squirrel_<version>_universal.dmg`

Both are signed and stapled. The build emits a `signed: <path> identity=<authority> stapled=yes`
line per artifact on completion.

**Dev iteration (no signing):** omit `APPLE_SIGNING_IDENTITY` (or leave it unset) and run
`pnpm tauri:build`. The wrapper emits a `WARN` line and produces an unsigned `.app` — suitable
for local testing only. End users will see a Gatekeeper warning.

### Verify a signed build

```bash
# Signing chain
codesign -dv --verbose=4 apps/desktop/src-tauri/target/universal-apple-darwin/release/bundle/macos/Squirrel.app
# Notarization staple
xcrun stapler validate Squirrel.app
# Gatekeeper assessment
spctl --assess --type execute --verbose Squirrel.app
# Expected: accepted source=Notarized Developer ID
```

Also verify the embedded sidecar:

```bash
codesign -dv --verbose=4 Squirrel.app/Contents/Resources/squirrel-backend-*-apple-darwin
# Should show the same Developer ID Application authority as the .app
```

## Building the installer DMG (signed universal)

```bash
./scripts/build-dmg.sh
```

With `APPLE_SIGNING_IDENTITY` set (plus `APPLE_ID`, `APPLE_PASSWORD`,
`APPLE_TEAM_ID`), the script:

1. Builds universal (arm64 + x86_64) `squirrel` CLI and `squirrel-backend`
   via PyInstaller (Rosetta for the x86_64 slice on Apple Silicon)
2. Strips extended attributes (`xattr -cr`) before signing
3. Signs both staged binaries with `codesign --force --options runtime --timestamp`
4. Verifies both signatures (`codesign --verify --strict --deep`) before packaging
5. Creates the DMG via `hdiutil`
6. Signs the DMG
7. Notarizes via `xcrun notarytool submit --wait`; fails the build on any non-Accepted verdict
8. Staples via `xcrun stapler staple`
9. Asserts Gatekeeper state via `spctl --assess`

Output: `squirrel-installer-macos.dmg` — signed, notarized, stapled.

**Dev iteration:** omit `APPLE_SIGNING_IDENTITY` and run `./scripts/build-dmg.sh`. All
signing/notarization steps are skipped; the script emits
`WARN: APPLE_SIGNING_IDENTITY unset — producing unsigned installer (dev iteration mode)`.
The resulting DMG is unsigned and `installer/install.sh` will refuse to install from it.

## One-time developer setup (signing credentials)

### 1. Apple Developer Program enrollment ($99/year)

- Enroll at https://developer.apple.com/programs/
- Individual is fine (no D-U-N-S number, faster approval — ~24h)
- Grants the right to issue Developer ID certificates

### 2. Create a "Developer ID Application" certificate

Outside-the-App-Store distribution requires this specific cert type.

- Easiest path: Xcode → Settings → Accounts → your Apple ID → Manage
  Certificates → `+` → **Developer ID Application**
- Alternative: developer.apple.com/account/resources/certificates → `+` →
  **Developer ID Application** → upload a CSR from Keychain Access
- Confirm: `security find-identity -v -p codesigning` should list
  `1) ABCD1234... "Developer ID Application: Your Name (TEAMID)"`

Copy the 10-character `TEAMID` (the part in parentheses) to your password manager.

### 3. App-specific password for `notarytool`

- Go to https://appleid.apple.com → Sign-In and Security → App-Specific Passwords → `+`
- Label it `tauri-notarize`
- Copy the generated password (`xxxx-xxxx-xxxx-xxxx`) to your password manager

### 4. Export credentials

Create a gitignored `.envrc` or add to your shell profile:

```bash
# .envrc (never commit this file)
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export APPLE_ID="your-apple-id@example.com"
export APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx"
export APPLE_TEAM_ID="TEAMID"
```

Verify:

```bash
echo "$APPLE_TEAM_ID" | wc -c          # should print 11 (10 chars + newline)
security find-identity -v -p codesigning | grep "$APPLE_TEAM_ID"
```

### 5. Common gotchas

- **PyInstaller extended attributes** — `xattr -cr` runs automatically on every slice
  before `codesign`. If you ever see "resource fork, Finder information, or similar
  detritus not allowed", re-run the build script; it cleans up automatically.
- **Two binaries to sign in the Tauri path** — the `.app` itself and
  `squirrel-backend-<TARGET_TRIPLE>` inside `Contents/Resources/`. Tauri's bundler
  re-signs the sidecar automatically when it's declared via `externalBin`.
- **Hardened runtime** — required for notarization. Tauri sets `--options=runtime`
  by default; `build-dmg.sh` uses `--options runtime` explicitly. No `.entitlements`
  file is needed for the current capability set.
- **CI (Phase 2)** — headless signing via GitHub Actions is a separate change.
  See `docs/tasks/app-signing-and-notarization.md` Unit 7 for scope.

## Notification branding (post-install user actions)

Branded reminder banners — the Squirrel logo on the notification and a click
that opens the app at the project — require two one-time actions on each
machine. Spec: [`docs/ears/notification-icon-branding.md`](ears/notification-icon-branding.md).

1. **Grant notification permission.** Open **System Settings → Notifications →
   Squirrel** and allow notifications. macOS only honours the reminders
   daemon's `-sender com.metuur.squirrel` branding after Squirrel has emitted
   at least one notification through the notification center with permission
   granted; the app's first-launch bootstrap does this automatically once
   permission is allowed. Until then banners may render a generic icon — the
   expected *cold-identity window*, not a regression.

2. **Reinstall the daemon (existing installs only).** The reminders daemon is
   referenced by an absolute path baked into its launchd plist, so an
   already-installed copy stays unbranded until it is replaced. Re-run
   `installer/install.sh` (or reinstall the app payload) to pick up the
   `-sender` daemon. Fresh installs from a release built after this change
   already carry it.

## Auto-updates

Once signing is in place, Tauri's updater plugin can be enabled. It
verifies update payloads against a pubkey embedded in the binary; only
matching signed updates install. Out of scope for the initial signing
work — track separately when you're ready.
