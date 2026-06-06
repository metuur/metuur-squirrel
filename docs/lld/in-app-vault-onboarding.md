# In-App Vault Onboarding — Low-Level Design

## Architecture

Four moving parts: a first-run gate + wizard in the React layer, a native folder picker via a new Tauri plugin, two new backend endpoints (Obsidian detection + vault write) reusing existing config logic, and a small change to un-hardcode the vault name.

```
┌─────────────────────────── Tauri desktop app ───────────────────────────┐
│ App.tsx                                                                   │
│   ├─ reads onboarding flag from tauri-plugin-store ("onboarding.done")    │
│   └─ if not done → render <OnboardingWizard/> as blocking overlay         │
│                     (reuse HandshakeBanner full-screen overlay pattern)   │
│                                                                           │
│ OnboardingWizard.tsx  (new)                                               │
│   Step 1 Welcome                                                          │
│   Step 2 Obsidian ──► GET  /api/env/obsidian        (backend)            │
│   Step 3 Vault     ──► open({directory:true})       (tauri-plugin-dialog)│
│                    ──► POST /api/config/vault        (backend)            │
│   Step 4 Done      ──► store.set("onboarding.done", true)                 │
│                                                                           │
│ OpenVaultButton.tsx / tray.rs  ──► vault name from configured vault       │
└──────────────────────────────────┬────────────────────────────────────────┘
                                    │ HTTP 127.0.0.1:3939
┌───────────────────────────────────▼──────────────────────────────────────┐
│ apps/backend/server.py                                                     │
│   GET  /api/env/obsidian  → { installed: bool, path: str|null }            │
│   POST /api/config/vault  → { name, path, create } → writes config.toml    │
│       └─ delegates to apps/cli/lib/config_loader.py (existing write logic) │
└────────────────────────────────────────────────────────────────────────────┘
                                    │
                          ~/.squirrel/config.toml  ([[vaults]] … default=true)
```

### Component responsibilities

