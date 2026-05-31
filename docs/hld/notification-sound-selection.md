# Notification Sound Selection — High-Level Design

## Overview

Squirrel currently signals notifications via two surfaces: the Tauri Rust process flips the tray icon state and emits `squirrel:notif-updated` (silent, no audio), and the launchd reminders daemon shows a macOS Notification Center banner with a **hardcoded `Submarine`** sound. The hardcoded daemon sound cannot be silenced or changed, and the tray surface has no audio at all. This change adds a single configurable notification sound — default `Glass`, alternatives `Funk` and `Silent` — that is honoured by both surfaces, with the selection living in the existing `[notifications]` section of `~/.squirrel/config.toml`.

## Stakeholders & Impact

- **User (Javier):** Gets a gentle, consistent audio cue across both notification surfaces. Can switch the sound to `Funk` or fully mute via `Silent` without touching macOS system volume, and the previously hardcoded daemon `Submarine` is replaced with the same configurable value.
- **No secondary consumers.** Local feature; no external API, no network egress; existing `in_app` and `os_popups` settings are unaffected.

## Goals

- A gentle audio cue (`Glass` by default) plays when either notification surface triggers.
- The user can switch to `Funk` or fully mute via `Silent` from the **existing Notifications section** of the settings page.
- The choice persists in `~/.squirrel/config.toml` and is honoured by both the Tauri process and the launchd reminders daemon.
- `Silent` fully suppresses audio on both surfaces with no other side-effect.
- Existing `in_app` and `os_popups` behaviour remains functionally unchanged.
- API clients that still post the legacy `{in_app, os_popups}` payload continue to succeed without overwriting an existing sound value.

## Non-Goals

- No custom sound file upload or arbitrary file picker.
- No per-surface sound (one sound serves both tray emit and reminders daemon).
- No volume control inside the app — users adjust macOS system volume.
- No cross-platform parity in v1 (macOS-only; `afplay`, `terminal-notifier`, and `osascript` are macOS APIs).
- No notification debouncing or rate-limiting (handled upstream).

## Success Criteria

1. On first launch with no `sound` key in config, the next tray notification plays `Glass`, and the next daemon-fired reminder also plays `Glass` (replacing the previous hardcoded `Submarine`).
2. Selecting `Funk` in settings → the next notification from either surface plays `Funk`.
3. Selecting `Silent` → no audio on either surface; visual cues remain unchanged.
4. Existing API clients posting `{in_app, os_popups}` without `sound` continue to succeed, and the previously persisted `sound` value is preserved.
5. The setting hot-applies: after a change, the next tray notification uses the new sound without an app restart, and the next daemon run uses it without a `launchctl unload/load`.
