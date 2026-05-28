# Squirrel

Local-first ADHD productivity companion. Monorepo.

## Layout

```
squirrel/
├── apps/
│   └── desktop/          # Tauri v2 + React + TypeScript (macOS menu-bar app)
│       ├── src/          # React UI
│       ├── src-tauri/    # Rust: tray, lifecycle, notifications, watcher
│       ├── scripts/      # gen-tray-icons.sh and friends
│       └── public/
├── docs/                 # LID + EARS docs (hld/ lld/ ears/ tasks/)
├── package.json          # pnpm workspace root
├── pnpm-workspace.yaml
└── Cargo.toml            # Cargo workspace root
```

Future siblings (created when each phase starts):

- `apps/backend/` — Flask sidecar (Python), built to a single binary and embedded by Tauri
- `apps/cli/` — `sq` command-line for the Markdown vault
- `apps/obsidian-plugin/` — Obsidian integration
- `crates/vault-watcher/`, `crates/vault-core/` — shared Rust libraries
- `packages/ui/`, `packages/ipc-contracts/`, `packages/vault-schema/` — shared TS
- `agent-pack/` — skills, hooks, configs distributed as a unit

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