**First-run gate (`apps/desktop/src/App.tsx`)**
- On mount, read key `onboarding.done` from `tauri-plugin-store` (already a dependency, `lib.rs:89`).
- If the key is absent/false, render `<OnboardingWizard/>` as a full-screen overlay that blocks the normal widgets — same structural pattern as `HandshakeBanner` (`App.tsx:170`). The wizard is independent of the backend-trust banner; if both apply, the handshake banner still takes precedence (a broken backend can't accept config writes).

**`OnboardingWizard.tsx` (new component)**
- Stepper state machine: `welcome → obsidian → vault → done`.
- Step 2 calls `api.getObsidianStatus()`; renders "found / not found". Not-found state shows a link to `https://obsidian.md/download` (opened via existing `tauri-plugin-opener` `openUrl`, which already allows `https://*`) plus "Re-check" (re-calls the endpoint) and "Skip for now".
- Step 3 offers two modes:
  - *Use existing folder* → invokes `tauri-plugin-dialog` `open({ directory: true })`; on selection, the absolute path is shown.
  - *Create new* → a default path `~/squirrel-vault` (editable text); `create: true` is sent so the backend makes the folder.
  - "Install" calls `api.setVaultConfig({ name, path, create })`.
- Step 4 marks `onboarding.done = true` and dismisses the overlay.

**Backend — Obsidian detection (`apps/backend/server.py`)**
- New route `GET /api/env/obsidian` returning `{ installed, path }`.
- Detection order (macOS): check `/Applications/Obsidian.app` exists; fallback `mdfind "kMDItemCFBundleIdentifier == 'md.obsidian'"` for non-default install locations. Returns the first hit path, else `installed:false, path:null`.

**Backend — vault write (`apps/backend/server.py` + `apps/cli/lib/config_loader.py`)**
- New route `POST /api/config/vault`, body `{ name?: string, path: string, create?: bool }`.
- **Handler order (explicit):** validate `name` charset → expand `~`/resolve symlinks and validate `path` is absolute + within `$HOME` (reject otherwise, 400) → if `create` and folder absent, `mkdir -p` → assert is-dir (else 400) → persist.
- **Persist = upsert + set-default, NOT a single existing call.** The current CLI-only helpers do not do what R-3.6/R-3.10 require in one step:
  - `add_vault` (`config_loader.py:576-652`) appends with `default = false` when a config already exists (`:622`) **and requires the path to already exist** (`:595-598`), **and raises on duplicate name** (`:614-615`).
  - `set_default` (`:785-821`) only flips existing vaults and raises `VaultNotFoundError` otherwise.
  - Therefore the handler must do: **(a)** if the name exists → update its `path` + mark default (idempotent upsert, R-3.11); **(b)** else `add_vault(name, path)` then `set_default(name)`. Because that is two `_atomic_write`s, a small **new `config_loader.upsert_default_vault(name, path)` helper** is in scope to make the add+default change atomic (R-3.10) — this is new work, not "reuse".
- **TOML-injection fix (in scope):** `_format_vault_entry` (`config_loader.py:562-570`) interpolates `name`/`path` via raw f-string with no escaping; a `name`/`path` containing `"` or newline corrupts the file. R-3.13 (name charset) + R-3.12 (path sandbox) gate this at the endpoint; additionally the helper SHALL emit TOML-safe quoted strings.
- `name` defaults to `"personal"` when omitted (matches the seed in `squirrel.toml.example`); with R-3.11 the common case (installer already seeded `personal`) becomes an idempotent path-update rather than a duplicate-name crash.

**Error contract for `POST /api/config/vault`**

| Status | Cause |
|---|---|
| 200 | vault persisted; returns `{ name, path (expanded), default: true }` |
| 400 | bad/unsafe `path` (R-3.12), bad `name` (R-3.13), or path not a directory after create (R-3.5) |
| 401 | request failed the backend token gate (`_dispatch:467-469`) |
| 500 | filesystem/config write failure (config left unchanged, R-3.10) |

**Un-hardcode vault name**
- `OpenVaultButton.tsx:3` (`obsidian://open?vault=vault-tdah`) and `tray.rs` (`OBSIDIAN_VAULT = "vault-tdah"`) are replaced with the configured vault name.
- **`OpenVaultButton` (React)** reads the active vault name from the existing `/api/me` workspace payload. **Ordering caveat:** `api_me` → `_context()` → `resolve_vault()` returns **503 "No workspace is set up yet"** when no vault resolves (`server.py:553-561`) — exactly the state *during* onboarding on a fresh machine. So it tolerates a 503/empty response and disables Open Vault (R-4.3/R-4.4) rather than crash.
- **Tray (Rust)** does NOT use `/api/me` — the tray menu is built at app start, before the backend is guaranteed up, so a network read would block/fail. Instead `tray.rs` reads `~/.squirrel/config.toml` directly via a small dependency-free parser (`parse_default_vault_name`) and `dirs::home_dir()`. Returns `Option<String>`; the "Open Obsidian Vault" item is **disabled when `None`** (R-4.4) and the click handler no-ops when `None` (R-4.3). The menu is rebuilt by the tray-alerts poller, so the item enables after onboarding writes config. (Decision: a direct file read avoids both a `toml` crate and an ordering dependency on the backend.)
- **Resolved (was flagged in Constraints):** the `tauri-plugin-dialog` v2 open permission identifier is **`dialog:allow-open`** (confirmed against plugin v2.7.1; granted in `capabilities/default.json`).

### Security considerations
- **Threat model:** the backend is localhost-only and token-gated (`server.py:13` C5; `_dispatch:467-469`). The new `POST /api/config/vault` is the app's first network-reachable, client-path-driven `mkdir`+file-write, so the threat is a malicious localhost process / page that obtained the token.
- **Path sandbox (R-3.12):** reject non-absolute paths, paths that escape `$HOME` after `~`/symlink expansion, before any `mkdir`.
- **Name charset (R-3.13):** restrict to `[A-Za-z0-9._-]+` before any write; prevents TOML corruption via `_format_vault_entry` and `obsidian://` URL injection (R-4.1).
- **Atomic, non-clobbering write (R-3.8/R-3.10):** preserve all other config keys; leave config unchanged on failure.
- `GET /api/env/obsidian` is read-only (stat + `mdfind`); bound `mdfind` with a timeout (R-2.8).

### Data shapes

```
GET  /api/env/obsidian   → 200 { "installed": true,  "path": "/Applications/Obsidian.app" }
                           → 200 { "installed": false, "path": null }

POST /api/config/vault   body { "name": "personal", "path": "~/squirrel-vault", "create": true }
                           → 200 { "name": "personal", "path": "/Users/.../squirrel-vault", "default": true }
                           → 400 { "error": "path is not a directory" }
```

## Constraints
- **macOS only** — Obsidian detection uses `/Applications` + `mdfind`; bundle id `md.obsidian`.
- **Tauri v2** — adding `tauri-plugin-dialog` requires both the Cargo dep and a capability entry in `apps/desktop/src-tauri/capabilities/default.json`; without the capability the call is silently denied at the IPC boundary (same failure mode as the `tauri-opener-custom-url-scheme` learn). **Confirm the exact permission identifier** (e.g. `dialog:allow-open`) against the installed `tauri-plugin-dialog` v2 before wiring — a wrong identifier reproduces the silent-denial bug.
- **`config.toml` is the source of truth** for the vault; the wizard must persist there, not just in a cookie. (`POST /api/vault` only sets a cookie and 404s on unknown names — it is **not** reused for persistence.)
- **No overwrite of a populated config beyond the vault entry** — only the default vault is written; other config keys (`default_email`, `machine_environment`, other vaults) are preserved.
- Backend must be reachable (adopted or managed) for steps 2–3 to function; the wizard surfaces an error if the write endpoint fails and keeps the user on the vault step.

## Key Decisions
- **First-run signal = `tauri-plugin-store` key `onboarding.done`**, not "is a vault present in config.toml". Rationale: `install.sh` already seeds a default vault, so config presence can't distinguish "installer default" from "user confirmed". The store flag is decoupled from the installer and uses a plugin already in the app. *Open for confirmation at the gate.*
- **Obsidian detection + vault write live in the Python backend**, not Rust/Tauri commands. Rationale: the backend already owns `config_loader.py` (the only existing vault-write logic) and the desktop already talks to it over HTTP for everything else; keeping config there avoids duplicating write logic in Rust. The folder *picker* must stay in Tauri (native dialog) — that's the only piece that can't be backend.
- **Reuse `tauri-plugin-opener` for the Obsidian download link and the `obsidian://` open** — already present and capability-scoped; no new opener work.
- **Wizard is config-only.** The mock's "installing binaries" step is dropped; binaries/launchd/agent-pack remain installer-owned per scope decision.
- **`name` defaults to `personal`** to match the existing seed; a multi-vault naming UI is out of scope. Because the installer already seeds `personal`, onboarding's persist is an **idempotent upsert** (R-3.11), not a fresh add — it updates the seeded vault's path rather than reconciling/migrating it.
- **Default new-vault path is `~/squirrel-vault`** (R-3.2). Note this differs from the example seed `~/vault-squirrel` and the historically hardcoded Obsidian name `vault-tdah`; the wizard's choice supersedes these once onboarding completes.
- **Obsidian detected `path` is informational** — shown in the wizard but not consumed by the open action (config-only scope); the `obsidian://` open keys off the vault *name*, not the detected `.app` path.

## Out of Scope
- Moving binary/launchd/agent-pack installation into the app (stays in `install.sh`).
- Agent selection in the wizard.
- Multi-vault add/remove/switch management UI.
- Windows/Linux detection paths.
- Editing the wizard's choices later from a Settings screen (no settings screen exists yet; deferred).
- Rewriting `install.sh` as a GUI or removing it.
