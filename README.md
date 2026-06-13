# Squirrel

Local-first focus & productivity companion. Monorepo.

## Installing (end users)

Squirrel ships in three flavors. Pick whichever fits your audience:

| Flavor                            | What you get                                                                                                    | Who it's for                                                               |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **All-in-one installer** (`.pkg`) | Guided double-click installer: **Squirrel.app** + `squirrel` CLI + `agent-pack/`, auto-configured (vault, config, and any AI agents you have). No Terminal. | **Most users — recommended.**                              |
| **Squirrel.app** (Tauri DMG)      | Just the desktop popup with a bundled backend that the app supervises itself. No terminal needed after install. | Just the tray popup, nothing else.                                         |
| **Full installer DMG** (below)    | `squirrel` CLI + backend + `agent-pack/` (Claude/Codex skills) + launchd service. No desktop app.               | Headless / CLI-only power users.                                           |

For the **all-in-one `.pkg`**: download `squirrel-macos.dmg`, mount it, and double-click the `.pkg` inside; click through the installer, then open Squirrel from `⌘+Space` → "Squirrel". It installs the app to `/Applications`, the `squirrel` CLI to `/usr/local/bin`, wires the agent-pack into any agents you have, and seeds a starter config + vault. Build instructions: [Building the all-in-one installer](#building-the-all-in-one-installer-pkg).

For the **Squirrel.app** path, see [`docs/install.md`](docs/install.md) — drag to Applications, then a one-time Gatekeeper bypass (right-click → Open) because the app is currently unsigned. The signing roadmap is in [`docs/release.md`](docs/release.md).

The instructions below cover the **full installer DMG** path.

**Prerequisites:** Claude Code, Codex, Cursor, Copilot, or Windsurf — plus a folder to use as your vault. Nothing else.

1. Download `squirrel-installer-macos.dmg`
2. Open it and double-click **Install Squirrel**
3. Answer two questions:
   - Which agent? (Claude Code / Codex / Cursor / Copilot / Windsurf)
   - Where is your vault? (existing folder or press Enter to create `~/squirrel-vault`)
4. Allow the notification permission prompt
5. Open your agent and type `/sq-status`

The installer places two self-contained binaries on your machine and registers the backend as a launchd service that starts automatically at login:

| What                              | Where                                                                       |
| --------------------------------- | --------------------------------------------------------------------------- |
| `squirrel` CLI                    | `~/.local/bin/squirrel`                                                     |
| `squirrel-backend` (API + web UI) | `~/.local/bin/squirrel-backend`                                             |
| Agent skills & commands           | `~/.claude/plugins/squirrel/` (or Codex/Cursor/Copilot/Windsurf equivalent) |
| Config                            | `~/.squirrel/config.toml`                                                   |
| Background service                | `~/Library/LaunchAgents/org.squirrel.web-ui.plist`                          |

### Upgrading

Run the same installer from a newer DMG. It detects the existing version, stops the service, swaps the binaries atomically, restarts the service, and replaces the agent-pack. Your `config.toml` is never touched.

### Uninstalling

Run the bundled uninstaller — it removes every Squirrel file across all install
types (app, CLI, launchd service, agent packs, app data) while **never touching
your vaults**:

```bash
# .pkg install:
/usr/local/share/squirrel/uninstall.sh

# DMG / manual-zip install: run uninstall.sh from the mounted DMG or unzipped folder
./uninstall.sh

# preview without deleting anything:
./uninstall.sh --dry-run
```

It reads your vault paths from `~/.squirrel/config.toml` first and preserves
them; only system paths (under `/usr/local`) prompt for your admin password.

### Background service

`squirrel-backend` serves the JSON API and the React web UI on `http://127.0.0.1:3939` (localhost only). launchd keeps it running — it restarts on crash and starts at login. Logs are at `~/.squirrel/web-ui.stdout.log` and `~/.squirrel/web-ui.stderr.log`.

---

## Building the installer (contributors)

Requires `pyinstaller` on the dev machine (not shipped to users):

```bash
pip install pyinstaller
make build-installers            # universal (arm64 + x86_64) → squirrel-installer-macos.dmg
make build-installers-arm64      # Apple-Silicon-only (skips the x86_64 slice + lipo)
make build-installers-dry        # preview steps without executing
```

Use `build-installers-arm64` on an Apple Silicon machine that doesn't have an
x86_64-capable Python (the universal build needs one to produce the x86_64 slice;
without it `lipo` fails). The arm64-only DMG won't run on Intel Macs.

**Versioning.** Add `BUMP=patch` (or `minor` / `major`) to bump the version
*before* building. It reads the canonical version from `apps/cli/pyproject.toml`,
then syncs the same number into every manifest (both `pyproject.toml`s,
`tauri.conf.json`, the desktop `Cargo.toml` `[package]`, all `package.json`s, and
the hardcoded plugin version in `apps/cli/squirrel`). Files are edited but **not**
committed or tagged — review the diff yourself. A plain build never changes the version.

```bash
make build-installers-arm64 BUMP=patch     # e.g. 0.7.0 → 0.7.1, then build
```

**Signing.** When the `APPLE_*` signing env vars **or** `APPLE_KEYCHAIN_PROFILE`
are set, the build signs the binaries + DMG, notarizes, staples, and asserts
Gatekeeper acceptance; the notarization step streams an elapsed-time heartbeat so
it doesn't look frozen while Apple scans. With nothing set it produces an
**unsigned** dev DMG (which `installer/install.sh` will refuse) and warns. See
[Signing & notarizing](#signing--notarizing-macos-distribution) for the one-time
credential setup. To keep your app-specific password out of `ps`, store it once
and use a keychain profile instead of `APPLE_PASSWORD`:

```bash
xcrun notarytool store-credentials squirrel-notary \
  --apple-id you@example.com --team-id TEAMID --password xxxx-xxxx-xxxx-xxxx
export APPLE_KEYCHAIN_PROFILE=squirrel-notary
```

What `make build-installers` does (signing/notarization steps run only when configured):

```
Step 1  pnpm -F squirrel-web-ui build     → apps/backend/app/dist/
Step 2  pyinstaller → dist/squirrel        (CLI, pure stdlib)
Step 3  pyinstaller → dist/squirrel-backend (API + React SPA embedded)
Step 4  assemble dmg-staging/
           bin/squirrel
           bin/squirrel-backend
           agent-pack/
           resources/plist.template
           resources/squirrel.toml.example
           VERSION
           "Install Squirrel"
Step 5  hdiutil → squirrel-installer-macos.dmg
```

Key files:

| File                                  | Purpose                                                              |
| ------------------------------------- | -------------------------------------------------------------------- |
| `scripts/build-dmg.sh`                | Builds the DMG artifact (runs on dev machine)                        |
| `installer/install.sh`                | End-user installer bundled inside the DMG                            |
| `scripts/bump_version.py`             | Syncs all manifests to one bumped version (`BUMP=` above)            |
| `apps/backend/launchd/plist.template` | launchd plist with `__PYTHON__`, `__SERVER_PY__`, `__PORT__`, `__TOKEN_FILE__`, `__HOME__` placeholders |

---

## Building the all-in-one installer (`.pkg`)

The all-in-one installer bundles the desktop app **and** the CLI **and** the
agent-pack into one guided, double-click `.pkg`.

`make build-pkg` is **Apple Silicon (arm64) only** — it skips the universal
x86_64 slice + `lipo`, which can't be produced on an Apple Silicon machine
without an x86_64 Python toolchain. It does the whole chain in one command:
freshly recompiles the arm64 `Squirrel.app` **and** the `dist/` CLI binaries,
then packages them — so the `.pkg` version always matches its contents. The
single public artifact is `squirrel-macos.dmg` (the signed `.pkg` wrapped in a
DMG); end users mount it and run the `.pkg` inside.

```bash
make build-pkg                  # rebuild arm64 app + CLI, package, then wrap → squirrel-macos.dmg
make build-pkg BUMP=patch       # bump (patch|minor|major), recompile, package — version-consistent
make build-pkg-fast             # reuse an already-built arm64 Squirrel.app + dist/ binaries (no recompile)
make build-pkg-dry              # print the steps without executing
```

> ⚠️ Don't combine `BUMP=` with `build-pkg-fast` — `-fast` reuses prior artifacts,
> so the `.pkg` would be labeled with the new version but contain the old build.
> Use `make build-pkg BUMP=…` (which recompiles) whenever bumping.

**What it installs** (root-owned payload, then a `postinstall` configures the
logged-in user):

| What                          | Where                                                              |
| ----------------------------- | ------------------------------------------------------------------ |
| `Squirrel.app`                | `/Applications/Squirrel.app`                                       |
| `squirrel` + `squirrel-backend` CLI | `/usr/local/bin/`                                            |
| Staged agent-pack + resources | `/usr/local/share/squirrel/`                                       |
| Per-user config + vault       | `~/.squirrel/config.toml`, `~/squirrel-vault` (seeded, never overwritten) |
| Agent-pack (per detected agent) | `~/.claude/plugins/squirrel`, `~/.codex/squirrel`, `~/.cursor/rules/squirrel`, `~/.windsurf/rules/squirrel` |

No launchd service — **the app owns the backend** (avoids a `:3939` port conflict
with a separately-installed service). The CLI reads the vault directly and works
standalone.

**Signing.** Needs a **Developer ID Installer** certificate (distinct from the
Developer ID *Application* cert used elsewhere — create it the same way at
[developer.apple.com → Certificates](https://developer.apple.com/account/resources/certificates)).
`build-pkg.sh` signs the app (`APPLE_SIGNING_IDENTITY`), signs the `.pkg`
(`APPLE_INSTALLER_IDENTITY`, auto-detected from the keychain if unset), then
notarizes + staples (same `APPLE_KEYCHAIN_PROFILE` / `APPLE_ID` credentials as
the DMG path). With no identity it builds an **unsigned** dev `.pkg` (Gatekeeper
will block it).

> **Hardened-runtime entitlements.** The PyInstaller `--onefile` backend extracts
> `libpython3.12.dylib` to a temp dir and `dlopen()`s it at runtime. Under the
> hardened runtime (`--options runtime`) macOS rejects that load with
> *"code signature … different Team IDs"* unless the binary carries
> `com.apple.security.cs.disable-library-validation` — otherwise the signed
> backend **crash-loops (exit 255)** and never serves `:3939`. The entitlement
> lives in `apps/desktop/src-tauri/Entitlements.plist` and is applied when signing
> the standalone CLI binaries (`build-dmg.sh`) and the app + bundled sidecar
> (Tauri via `tauri.conf.json`, plus `build-pkg.sh`'s inside-out re-sign).

Key files: `scripts/build-pkg.sh`, `apps/desktop/src-tauri/Entitlements.plist`,
`installer/pkg/scripts/postinstall`, `installer/pkg/distribution.xml.template`,
`installer/pkg/resources/`.

> **Launching:** Squirrel is a menu-bar app. After install, `⌘+Space` → "Squirrel"
> brings the popup forward (the app handles macOS `Reopen` + single-instance
> relaunch); the menu-bar icon toggles it too.

---

## Building the desktop popup (contributors)

Also requires `pyinstaller` on the dev machine — the Tauri app bundles a PyInstaller-built `squirrel-backend` inside `Contents/Resources/` so the `.app` is self-sufficient (no launchd or separate install needed).

```bash
pip install pyinstaller
make build                  # → Squirrel.app + .dmg (unsigned)
```

What `make build` does (via Tauri's `beforeBundleCommand`):

```
Step 1  pnpm build                              → apps/desktop/dist/  (Tauri SPA)
Step 2  pnpm tauri:prebuild-backend             → src-tauri/bin/squirrel-backend-<TARGET_TRIPLE>
        (PyInstaller; embeds apps/backend/app/dist/ for the React web UI)
Step 3  cargo build --release
Step 4  bundle .app + .dmg
```

Artifacts land at:

- `apps/desktop/src-tauri/target/release/bundle/macos/Squirrel.app`
- `apps/desktop/src-tauri/target/release/bundle/dmg/Squirrel_<version>_<arch>.dmg`

The bundled backend is supervised by the Tauri app (see `apps/desktop/src-tauri/src/backend_supervisor.rs`): it's spawned on launch, health-checked every 30s, respawned on crash (bounded), and SIGTERM'd on quit. No launchd plist needed.

Iterating on the backend without rebuilding the whole bundle:

```bash
cd apps/desktop && pnpm tauri:prebuild-backend   # rebuilds just the sidecar
```

`make build` produces an **unsigned** app — fine for local testing, but other Macs
show a Gatekeeper warning. For distribution you need a signed + notarized + stapled
bundle. The steps below are the exact one-time setup; [`docs/release.md`](docs/release.md)
has the longer-form reference.

### Signing & notarizing (macOS distribution)

#### 1. Prerequisites

- Apple Developer Program membership ($99/yr)
- Rust targets for your build:
  ```bash
  rustup target add aarch64-apple-darwin x86_64-apple-darwin
  ```
  A `universal` build needs both; an Apple-Silicon-only build needs just `aarch64-apple-darwin`.

#### 2. Create a "Developer ID Application" certificate

[developer.apple.com → Certificates](https://developer.apple.com/account/resources/certificates)
→ **+** → **Software → Developer ID Application** → choose the **G2 Sub-CA** intermediary.

It asks for a CSR. Generate one either via Keychain Access (*Certificate Assistant →
Request a Certificate From a Certificate Authority…*, "Saved to disk"), or via openssl:

```bash
openssl req -new -newkey rsa:2048 -nodes \
  -keyout DeveloperID.key \
  -out DeveloperID.certSigningRequest \
  -subj "/emailAddress=you@example.com/CN=Your Name/C=US"
```

Upload the **`.certSigningRequest`** (not the `.key`), then download the resulting `.cer`.

#### 3. Import the identity into your keychain

If you used openssl, bundle cert + key into a `.p12` first. **Use `-legacy`** — OpenSSL 3.x's
default encryption can't be read by macOS's keychain (you'll get `MAC verification failed`):

```bash
# DER cert → PEM
openssl x509 -inform DER -in developerID_application.cer -out developerID_application.pem

# cert + key → legacy .p12
openssl pkcs12 -export -legacy \
  -inkey DeveloperID.key -in developerID_application.pem \
  -out DeveloperID.p12 -name "Developer ID Application" \
  -passout pass:CHANGEME

# import, allowing codesign/productsign to use the key
security import DeveloperID.p12 -k ~/Library/Keychains/login.keychain-db \
  -P CHANGEME -T /usr/bin/codesign -T /usr/bin/security -T /usr/bin/productsign
```

Install Apple's intermediate CAs so the chain validates — without them `find-identity`
reports **0 valid identities** even though the import "succeeded":

```bash
curl -fsSLO https://www.apple.com/certificateauthority/DeveloperIDG2CA.cer
curl -fsSLO https://www.apple.com/certificateauthority/AppleRootCA-G2.cer
security import DeveloperIDG2CA.cer -k ~/Library/Keychains/login.keychain-db
security import AppleRootCA-G2.cer  -k ~/Library/Keychains/login.keychain-db
```

Verify:

```bash
security find-identity -v -p codesigning
# 1) <hash> "Developer ID Application: Your Name (TEAMID)"
#    1 valid identities found
```

#### 4. App-specific password for notarization

[appleid.apple.com](https://appleid.apple.com) → Sign-In and Security →
**App-Specific Passwords** → **+**. Copy the `xxxx-xxxx-xxxx-xxxx` value, then sanity-check
it authenticates:

```bash
xcrun notarytool history --apple-id you@example.com \
  --password xxxx-xxxx-xxxx-xxxx --team-id TEAMID
# "No submission history." = credentials OK
```

#### 5. Export credentials

Create a **gitignored** `.envrc` in the repo root (never commit it):

```bash
export APPLE_SIGNING_IDENTITY="Developer ID Application: Your Name (TEAMID)"
export APPLE_ID="you@example.com"
export APPLE_TEAM_ID="TEAMID"                  # 10-char team ID
export APPLE_PASSWORD="xxxx-xxxx-xxxx-xxxx"    # app-specific password, not your Apple ID password
```

#### 6. Build

```bash
cd apps/desktop
set -a; source ../../.envrc; set +a

pnpm tauri:build                                 # universal (arm64 + x86_64) — default
TAURI_TARGET=aarch64-apple-darwin pnpm tauri:build   # Apple Silicon only
```

The wrapper (`scripts/tauri-build.sh`) checks the keychain + env vars, runs
`tauri build` (sign → notarize → staple the `.app`), then **notarizes + staples the
`.dmg`** too (Tauri only signs the DMG, so the wrapper finishes the job) and verifies
both artifacts. It tolerates Tauri's cosmetic DMG Finder-window AppleScript step, which
exits non-zero in headless contexts *after* the artifacts are built. Override the build
target with the `TAURI_TARGET` env var (defaults to `universal-apple-darwin`). Artifacts:

```
target/release/bundle/macos/Squirrel.app          # workspace-root target/ (Cargo workspace)
target/release/bundle/dmg/Squirrel_<version>_<arch>.dmg
```

#### 7. Verify

```bash
codesign -dv --verbose=4 Squirrel.app          # signing chain + TeamIdentifier
xcrun stapler validate Squirrel.app            # notarization staple
spctl --assess --type execute --verbose Squirrel.app
# → accepted  source=Notarized Developer ID
```

---

## Publishing the landing page & download

Once you've built a DMG, **`scripts/deploy-landing.sh`** ships it: it uploads the
bundle to Cloudflare R2 and (re)deploys the public landing page that links to it —
in one command.

```bash
./scripts/deploy-landing.sh          # upload dmg + update manifest + deploy pages
```

What it does:

1. **Uploads the bundle** — pushes the macOS `.dmg` to the R2 bucket `squirrel` at
   `dmg/squirrel-macos-v<version>.dmg`, served from `https://squirrel-file.metuur.com/dmg`.
2. **Updates the download manifest** — rewrites `landing/pages/downloads.json` to point
   at that version/URL (via `scripts/update-landing-download.sh`).
3. **Deploys the landing page** — `wrangler pages deploy landing/pages`, to the project's
   production branch (`squirrel`) by default so it lands in Production.

The version is read from `package.json` (strip a leading `v`). The `.dmg` is auto-located —
it checks `squirrel-macos-v<version>-arm64.dmg`, `squirrel-macos-arm64.dmg`,
`squirrel-macos.dmg`, then the Tauri `target/.../dmg/Squirrel_<version>_aarch64.dmg`
paths — unless you pass `--dmg`.

**Prerequisites:** `wrangler` (logged in via `wrangler login`) and `jq`.

| Flag                | Effect                                                                 |
| ------------------- | --------------------------------------------------------------------- |
| `--pages-only`      | Only redeploy the landing page (skip the R2 upload)                   |
| `--dmg-only`        | Only upload the `.dmg` + update the manifest (skip the Pages deploy)  |
| `--dmg /path.dmg`   | Use a specific bundle instead of auto-locating                        |
| `--version 0.8.0`   | Override the version (default: `package.json`)                        |
| `--branch <name>`   | Deploy to a specific Pages branch                                     |
| `--preview`         | Deploy as a Preview off the current git branch (not Production)       |
| `--dry-run`         | Print every action without executing it                              |

Typical release flow: `make build-pkg` (or `build-dmg.sh`) → `./scripts/deploy-landing.sh`.
Note this is distinct from `scripts/publish-release.sh` / `scripts/publish.sh`, which cut
a GitHub Release / GHCR artifact rather than the R2-hosted landing download.

---

## Installing for GitHub Copilot

Squirrel integrates with GitHub Copilot by placing files on disk — no GitHub App or cloud service needed. Both VS Code Copilot Chat and the Copilot CLI are supported.

### User-level install (default — applies to all workspaces)

```bash
./agent-pack/scripts/install-copilot.sh --yes
```

Skills land at `~/.copilot/agents/squirrel-<name>.agent.md`, slash-command prompts at `~/.copilot/prompts/sq-<cmd>.prompt.md`, and hook registration at `~/.copilot/hooks/squirrel.json`. A manifest block is appended to `~/.copilot/copilot-instructions.md`.

You can override the destination with the `COPILOT_HOME` env var.

### Workspace-level install (files committed to the repo)

```bash
./agent-pack/scripts/install-copilot.sh --workspace --yes
```

Writes to `.github/agents/`, `.github/prompts/`, `.github/copilot-instructions.md`, and `.github/hooks/squirrel.json`. Commit the generated files so teammates pick up the Squirrel integration automatically.

### Key flags

| Flag           | Effect                                                         |
| -------------- | -------------------------------------------------------------- |
| `--workspace`  | Write to `.github/` instead of `~/.copilot/`                   |
| `--link`       | Create symlinks instead of copies (auto-updates on `git pull`) |
| `--dry-run`    | Preview without writing anything                               |
| `--yes` / `-y` | Non-interactive                                                |
| `--no-config`  | Skip seeding `~/.squirrel/config.toml`                         |

After install, restart VS Code and try `/sq-where-am-i` in Copilot Chat.

---

## Layout

```
squirrel/
├── apps/
│   ├── desktop/          # Tauri v2 + React + TypeScript (macOS menu-bar app) — Phase 1
│   ├── cli/              # Python `squirrel` CLI + lib/ (migrated from v0.5)
│   └── backend/          # stdlib HTTP server + React web UI (API on :3939)
├── agent-pack/           # Skills, commands, hooks, templates (installed into AI agents)
├── installer/            # End-user install.sh (bundled inside the DMG)
├── scripts/              # Dev scripts — build-dmg.sh produces the installer DMG
├── docs/                 # LID + EARS docs (hld/ lld/ ears/ tasks/)
│   └── legacy/v0.5/      # Reference docs from the v0.5 first version
├── package.json          # pnpm workspace root
├── pnpm-workspace.yaml
└── Cargo.toml            # Cargo workspace root
```

Future siblings (created when each phase starts):

- `apps/obsidian-plugin/` — Obsidian integration
- `crates/vault-watcher/`, `crates/vault-core/` — shared Rust libraries
- `packages/ui/`, `packages/ipc-contracts/`, `packages/vault-schema/` — shared TS

## Migrated from v0.5 (adhd-context-bridge)

The first version of Squirrel (v0.5.0, `~/others/ai-agents/adhd-context-bridge`) was copied in. The source repo is preserved untouched as a reference. Mapping:

| v0.5 source                                                                                    | New location                             | Notes                                                            |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------- | ---------------------------------------------------------------- |
| `lib/*.py` + `squirrel` + `tests/`                                                             | `apps/cli/`                              | Python core + CLI entry + 24 tests                               |
| `companions/web-ui/`                                                                           | `apps/backend/`                          | Flask `server.py` + Vite `app/` frontend (node_modules stripped) |
| `companions/macos-reminders/`                                                                  | `agent-pack/companions/macos-reminders/` | launchd daemon, will be folded into Tauri                        |
| `companions/menubar*/` (Swift)                                                                 | not migrated                             | Superseded by `apps/desktop/` (Tauri)                            |
| `skills/` `commands/` `hooks/` `templates/` `examples/` `config/` `scripts/` `.claude-plugin/` | `agent-pack/`                            | Agent integrations                                               |
| `companions/{codex,cursor}/`                                                                   | `agent-pack/companions/`                 | Per-agent adapters                                               |
| `install.sh` `Makefile` `INSTALL*.md`                                                          | `agent-pack/`                            | Installer belongs with the pack                                  |
| `docs/` + `ARCHITECTURE.md` + old `README.md` + old `CLAUDE.md`                                | `docs/legacy/v0.5/`                      | Preserved unchanged                                              |

## Develop

```bash
pnpm install
make dev                # pnpm tauri dev (adopts the running backend on :3939)
make backend-start      # in a second terminal: python3 apps/backend/server.py --port 3939
make build              # produces an unsigned Squirrel.app + .dmg (bundles PyInstaller backend)
```

`make help` lists every target. Most useful day-to-day:

| Target                  | What it does                                                      |
| ----------------------- | ----------------------------------------------------------------- |
| `make dev`              | Tauri popup in dev mode — supervisor adopts whatever's on `:3939` |
| `make dev-all`          | preflight backend check + `make dev`                              |
| `make build`            | full unsigned Tauri bundle with embedded backend                  |
| `make backend-start`    | run the backend directly (for `make dev` to adopt)                |
| `make backend-build`    | rebuild the React web UI served by the backend                    |
| `make build-installers` | the other distribution path: CLI + agent-pack DMG                 |
| `make build-pkg`        | all-in-one `.pkg`: app + CLI + agent-pack, auto-configured        |
| `make test-cli`         | run the Python test suite                                         |

Per-package commands work via filter:

```bash
pnpm -F @squirrel/desktop dev
pnpm -F @squirrel/desktop build
```

## macOS Notifications (reminder daemon)

The reminder daemon (`agent-pack/companions/macos-reminders/reminder-daemon.sh`) emits
banners with an optional deep-link back to the Squirrel popup.

### Optional: `terminal-notifier`

```bash
brew install terminal-notifier
```

`terminal-notifier` is **optional**. When it is on `$PATH` the banner includes an
`-open squirrel://…` URL so clicking the notification foregrounds the Squirrel popup
and scrolls to the relevant card. Without it the daemon falls back to
`osascript display notification`, which shows a no-click banner (the URL is silently
dropped because `osascript` cannot open custom schemes from a notification action).

If notification permission for Script Editor is also denied the daemon falls back further
to a modal `osascript display dialog` as a last resort.

### v1 icon caveat

v1 banners display with the **generic Terminal icon**, not the Squirrel app icon. Showing
the Squirrel branding requires passing `-sender com.metuur.squirrel` to `terminal-notifier`,
which in turn requires a `UNUserNotificationCenter` bootstrap on the Tauri side to register
the bundle ID as a notification delegate. That wiring is tracked as a follow-up change.

## Phase 1 scope

Only `apps/desktop/` is implemented. See `docs/hld/phase-1-mvp-desktop-shell.md`.

## Recommended IDE setup

[VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
