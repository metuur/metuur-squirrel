# In-App Vault Onboarding — High-Level Design

## Overview
Today the only way to point Squirrel at a vault is the terminal installer (`installer/install.sh`), which prompts for a vault path and `sed`-writes it into `~/.squirrel/config.toml`. There is no in-app way to set the vault, no check for whether Obsidian is installed, and the desktop app's "Open Vault" button targets a hardcoded vault name (`vault-tdah`).

This change adds a **first-run onboarding wizard inside the existing Tauri desktop app** that:
1. checks whether Obsidian is installed (and offers a download link if not),
2. lets the user pick or create a vault folder via a native OS folder picker, and
3. persists that choice to `~/.squirrel/config.toml`.

Scope is **config only**. Installing binaries, the launchd service, and the agent-pack remain the job of the installer/DMG. This wizard owns Obsidian detection, vault selection, and the config write — nothing else.

## Stakeholders & Impact
- **New macOS desktop users** — today they must answer a Terminal prompt for the vault path during install. After this ships, they complete vault setup in the GUI with a real folder picker and clear Obsidian guidance.
- **Users without Obsidian** — today the "Open Vault" button silently no-ops. After this ships, onboarding tells them Obsidian is missing and links to `https://obsidian.md/download`.
- **The desktop app itself** — the "Open Vault" button and tray menu currently hardcode `vault-tdah`; after this ships they use the vault the user actually configured.
- **The installer (`install.sh`)** — unchanged in responsibility (still installs binaries/launchd/agent-pack); the in-app wizard becomes the surface that confirms/sets the vault.

## Goals
- On first run, when no vault has been confirmed in-app, the app presents a blocking onboarding overlay before the normal UI.
- The app detects whether Obsidian is installed and shows the result; when absent, it shows a download link and a re-check action, and still lets the user continue.
- The user can choose an existing folder (native picker) or create a new default-named vault folder.
- The chosen vault is written to `~/.squirrel/config.toml` as the default vault and survives restarts.
- After onboarding completes, the "Open Vault" action targets the configured vault, not a hardcoded name.
- Onboarding does not repeat on subsequent launches once completed.

## Non-Goals
- No change to what the installer installs (binaries, launchd plist, agent-pack stay in `install.sh`/DMG).
- No agent (Claude/Codex/Cursor/Windsurf) selection in the wizard — that stays in the installer.
- No multi-vault management UI (add/remove/switch among many vaults) — only setting the single default vault.
- No Windows/Linux support — macOS only, consistent with the rest of the app.
- No app auto-updater work.
- The terminal `install.sh` is not removed or rewritten as a GUI.
- No migration/reconciliation of a pre-existing installer-seeded vault — onboarding performs an idempotent upsert of the user's chosen vault (overwriting the seeded default's path), not a merge of prior state.

## Security Considerations
- `POST /api/config/vault` is the app's first network-reachable, client-path-driven directory creation + config write. The backend is localhost-only and token-gated, but the wizard input is still treated as untrusted: the chosen `path` is sandboxed to `$HOME` (no traversal/escape) and the vault `name` is charset-restricted before any write, to prevent `config.toml` corruption and `obsidian://` URL injection.
- `GET /api/env/obsidian` is read-only (filesystem stat + bounded `mdfind`).
- Config writes are atomic and non-clobbering: on any failure `config.toml` is left unchanged; exactly one vault remains `default = true`.

## Rollback
- Fully additive and reversible: the new endpoints are additive, the first-run gate is a single deletable `tauri-plugin-store` key (`onboarding.done`), and config writes are atomic single-vault changes. To force re-onboarding, delete the `onboarding.done` store key. Reverting the code removes the wizard without affecting an already-written `config.toml`.

## Success Criteria
- A fresh user launching the app with no configured vault sees the onboarding overlay, completes it, and lands in the normal app with a working vault.
- With Obsidian absent, the wizard shows the "not found" state with a working download link and lets the user finish anyway.
- After completion, `~/.squirrel/config.toml` contains the chosen vault as `default = true`, and relaunching the app goes straight to the normal UI (no wizard).
- Clicking "Open Vault" after onboarding opens the configured vault in Obsidian (when installed).
