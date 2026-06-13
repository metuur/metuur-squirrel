# Web UI Settings Page — High-Level Design

> _Backfilled from the as-built `apps/backend/app/src/pages/SettingsPage.tsx`. Two
> of its sections are specified in their own features — notification sound
> (`docs/ears/notification-sound-selection.md`, R-3.x) and the notifications
> section shape (`docs/ears/in-app-notification-center.md`, Unit 9). This chain
> documents the page container and the Appearance/Vault/About sections._

## Overview

Squirrel's preferences were spread across `~/.squirrel/config.toml`, theme cookies,
and CLI commands, with no single place in the Web UI to see or change them. This
change adds a **Settings page** that gathers the user-facing preferences into
labeled sections: Appearance (theme), Obsidian Vault (active vault, path, switch,
change), Notifications (in-app/OS toggles + sound), and About (version).

The page is the Web UI's settings hub; each section reads from `/api/me` and writes
through the existing per-concern endpoints, with optimistic updates and toast-based
error recovery.

## Stakeholders & Impact

- **User:** changes theme, switches or relocates the vault, and tunes notifications
  from one screen, with immediate visual feedback.
- **Backend:** reuses existing endpoints (`/api/set-theme`, `/api/config/vault`,
  `/api/settings/notifications`, vault switch) — the page is a new consumer, not a
  new contract (except where the notification-sound feature extended them).
- **Other features:** notification sound and the notifications section are owned by
  their own specs; this page hosts them.

## Goals

- A single Settings hub with clearly delimited sections.
- Appearance theme switch (auto / light / dark) applied immediately.
- Vault section showing the active vault's name and path, switching between vaults
  (multi-vault), and changing/relocating the active vault's path.
- Optimistic updates that revert and toast on failure.
- An About section showing the running version.

## Non-Goals

- No new preference storage — the page reads `/api/me` and writes existing
  endpoints.
- No vault **content** migration from the page (the Change-vault flow only repoints
  config; bringing content over is `/sq-migrate-vault`).
- No re-specification of the notification toggles/sound (owned by their features).
- No account/auth settings (Squirrel is local-only).

## Success Criteria

1. The page renders Appearance, Obsidian Vault, Notifications, and About sections
   from `/api/me`.
2. Selecting a theme applies it immediately and persists it.
3. In multi-vault mode the user can switch the active vault (page reloads so every
   view reflects it); in single-vault mode the name/path are shown read-only with a
   "Change vault" action.
4. "Change vault" repoints config to a new path (optionally creating it), then
   reloads; nothing in the old folder is moved or deleted.
5. A failed notification-settings write reverts the control and shows an error
   toast.
