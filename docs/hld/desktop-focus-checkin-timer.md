# Desktop Focus Check-in / Check-out & Live Timer — High-Level Design

## Overview
Bring **check-in / check-out** of focus work into the native Tauri popup and show a
live **HH:MM timer** for the current session. The timer is *derived*, not a
background process: on every render it computes `now − checkin_at` from the open
work-session's check-in timestamp. Nothing runs while the window is closed; when
the user reopens the popup, the elapsed time is recomputed from `checkin_at` and
the display is correct again. Switching to a different task while one is open is
gently gated.

The backend already exposes everything required —
`POST /api/focus/checkin`, `POST /api/focus/checkout`, and
`GET /api/focus/session` (see `am-pm-focus-and-time-tracking` Unit 3). This change
is **frontend-only** in `apps/desktop`.

## Stakeholders & Impact
- **Primary user (ADHD knowledge worker):** today they can pick a focus but cannot
  mark "I'm sitting down with this now" from the popup, nor see how long the
  current sitting has run. After this ships they tap **Check in** on any focus
  pick, watch an HH:MM clock, and **Check out** when they stop — banking the
  minutes against that intent.
- **Web UI:** unchanged. It keeps its own parallel focus surface; this work does
  not touch it (per the "desktop completes actions in-app" convention).
- **Backend / SQLite `work_sessions`:** consumer only — no schema or endpoint
  changes. The existing one-open-session-per-vault invariant is relied upon.

## Goals
- From the popup, the user can **Check in** to any focus pick (Today AM, Today PM,
  or This Week) — but only **one** session open at a time, vault-wide.
- While checked in, the focus card shows a live **HH:MM** timer that ticks each
  minute and is correct after the window is closed and reopened.
- The user can **Check out** to end the current session, banking the elapsed
  minutes against that intent.
- Switching to a different task while a session is open shows a **friendly
  confirmation** and requires checking out the current task first — no silent
  auto-checkout.
- No background timer process; the clock is purely derived from `checkin_at` and
  the computer's local clock.

## Non-Goals
- No backend, SQLite, or HTTP-API changes.
- No changes to the web UI focus surface.
- No Pause/Hold concept — stopping work is a plain **Check out** (deferred; may
  return later).
- No seconds-precision display, no idle/auto-pause detection, no notifications
  tied to session length.
- No change to estimate↔actual reconciliation copy (the existing `EstimateLine`
  stays as the home for accumulated totals).

## Success Criteria
- Tapping **Check in** on a focus pick opens a session and the card shows `00:00`,
  advancing to `00:01` after a minute.
- Closing the popup for N minutes and reopening it shows the timer at the correct
  `HH:MM` (≈ N minutes later), proving the clock is derived, not background-run.
- **Check out** banks the elapsed minutes against the intent (verified via
  `time_invested_minutes`).
- Tapping **Check in** on a second pick while one is open shows the friendly
  message and does **not** open a second session.
- **Check out** closes the session, the timer disappears, and the card returns to a
  pickable "Check in" state.
