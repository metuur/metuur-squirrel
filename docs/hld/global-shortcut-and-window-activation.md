# Global Shortcut & Window Activation — High-Level Design

## Overview

Squirrel is a tray-bar-only app with no Dock icon and no Cmd+Tab entry while hidden. The only way to open its window today is clicking the tray icon. This change adds a system-wide keyboard shortcut (`Cmd+Shift+S` on macOS) that shows and focuses the window from anywhere, and introduces dynamic activation-policy management so the app behaves like Ollama: invisible in the Dock and Cmd+Tab while the window is hidden, but a normal foreground app while the window is open.

## Stakeholders & Impact

- **User (Javier):** Can summon Squirrel instantly from any app — fullscreen, terminal, browser — without touching the mouse. When the window is visible, it appears in Cmd+Tab like any other app. When dismissed (close button or hide), the app returns to tray-only mode and keeps running silently in the background.
- **No secondary consumers.** The shortcut is registered at the Rust level; the frontend is not involved.

## Goals

- Pressing `Cmd+Shift+S` from anywhere shows and focuses the Squirrel main window.
- While the window is visible, the app appears in Cmd+Tab (regular activation policy).
- Closing or hiding the window returns the app to background mode: no Dock icon, not in Cmd+Tab (accessory activation policy).
- The app never quits on window close — it continues polling the tray alerts in the background.

## Non-Goals

- No Dock icon at any time (even while the window is open, the Dock presence is an OS side-effect of `Regular` policy and is acceptable, but not a goal).
- No frontend JavaScript shortcut registration.
- No user-configurable shortcut (fixed key combination for now).
- No change to the tray menu or alert-polling behaviour.

## Success Criteria

1. From any foreground app, pressing `Cmd+Shift+S` brings the Squirrel window to the front.
2. While the window is open, the app icon appears in the Cmd+Tab switcher.
3. Pressing the red close button (or `Cmd+W`) hides the window without quitting; the app disappears from Cmd+Tab and the Dock.
4. The tray icon remains present and polling continues regardless of window state.
