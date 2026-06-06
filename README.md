# Squirrel

Local-first focus & productivity companion. Monorepo.

## Installing (end users)

Squirrel ships in two flavors. Pick whichever fits your audience:

| Flavor                         | What you get                                                                                                    | Who it's for                                                               |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Squirrel.app** (Tauri DMG)   | Just the desktop popup with a bundled backend that the app supervises itself. No terminal needed after install. | End users who want the tray popup.                                         |
| **Full installer DMG** (below) | `squirrel` CLI + backend + `agent-pack/` (Claude/Codex skills) + launchd service.                               | Power users who want CLI access and agent integration alongside the popup. |

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

```bash
launchctl unload ~/Library/LaunchAgents/org.squirrel.web-ui.plist
rm ~/Library/LaunchAgents/org.squirrel.web-ui.plist
rm ~/.local/bin/squirrel ~/.local/bin/squirrel-backend
rm -rf ~/.claude/plugins/squirrel   # or your agent's equivalent
# optionally: rm -rf ~/.squirrel
```

### Background service

`squirrel-backend` serves the JSON API and the React web UI on `http://127.0.0.1:3939` (localhost only). launchd keeps it running — it restarts on crash and starts at login. Logs are at `~/.squirrel/web-ui.stdout.log` and `~/.squirrel/web-ui.stderr.log`.

---

## Building the installer (contributors)

Requires `pyinstaller` on the dev machine (not shipped to users):

```bash
pip install pyinstaller
make build-installers       # → squirrel-installer-macos.dmg
make build-installers-dry   # preview steps without executing
```

What `make build-installers` does:

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
| `apps/backend/launchd/plist.template` | launchd plist with `__BINARY__`, `__PORT__`, `__HOME__` placeholders |

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

In the scrashpad project add a mandatory task which can be deleted , to asct as journally for your mind, and add a reminder to check it every 4 hours, to add a note like "WHat is you minf thinking right now?" and "What are you doing right now?" for happy and sad moments, to track your mood and activities.
