# Squirrel

Local-first ADHD productivity companion. Monorepo.

## Layout

```
squirrel/
├── apps/
│   ├── desktop/          # Tauri v2 + React + TypeScript (macOS menu-bar app) — Phase 1
│   ├── cli/              # Python `squirrel` CLI + lib/ (migrated from v0.5)
│   └── backend/          # Flask sidecar + companion web UI (migrated from v0.5)
├── agent-pack/           # Skills, commands, hooks, templates, installer (migrated from v0.5)
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

## Phase 1 scope

Only `apps/desktop/` is implemented. See `docs/hld/phase-1-mvp-desktop-shell.md`.

## Recommended IDE setup

[VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
