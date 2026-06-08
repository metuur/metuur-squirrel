# Desktop Focus Check-in / Check-out & Live Timer — EARS Specifications

Keywords: `THE SYSTEM SHALL` (always-on) · `WHEN <trigger>` (event) ·
`WHILE <state>` (continuous) · `IF <condition>` (conditional/gate) ·
`WHERE <context>` (scoped). Scope: the native Tauri desktop popup (`apps/desktop`).
The backend endpoints are consumed as-is; no backend behaviour is specified here.

## Unit 1: API client

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL expose `api.focusCheckin({project_slug, intent_slug, slot})` that `POST`s to `/api/focus/checkin` and resolves to `{session_id}`. |
| R-1.2 | THE SYSTEM SHALL expose `api.focusCheckout()` that `POST`s to `/api/focus/checkout` and resolves to `{session_id, duration_minutes, time_invested_minutes}`. |
| R-1.3 | THE SYSTEM SHALL expose `api.focusSession()` that `GET`s `/api/focus/session` and resolves to an `OpenSession {project_slug, intent_slug, checkin_at}`. |
| R-1.4 | WHEN `/api/focus/session` responds `404` (`no_open_session`), `api.focusSession()` SHALL resolve to `null` and SHALL NOT throw. |
| R-1.5 | THE SYSTEM SHALL set the check-in `slot` to `"today"` for an AM pick, `"today_pm"` for a PM pick, and `"week"` for the weekly pick. |

## Unit 2: Derived timer (no background process)

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHILE a work session is open, THE SYSTEM SHALL compute elapsed time as `floor((now − checkin_at) / 60000)` minutes, deriving it from `checkin_at`, never from an accumulator. |
| R-2.2 | THE SYSTEM SHALL render the elapsed time as a zero-padded `HH:MM` string with unbounded hours (e.g. `00:07`, `12:34`). |
| R-2.3 | WHILE the popup document is visible AND a session is open, THE SYSTEM SHALL advance the displayed `HH:MM` once per minute via a single foreground `setInterval`. |
| R-2.4 | WHEN the popup document becomes hidden, THE SYSTEM SHALL clear that interval so no timer work runs while the window is closed or backgrounded. |
| R-2.5 | WHEN the popup document becomes visible again, THE SYSTEM SHALL re-fetch the open session and immediately recompute `HH:MM` from `checkin_at`, so the displayed value is correct without waiting for the next minute tick. |
| R-2.6 | IF `now − checkin_at` is negative (clock skew), THE SYSTEM SHALL clamp the displayed elapsed time to `00:00`. |
| R-2.7 | THE SYSTEM SHALL resolve `checkin_at` (backend UTC ISO) to an absolute epoch via `Date.parse`, and compute elapsed against the computer's local clock via `Date.now()`; because both are absolute, elapsed minutes SHALL be correct in any machine timezone. |

## Unit 3: Check in / Check out

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHILE online and no session is open, THE SYSTEM SHALL show a **Check in** control on every focus pick (Today AM, Today PM, This Week). |
| R-3.2 | WHEN the user taps **Check in** on a pick AND no session is open, THE SYSTEM SHALL call `api.focusCheckin` for that pick's `{project_slug, intent_slug, slot}`, then refresh home and the open session. |
| R-3.3 | WHILE a session is open for a pick, THE SYSTEM SHALL show the live `HH:MM` timer plus a **Check out** control on that pick, and SHALL NOT show its **Check in** control. |
| R-3.4 | WHEN the user taps **Check out**, THE SYSTEM SHALL call `api.focusCheckout` and refresh home and the open session; the pick SHALL return to the **Check in** state. |
| R-3.5 | WHEN a checked-out intent is checked in again later, THE SYSTEM SHALL treat it as a new session; the intent's total time SHALL be the backend sum of all its segments (`time_invested_minutes`). |
| R-3.6 | THE SYSTEM SHALL show only the live running-segment timer on the card and SHALL NOT show accumulated past totals there (those remain in the existing estimate/actual line). |

## Unit 4: One session at a time & friendly switch gate

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL permit at most one open work session vault-wide and SHALL NOT attempt a second check-in while one is open. |
| R-4.2 | WHEN the user taps **Check in** on a pick WHILE a session is open for a *different* intent, THE SYSTEM SHALL present a friendly in-app confirmation dialog — e.g. "Do you really want to change task? Double-check it's really necessary. If yes, that's fine — but check out the current task before checking into a new one." — naming the currently-open and attempted tasks, and SHALL NOT call `api.focusCheckin`. |
| R-4.3 | THE SYSTEM SHALL offer a **Check out current task** action in the switch dialog that checks out the open session and dismisses the dialog, leaving the open session untouched until the user invokes it. |
| R-4.4 | THE SYSTEM SHALL NOT auto-check-out the running session, and SHALL NOT auto-check-in the attempted task; after checking out via the dialog the user re-taps **Check in**. |
| R-4.5 | THE SYSTEM SHALL allow the user to dismiss the switch dialog (Keep current task / Escape / backdrop) leaving the open session running and no new session started. |

## Unit 5: Offline & resilience

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | WHILE the backend is offline, THE SYSTEM SHALL hide or disable the Check in / Check out / Pause controls, consistent with the existing dimmed focus-card pattern. |
| R-5.2 | IF a check-in, check-out, or session fetch request fails, THE SYSTEM SHALL fail best-effort (leave existing UI state in place) without crashing the popup, matching the existing focus-action error handling. |
| R-5.3 | WHEN the server has auto-closed a stale prior-day session (backend `R-3.5`), `api.focusSession()` SHALL return `null` and THE SYSTEM SHALL show no live timer. |
| R-5.4 | THE SYSTEM SHALL NOT modify any backend, SQLite, or web-UI behaviour. |
