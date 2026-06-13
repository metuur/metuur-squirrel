# Web UI Settings Page — Low-Level Design

> _Backfilled from the as-built `SettingsPage.tsx`._

## Architecture

A single page composed of `SettingsSection` cards. State seeds from `useMe()`
(`/api/me`); each section writes through an existing per-concern endpoint and calls
`mutate()` to refresh `me`. Notification controls use optimistic local state with
revert-on-failure.

```
SettingsPage.tsx
  useMe() → me ; useToast()
  Appearance      → api.setTheme(auto|light|dark) + applyThemeClass + mutate
  Obsidian Vault  → switch: api.setVault(name) + reload
                    change: api.setVaultConfig({name, path, create}) + reload
  Notifications   → ToggleRow in_app/os_popups  → api.setNotificationSettings
                    SoundRow Glass|Funk|Silent   → api.setNotificationSettings
                    preview                       → api.previewNotificationSound
  About           → me.version
```

## Sections

### Appearance
- Segmented control `auto | light | dark`. `setTheme` calls `api.setTheme`,
  applies the class locally (`applyThemeClass`: `auto` follows
  `prefers-color-scheme`), then `mutate()`. Current selection from `me.theme`.

### Obsidian Vault (only when `me.active_workspace`)
- **Multi-vault** (`me.multi_vault`): a `<select>` of `me.workspaces`; `setWorkspace`
  calls `api.setVault(name)`, `mutate()`, then `window.location.reload()` so every
  view re-reads the new vault.
- **Single-vault**: name shown read-only; path shown in a monospace box.
- **Change vault**: a disclosure with a path input, a "Create the folder (with the
  Squirrel structure) if it doesn't exist" checkbox, and Change/Cancel. `handleChangeVault`
  calls `api.setVaultConfig({ name: active.name, path, create })` then reloads.
  The Change button is disabled while busy, when the path is empty, or when the
  path equals the current path. Errors render inline. Copy explicitly notes nothing
  in the current folder is moved/deleted and points to `/sq-migrate-vault` for
  bringing content along.

### Notifications
- `ToggleRow` for `in_app` and `os_popups`; `os_popups` is disabled unless `in_app`
  is on. `handleNotifToggle` optimistically updates `localNotif`, calls
  `api.setNotificationSettings(next)` + `mutate()`, and on failure reverts +
  toasts "Failed to save notification settings".
- Sound: three `SoundRow`s (`Glass | Funk | Silent`), the selected one marked;
  `handleSoundChange` mirrors the toggle's optimistic/revert pattern. A per-row
  preview button calls `api.previewNotificationSound(sound)` (disabled for
  `Silent`). _(Sound contract is owned by `notification-sound-selection`.)_
- `localNotif` seeds from `me.notifications` via an effect keyed on its fields.

### About
- Renders `Squirrel <me.version ?? '?'>` and a note that the CLI keeps working.

## Shared components
- `SettingsSection({icon, title, subtitle, children})` — card with header.
- `ToggleRow` — accessible `role="switch"` button with `aria-checked`.
- `SoundRow` — select + preview affordance.

## Constraints
- The page is a consumer of existing endpoints; it introduces no new persistence.
- Vault switch and change both `window.location.reload()` because vault identity is
  read at init across every widget.
- Optimistic writes must revert to the prior value and toast on failure (no silent
  loss).

## Key Decisions
- **Reload on vault change/switch** — simplest correct way to re-init every view
  against a different vault, rather than threading a vault-changed event everywhere.
- **Optimistic + revert for notifications** — instant feedback on a cheap local
  write, with a guaranteed rollback path on error.
- **Change-vault repoints config only** — content migration is a separate,
  explicit, copy-only operation (`/sq-migrate-vault`); Settings never moves files.

## Out of Scope
- Notification toggle/sound semantics (own features).
- Vault content migration.
- Any account/auth settings.
