# Desktop Vault Recovery — Low-Level Design

> _Backfilled from the as-built popup components and backend classifier._

## Architecture

The backend is the single source of truth for vault health: `/api/me` raises a
structured `409` with a machine-readable `code` when the configured vault is
unusable. The popup mounts a gate that probes `/api/me`, maps the error to a
recovery payload, and — only for vault-recovery codes — renders a blocking overlay
that drives the matching fix back through `/api/config/vault`.

```
[popup mount]
   └ VaultRecoveryGate            apps/desktop/src/components/VaultRecoveryGate.tsx
       └ probe(): api.me()
            ok            → render nothing (normal popup proceeds)
            error         → asVaultRecovery(e)
                              vault-recovery code → VaultRecoveryPayload
                              transport/401       → null (yield to other banners)
       └ VaultRecovery info       apps/desktop/src/components/VaultRecovery.tsx
            NO_VAULT / VAULT_MISSING → pick/enter folder → setVaultConfig(create:true)
            VAULT_EMPTY              → setVaultConfig(currentPath, create:true)  (scaffold)
            VAULT_UNSTRUCTURED       → create NEW vault + show /sq-migrate-vault cmd
       └ onRecovered(): re-probe → healthy ? window.location.reload() : setInfo(next)

[backend]  apps/backend/server.py
   classify_vault(path) -> "ok" | "missing" | "empty" | "unstructured"
   _vault_setup_error(vault, status) -> _UserError(409, msg, code, details)
   POST /api/config/vault -> api_config_vault (persist + scaffold)
```

## Backend contract

### `classify_vault(path)` (`server.py`)
- `"ok"` — a known structure marker directory exists.
- `"missing"` — path is not a directory.
- `"empty"` — directory exists but contains only hidden / `.DS_Store` entries.
- `"unstructured"` — has visible non-hidden content but no structure marker.

### `_vault_setup_error(vault, status)` → `_UserError(409, …)`
Carries `code` plus `details = {vault: {name, path}, vault_status}`:

| status | code | extra |
|--------|------|-------|
| missing | `VAULT_MISSING` | — |
| empty | `VAULT_EMPTY` | — |
| unstructured | `VAULT_UNSTRUCTURED` | `details.migrate_command = "/sq-migrate-vault <path>"` |

A vault that was never configured surfaces as `NO_VAULT` (also `409`) from the
no-context path. The popup's `asVaultRecovery(e)` recognizes exactly
`{NO_VAULT, VAULT_MISSING, VAULT_EMPTY, VAULT_UNSTRUCTURED}` and returns a typed
`VaultRecoveryPayload {code, error, vault?, migrate_command?}`; anything else
(transport, 401) yields `null`.

### `POST /api/config/vault` → `api_config_vault`
- Body `{name?, path, create?}`; `name` defaults to `personal`, validated against
  `_VAULT_NAME_RE`; `path` validated via `_validate_vault_path`.
- When `create` and the path doesn't exist → `mkdir(parents=True)`.
- Persists the default vault via `config_loader.upsert_default_vault`.
- Scaffolds the skeleton + mind journal **unless** the folder classifies as
  `unstructured` — so a raw Obsidian vault is left intact for `/sq-migrate-vault`
  to convert (scaffolding it would make it look already-Squirrel and block
  migration). Scaffolding is idempotent and non-fatal.

## Frontend behavior (`VaultRecovery.tsx`)

Three branches keyed by `info.code`:

- **Not found (`NO_VAULT` / `VAULT_MISSING`):** a path input prefilled with the
  current path + native "Choose…" folder picker; "Set up workspace" calls
  `setVaultConfig({path, create:true})` then `onRecovered()`.
- **Empty (`VAULT_EMPTY`):** single "Generate structure" button calling
  `setVaultConfig(currentPath, create:true)` (scaffold-in-place).
- **Unstructured (`VAULT_UNSTRUCTURED`):** two steps — (1) create a **new**
  destination vault (`newPath`, defaulted to `~/squirrel-vault`, required to differ
  from the source) via `setVaultConfig({path:newPath, create:true})`; (2) a
  copy-able `migrate_command` (from the payload, fallback `/sq-migrate-vault
  <currentPath>`) to run in the coding agent. "Open Squirrel" exits via
  `onRecovered()`.

Shared: native `@tauri-apps/plugin-dialog` `open({directory:true})` for folder
selection (no `window.prompt` — unavailable in the Tauri webview); inline error
text on failure; a footer "Set up in the web UI →" escape hatch via
`openWebUrl("")`.

### Gate lifecycle (`VaultRecoveryGate.tsx`)
- On mount, `probe()` once; store the payload (or `null`).
- `onRecovered()` re-probes: healthy → `window.location.reload()` so every widget
  re-initializes against the new vault; still-broken → update to the next recovery
  state (e.g. created-but-now-empty).

## Constraints

- The gate must **not** claim transport/auth errors — those belong to
  `BackendStatusBanner` / `HandshakeBanner`; `asVaultRecovery` returning `null` is
  the yield mechanism.
- All recovery actions complete in-app (popup), matching the desktop-in-app
  principle; the web UI is only an optional bigger-window escape hatch.
- Folder selection uses the native dialog; no text `prompt()`/`confirm()`.

## Key Decisions

- **Separate gate from onboarding** — onboarding gates on the first-run "done"
  flag; recovery gates on live `/api/me` health, so a returning user with a broken
  vault is handled even though onboarding already "completed".
- **Backend classifies, popup renders** — vault health logic lives once in
  `classify_vault`; the popup only maps codes to flows.
- **Don't scaffold unstructured folders** — preserves the raw vault so migration
  (copy-only) can convert it; scaffolding would corrupt the source==target /
  already-Squirrel guard.

## Out of Scope

- Migration itself (handed to `/sq-migrate-vault`).
- The web UI's own settings-page vault change flow (see
  `docs/lld/web-ui-settings-page.md`), which shares `POST /api/config/vault`.
