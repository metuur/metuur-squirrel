# Notification Icon Branding (Squirrel logo on every banner) — High-Level Design

## Overview

Today a Squirrel notification can appear with the generic **Terminal `>_` icon** instead of the Squirrel logo. This is the deferred `R-1.10` branding work from `native-notification-banner`. The root cause is a single macOS rule: macOS only honors a bundle identifier for notification branding **after that bundle has emitted at least one notification through the modern `UNUserNotificationCenter` API**. Until `com.metuur.squirrel` has done so, both the Tauri-posted banners and the daemon's `terminal-notifier` banners fall back to a generic icon.

This change makes the Squirrel logo appear on every banner type it *can* appear on, by (a) establishing the app's notification identity on first launch, (b) restoring `-sender com.metuur.squirrel` on the daemon's `terminal-notifier` invocations so they post as Squirrel, and (c) documenting the one-time macOS permission grant. It supersedes the `R-1.10` deferral and flips `native-notification-banner` `R-1.6` to require `-sender`.

## Stakeholders & Impact

- **Primary user (ADHD knowledge worker):** every Squirrel banner — the daily focus plan, journal/break nudges, and deadline reminders from the daemon — shows the Squirrel logo, so notifications are instantly recognizable instead of looking like a stray terminal popup. Clicking a daemon reminder activates Squirrel (a side benefit of `-sender`).
- **`reminder-daemon.sh` (macOS reminders companion):** its `terminal-notifier` banners gain `-sender com.metuur.squirrel`; behavior is otherwise unchanged (group, title, subtitle, message, open-url, sound).
- **Tauri desktop app:** gains a one-shot, first-launch notification-identity bootstrap; its existing organic notifications are otherwise untouched.
- **No backend / SQLite / web-UI impact.**

## Goals

- After first launch and the one-time permission grant, **Tauri-posted banners show the Squirrel logo** (the app-bundle icon), not the Terminal icon.
- **`terminal-notifier` deadline reminders show the Squirrel logo** by posting as `com.metuur.squirrel`.
- The app **establishes its `UNUserNotificationCenter` identity exactly once**, early, via a persisted first-launch flag — so the daemon's `-sender` is honored even before the first organic notification.
- The `R-1.10` deferral is removed; `R-1.6` requires `-sender`; the System Settings permission step is documented.

## Non-Goals

- No attempt to brand the **`osascript` fallback** banner — macOS gives `osascript display notification` no icon control (always Script Editor). The daemon already prefers `terminal-notifier`; `osascript` stays the unbranded last-resort path.
- No per-notification custom image on the Tauri side — `tauri-plugin-notification` exposes no macOS banner-image API; the banner inherits the app-bundle icon by design.
- No change to notification copy, timing, cadence, sound, dedup, cooldowns, or click-routing-via-tray behavior.
- No backend, SQLite, or web-UI changes. No new runtime dependencies.
- macOS only.

## Success Criteria

1. On a clean install where notification permission is **granted**, launching Squirrel fires exactly **one** bootstrap banner and creates the `~/.squirrel/.notif_identity` sentinel; relaunching does **not** re-fire it. If permission is denied, no sentinel is created and the bootstrap retries next launch.
2. After granting **System Settings → Notifications → Squirrel**, a Tauri banner (e.g. the daily focus plan) shows the **Squirrel logo**.
3. After the daemon is **reinstalled**, a daemon deadline reminder posted via `terminal-notifier` (on a warmed identity) shows the **Squirrel logo** and, when clicked, activates Squirrel and routes the deep-link.
4. `native-notification-banner` `R-1.6` requires `-sender com.metuur.squirrel` (sound deferred to `notification-sound-selection`); `R-1.10` is marked delivered/superseded; `docs/release.md` (or the companion README) documents both the permission grant **and** the daemon reinstall step.
5. The existing `apps/cli/tests/test_emitters.sh` assertion is inverted to require `-sender` (was: forbid it); the `osascript` fallback path is unchanged and still functions when `terminal-notifier` is absent.
