# Squirrel

Local-first ADHD productivity companion. Monorepo.

## Installing (end users)

**Prerequisites:** Claude Code, Codex, Cursor, or Windsurf — plus a folder to use as your vault. Nothing else.

1. Download `squirrel-installer-macos.dmg`
2. Open it and double-click **Install Squirrel**
3. Answer two questions:
   - Which agent? (Claude Code / Codex / Cursor / Windsurf)
   - Where is your vault? (existing folder or press Enter to create `~/squirrel-vault`)
4. Allow the notification permission prompt
5. Open your agent and type `/sq-status`

The installer places two self-contained binaries on your machine and registers the backend as a launchd service that starts automatically at login:

| What | Where |
|------|-------|
| `squirrel` CLI | `~/.local/bin/squirrel` |
| `squirrel-backend` (API + web UI) | `~/.local/bin/squirrel-backend` |
| Agent skills & commands | `~/.claude/plugins/squirrel/` (or Codex/Cursor/Windsurf equivalent) |
| Config | `~/.squirrel/config.toml` |
| Background service | `~/Library/LaunchAgents/org.squirrel.web-ui.plist` |

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

| File | Purpose |
|------|---------|
| `scripts/build-dmg.sh` | Builds the DMG artifact (runs on dev machine) |
| `installer/install.sh` | End-user installer bundled inside the DMG |
| `apps/backend/launchd/plist.template` | launchd plist with `__BINARY__`, `__PORT__`, `__HOME__` placeholders |

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

| v0.5 source | New location | Notes |
|---|---|---|
| `lib/*.py` + `squirrel` + `tests/` | `apps/cli/` | Python core + CLI entry + 24 tests |
| `companions/web-ui/` | `apps/backend/` | Flask `server.py` + Vite `app/` frontend (node_modules stripped) |
| `companions/macos-reminders/` | `agent-pack/companions/macos-reminders/` | launchd daemon, will be folded into Tauri |
| `companions/menubar*/` (Swift) | not migrated | Superseded by `apps/desktop/` (Tauri) |
| `skills/` `commands/` `hooks/` `templates/` `examples/` `config/` `scripts/` `.claude-plugin/` | `agent-pack/` | Agent integrations |
| `companions/{codex,cursor}/` | `agent-pack/companions/` | Per-agent adapters |
| `install.sh` `Makefile` `INSTALL*.md` | `agent-pack/` | Installer belongs with the pack |
| `docs/` + `ARCHITECTURE.md` + old `README.md` + old `CLAUDE.md` | `docs/legacy/v0.5/` | Preserved unchanged |

## Develop

```bash
pnpm install
pnpm tauri dev          # runs the desktop app (filters to @squirrel/desktop)
pnpm tauri build        # produces an unsigned .app + .dmg
```

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
