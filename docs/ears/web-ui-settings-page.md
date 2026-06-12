# Web UI Settings Page — EARS Specifications

> _Backfilled from the as-built `SettingsPage.tsx`. The Notifications section's
> toggle and sound semantics are specified in `in-app-notification-center.md`
> (Unit 9) and `notification-sound-selection.md` (Unit 3); the requirements below
> cover the page container and the Appearance / Vault / About sections, plus the
> page's optimistic-write behavior._

## Unit 1: Page composition

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL render a Settings page composed of an Appearance section, an Obsidian Vault section (when a workspace is active), a Notifications section, and an About section. |
| R-1.2 | THE SYSTEM SHALL seed every section's state from `GET /api/me`. |

## Unit 2: Appearance

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL present a theme control with `auto`, `light`, and `dark`, indicating the current selection from `me.theme`. |
| R-2.2 | WHEN the user selects a theme, THE SYSTEM SHALL persist it via the theme endpoint and apply it immediately; `auto` SHALL follow the OS `prefers-color-scheme`. |

## Unit 3: Obsidian Vault

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN multiple vaults are configured, THE SYSTEM SHALL let the user switch the active vault and SHALL reload the page so every view reflects the new vault. |
| R-3.2 | WHEN a single vault is configured, THE SYSTEM SHALL show its name and path read-only. |
| R-3.3 | THE SYSTEM SHALL provide a "Change vault" action that repoints the active vault to a new path via `POST /api/config/vault`, optionally creating the folder with the Squirrel structure, then reloads. |
| R-3.4 | THE SYSTEM SHALL disable the Change action while busy, when the path is empty, or when the path equals the current path. |
| R-3.5 | THE SYSTEM SHALL NOT move or delete anything in the previous vault folder on change, and SHALL direct the user to `/sq-migrate-vault` to bring content along. |
| R-3.6 | WHEN a change fails, THE SYSTEM SHALL show the error inline without leaving the section. |

## Unit 4: Notifications (page-level)

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL render in-app and OS notification toggles and the notification-sound control, seeded from `me.notifications`. |
| R-4.2 | THE SYSTEM SHALL disable the OS-notifications toggle while in-app notifications are off. |
| R-4.3 | WHEN the user changes a notification toggle or sound, THE SYSTEM SHALL apply the change optimistically and persist it via `POST /api/settings/notifications`. |
| R-4.4 | WHEN a notification-settings write fails, THE SYSTEM SHALL revert the control to its prior value and show an error toast. |
| R-4.5 | WHEN the user previews a sound, THE SYSTEM SHALL play it without changing the persisted selection, and SHALL disable preview for `Silent`. |

## Unit 5: About

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL display the running Squirrel version from `me.version`, falling back to `?` when unknown. |
