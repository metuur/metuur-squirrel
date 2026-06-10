# In-App Vault Onboarding — EARS Specifications

## Unit 1: First-run gate

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN the desktop app mounts and the `tauri-plugin-store` key `onboarding.done` is absent or false, THE SYSTEM SHALL render the onboarding wizard as a full-screen overlay that blocks the normal app widgets. |
| R-1.2 | WHEN the `tauri-plugin-store` key `onboarding.done` is true, THE SYSTEM SHALL render the normal app UI without the onboarding wizard. |
| R-1.3 | IF the backend-trust handshake banner is active, THE SYSTEM SHALL display the handshake banner in preference to the onboarding wizard. |
| R-1.4 | WHEN the user completes the final wizard step, THE SYSTEM SHALL set `onboarding.done` to true and remove the overlay without requiring an app restart. |
| R-1.5 | THE SYSTEM SHALL NOT modify, remove, or re-run the terminal installer (`install.sh`) responsibilities (binaries, launchd, agent-pack) as part of onboarding. |
| R-1.6 | IF the `onboarding.done` flag cannot be read (store missing or corrupt), THE SYSTEM SHALL treat onboarding as not done and show the wizard, rather than skipping setup. |

## Unit 2: Obsidian detection

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the wizard reaches the Obsidian step, THE SYSTEM SHALL request Obsidian status from `GET /api/env/obsidian`. |
| R-2.2 | WHERE the host is macOS, THE SYSTEM SHALL report Obsidian as installed if `/Applications/Obsidian.app` exists, otherwise if `mdfind "kMDItemCFBundleIdentifier == 'md.obsidian'"` locates a bundle within a bounded timeout. |
| R-2.8 | IF the `mdfind` probe exceeds its timeout or Spotlight is unavailable, THE SYSTEM SHALL report `installed: false` and allow the user to proceed (consistent with R-2.7). |
| R-2.3 | WHEN Obsidian is detected, THE SYSTEM SHALL return `{ installed: true, path: <app path> }` and the wizard SHALL show a confirmation with the resolved path. |
| R-2.4 | IF Obsidian is not detected, THE SYSTEM SHALL return `{ installed: false, path: null }` and the wizard SHALL show a download link to `https://obsidian.md/download`, a "Re-check" action, and a means to continue. |
| R-2.5 | WHEN the user activates "Re-check", THE SYSTEM SHALL re-request `GET /api/env/obsidian` and update the displayed state. |
| R-2.6 | WHEN the user activates the download link, THE SYSTEM SHALL open `https://obsidian.md/download` via the existing opener plugin. |
| R-2.7 | IF Obsidian is not installed, THE SYSTEM SHALL still allow the user to proceed to the vault step. |

## Unit 3: Vault selection and persistence

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN the user chooses "Use an existing folder", THE SYSTEM SHALL open a native folder picker via `tauri-plugin-dialog` (`open({ directory: true })`) and display the selected absolute path. |
| R-3.2 | WHEN the user chooses "Create a new vault", THE SYSTEM SHALL present an editable default path of `~/squirrel-vault`. |
| R-3.3 | WHEN the user confirms the vault, THE SYSTEM SHALL call `POST /api/config/vault` with `{ name, path, create }`. |
| R-3.4 | WHERE `create` is true and the target folder does not exist, THE SYSTEM SHALL create the folder (after path validation per R-3.12) before writing config. |
| R-3.5 | IF the resolved path is not an existing directory after any creation, THE SYSTEM SHALL respond 400 with an error and the wizard SHALL keep the user on the vault step with the error shown. |
| R-3.6 | WHEN `POST /api/config/vault` succeeds, THE SYSTEM SHALL write the vault into `~/.squirrel/config.toml` as an entry with `default = true`, expanding `~` to the user home. |
| R-3.7 | WHERE `name` is omitted, THE SYSTEM SHALL default the vault name to `personal`. |
| R-3.8 | GIVEN a `config.toml` containing `default_email`, `machine_environment`, and N existing vault entries, WHEN a new vault is persisted, THE SYSTEM SHALL leave all of those keys and entries intact except for the added/updated entry and the single relocated `default = true` flag. |
| R-3.9 | IF the backend is unreachable when confirming the vault, THE SYSTEM SHALL surface a failure message and keep the user on the vault step. |
| R-3.10 | WHEN persisting the chosen vault, THE SYSTEM SHALL append the vault entry and mark it the sole `default = true` vault such that the resulting `config.toml` has exactly one default; IF persistence cannot complete, THE SYSTEM SHALL leave `config.toml` unchanged. |
| R-3.11 | IF a vault with the target name already exists in `config.toml`, THE SYSTEM SHALL update that vault's path to the chosen path and mark it default (idempotent upsert), rather than failing on a duplicate-name error. |
| R-3.12 | THE SYSTEM SHALL reject a vault `path` that, after `~`/symlink expansion, is not absolute or escapes the user home directory, responding 400 without creating any directory. |
| R-3.13 | THE SYSTEM SHALL reject a vault `name` that does not match `[A-Za-z0-9._-]+`, responding 400 before any config write, since `name` is interpolated into `config.toml`. |

## Unit 4: Vault wiring (un-hardcode)

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the "Open Vault" action is invoked after onboarding, THE SYSTEM SHALL open `obsidian://open?path=<configured vault path>` using the active vault path from `/api/me`, not a hardcoded value. Path (not vault name) is used because Obsidian registers vaults under their folder name, which may differ from squirrel's configured vault name. |
| R-4.2 | WHEN the tray menu is built, THE SYSTEM SHALL use the configured vault's path rather than a hardcoded value. |
| R-4.3 | IF no vault is available from configuration, THE SYSTEM SHALL omit or disable the "Open Vault" action rather than open a non-existent vault. |
| R-4.4 | IF `/api/me` is unavailable or returns no active vault (e.g. 503 before onboarding completes), THE SYSTEM SHALL treat the Open Vault action as disabled (R-4.3) and SHALL NOT block tray construction or app mount. |
