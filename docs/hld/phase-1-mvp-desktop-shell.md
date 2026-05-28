# Phase 1 MVP — Desktop Shell — High-Level Design

## Overview

Squirrel is a local-first ADHD productivity companion that will ultimately bundle a Tauri desktop shell, a Flask sidecar, a CLI, an agent pack, Obsidian integration, and a background vault watcher. Phase 1 deliberately scopes down to **proving the desktop runtime architecture works** before any real domain functionality is built. The MVP is a single Tauri v2 + React + TypeScript application that runs as a macOS menu bar app, stays alive in the background, fires native notifications driven by a fake internal timer, and exposes a minimal dashboard.

The objective of Phase 1 is **not UI and not features** — it is to validate the parts of a desktop application that are hardest to retrofit later: lifecycle, background execution, tray behaviour, notification reliability, and local runtime orchestration.

## Stakeholders & Impact

| Stakeholder | Today's pain | After Phase 1 ships |
|---|---|---|
| Primary user (Javier, ADHD operator) | No unified desktop presence for Squirrel; vault activity is invisible unless actively working in CLI; nothing surfaces when context is lost | SQ icon is persistently visible in macOS menu bar; app survives window close; notifications can surface events even while user is in another app |
| Future Phase 2/3 engineering work (Flask sidecar, CLI, real watcher, agent skills) | Each would have to re-solve desktop lifecycle and notification plumbing | Plumbing exists; later phases plug into a stable host |
| Future Windows users | Not addressed in Phase 1 | Tauri cross-platform code will not block a future Windows MSI build, but Phase 1 only ships and tests macOS |

Secondary consumers (Flask sidecar, Obsidian plugin, CLI, hooks, agent skills, vault watcher) are **explicitly not stakeholders for Phase 1**. They are mentioned only to scope them out.

## Goals

When Phase 1 ships, the following are observable and true:

1. **A single signed/notarised `Squirrel.dmg` installs the app on macOS.**
2. **An "SQ" icon appears in the macOS menu bar and persists** for as long as the app process is running.
3. **The icon supports at least four visible states**: Normal, Notification (alert/dot), Processing (sync), Error/Disconnected (gray). The MVP must be able to switch between them on demand.
4. **Closing the main window does not quit the app.** The window hides; the menu bar icon remains; the background worker continues.
5. **Quit is explicit.** Only the tray menu's "Quit Squirrel" item (or OS-level termination) ends the process.
6. **Native macOS notifications fire reliably**, including requesting notification permission on first run.
7. **A fake background watcher emits one simulated event every 60 seconds.** Each event triggers a notification and updates the SQ icon state.
8. **Clicking a notification opens (or focuses) the dashboard window** and clears the alert state on the icon.
9. **The dashboard exposes**: current status, watcher on/off indicator, time since last event, and three buttons — Trigger Test Notification, Open Logs, Quit.
10. **The tray menu exposes**: Open Squirrel, Background Watcher On/Off, Settings (placeholder), View Logs, Quit Squirrel.
11. **Auto-start at login is supported as an opt-in setting**, but defaults to OFF.

## Non-Goals

The following are out of scope for Phase 1 and **must not be implemented**:

- Flask sidecar process or any Python runtime
- CLI binary (`squirrel` command)
- Vault detection, vault selection, or any Markdown/Obsidian interaction
- Persistent settings storage beyond what is required to remember the auto-start preference
- Agent skills, hooks, agent pack distribution
- Sync, indexing, or any real file-system watcher
- AI / LLM integration
- Windows `.msi` build as a release deliverable (cross-platform code is fine; shipping a tested Windows artefact is not a Phase 1 gate)
- Branding/design polish beyond a recognisable "SQ" mark and the icon state set
- Telemetry, analytics, crash reporting

## Success Criteria

Phase 1 is done when a fresh macOS machine can:

1. Install Squirrel from the `Squirrel.dmg`.
2. Launch the app; see the SQ icon in the menu bar; grant notification permission.
3. Close the window; observe the app is still running (icon still present, fake watcher still ticking).
4. Receive a native notification within 60 seconds; observe the SQ icon changes to the notification state.
5. Click the notification; observe the dashboard opens/focuses; the icon returns to Normal.
6. Click "Trigger Test Notification" on the dashboard; receive an immediate notification.
7. Click "Quit Squirrel" from the tray menu; observe the process actually exits and the icon disappears.

If all seven steps pass on a clean install, Phase 1 ships.
