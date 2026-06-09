# AM/PM Focus Slots & Time Tracking — EARS Specifications

## Unit 1: AM/PM Focus Slots

| ID | EARS statement |
|----|----------------|
| R-1.1 | WHEN the user sets a focus for slot `"today"`, THE SYSTEM SHALL write `focus_today: YYYY-MM-DD` to the chosen intent file's YAML frontmatter and remove `focus_today` from all other intent files in the vault. |
| R-1.2 | WHEN the user sets a focus for slot `"today_pm"`, THE SYSTEM SHALL write `focus_today_pm: YYYY-MM-DD-PM` to the chosen intent file's YAML frontmatter and remove `focus_today_pm` from all other intent files in the vault. |
| R-1.3 | THE SYSTEM SHALL NOT remove `focus_today` when setting `focus_today_pm`, and SHALL NOT remove `focus_today_pm` when setting `focus_today`. |
| R-1.4 | IF `focus_today_pm` is not set for today's date, THE SYSTEM SHALL treat `focus_today` as the active focus for both AM and PM halves of the day. |
| R-1.5 | WHEN `GET /api/focus` is called, THE SYSTEM SHALL return `today_pm: null` if no intent file carries a `focus_today_pm` token matching today's date. |
| R-1.6 | WHEN the user clears a slot, THE SYSTEM SHALL remove the corresponding frontmatter key from the intent file (key deleted, not set to null). |
| R-1.7 | IF two intent files carry the same slot token for today (e.g. after a manual vault edit), THE SYSTEM SHALL treat the most-recently-modified file as active and prune the duplicate on the next write. |

## Unit 2: SQLite Database

| ID | EARS statement |
|----|----------------|
| R-2.1 | THE SYSTEM SHALL maintain a SQLite database at `{state_dir}/squirrel.db`. |
| R-2.2 | WHEN the server starts, THE SYSTEM SHALL create the `focus_picks` and `work_sessions` tables if they do not exist. |
| R-2.3 | THE SYSTEM SHALL open the database with `PRAGMA journal_mode=WAL` on every connection. |
| R-2.4 | THE SYSTEM SHALL open a new database connection per HTTP request and close it when the request completes. |
| R-2.5 | WHEN the user sets a manual focus (any slot), THE SYSTEM SHALL INSERT a row into `focus_picks` with `vault`, `slot`, `date`, `project_slug`, `intent_slug`, `picked_at = now`, `cleared_at = NULL`. |
| R-2.6 | WHEN the user clears a manual focus (any slot), THE SYSTEM SHALL UPDATE the matching open `focus_picks` row, setting `cleared_at = now`. |

## Unit 3: Check-in / Check-out

| ID | EARS statement |
|----|----------------|
| R-3.1 | WHEN `POST /api/focus/checkin` is called with `{project_slug, intent_slug, slot}`, THE SYSTEM SHALL INSERT a row into `work_sessions` with `checkin_at = now` and `checkout_at = NULL`. |
| R-3.2 | WHEN `POST /api/focus/checkout` is called, THE SYSTEM SHALL find the open `work_sessions` row for the current vault (where `checkout_at IS NULL`) and set `checkout_at = now`. |
| R-3.3 | WHEN a checkout completes, THE SYSTEM SHALL compute `SUM(checkout_at - checkin_at)` in seconds across ALL `work_sessions` rows for that `vault + intent_slug` where `checkout_at IS NOT NULL`, convert to integer minutes, and write `time_invested_minutes: <n>` to the intent file's YAML frontmatter. |
| R-3.4 | IF `time_invested_minutes` in the intent file differs from the SQLite-derived total, THE SYSTEM SHALL treat the SQLite value as authoritative. |
| R-3.5 | WHEN the server starts, THE SYSTEM SHALL close any `work_sessions` rows where `checkout_at IS NULL` AND `date < today` by setting `checkout_at = date || 'T23:59:59'`. |
| R-3.6 | WHEN `POST /api/focus/recalculate` is called, THE SYSTEM SHALL recompute `time_invested_minutes` for every intent in the vault from `work_sessions` aggregates and update each intent file's frontmatter accordingly. |
| R-3.7 | IF no open work session exists when `POST /api/focus/checkout` is called, THE SYSTEM SHALL return HTTP 409 with `{"error": "no_open_session"}`. |

## Unit 4: GET /api/focus/history

| ID | EARS statement |
|----|----------------|
| R-4.1 | WHEN `GET /api/focus/history` is called with `?date=YYYY-MM-DD`, THE SYSTEM SHALL return all `focus_picks` and `work_sessions` rows for the current vault on that date. |
| R-4.2 | WHEN `GET /api/focus/history` is called with `?from=YYYY-MM-DD&to=YYYY-MM-DD`, THE SYSTEM SHALL return all rows for the current vault within the inclusive date range. |
| R-4.3 | THE SYSTEM SHALL include a computed `duration_minutes` field on each `work_sessions` row in the history response (null if `checkout_at` is null). |
| R-4.4 | IF neither `date` nor `from/to` is provided, THE SYSTEM SHALL return rows for today's date. |

## Unit 5: API Shape

| ID | EARS statement |
|----|----------------|
| R-5.1 | THE SYSTEM SHALL accept `PUT /api/focus/today` with body `{project_slug, intent_slug, slot: "am"\|"pm"}` where `slot` defaults to `"am"` when omitted (backwards compatible). |
| R-5.2 | WHEN `slot` is `"am"`, `PUT /api/focus/today` SHALL call `set_manual_focus("today", ...)`. WHEN `slot` is `"pm"`, it SHALL call `set_manual_focus("today_pm", ...)`. |
| R-5.3 | `GET /api/focus` SHALL return `{today: ManualPick\|null, today_pm: ManualPick\|null, week: ManualPick\|null}`. |
| R-5.4 | `POST /api/focus/checkin` SHALL return `{session_id: <int>}` on success. |
| R-5.5 | `POST /api/focus/checkout` SHALL return `{session_id, duration_minutes, time_invested_minutes}` on success. |

## Unit 6: Morning Prompt (Tray)

| ID | EARS statement |
|----|----------------|
| R-6.1 | WHEN the desktop app starts, THE SYSTEM SHALL call `GET /api/focus` to read today's focus plan (`today` AM slot and `today_pm` PM slot). |
| R-6.2 | IF the daily prompt has not already fired today, THE SYSTEM SHALL fire a tray notification regardless of whether a focus is set: when a focus plan exists, "Your plan for today — {plan} — tap to confirm or change it." (where `{plan}` combines the AM and PM slots); otherwise "What's your focus today? Tap to pick your focus for the morning." |
| R-6.3 | WHEN the morning prompt notification is fired, THE SYSTEM SHALL write `last_focus_prompt: YYYY-MM-DD` (today) to vault state JSON. |
| R-6.4 | THE SYSTEM SHALL NOT fire the morning prompt more than once per calendar day per vault. |
| R-6.5 | WHEN the user clicks the morning prompt notification, THE SYSTEM SHALL open `http://localhost:3939` (the web UI). |

## Unit 7: Frontend — Focus Card

| ID | EARS statement |
|----|----------------|
| R-7.1 | WHEN `today_pm` is null, THE SYSTEM SHALL render one focus card labelled "TODAY" showing the `today` pick (or "No focus set"). |
| R-7.2 | WHEN `today_pm` is not null, THE SYSTEM SHALL render two focus cards: one labelled "AM" showing `today`, one labelled "PM" showing `today_pm`. |
| R-7.3 | WHEN `time_invested_minutes > 0`, THE SYSTEM SHALL display the value formatted as "Xh Ym" on the focus card for that intent. |
| R-7.4 | WHILE a work session is open (checked in, not checked out), THE SYSTEM SHALL show an active indicator on the focus card. |
| R-7.5 | THE SYSTEM SHALL provide a "Check in" button on the focus card when no session is open, and a "Check out" button when a session is open. |
| R-7.6 | THE SYSTEM SHALL provide a "Change" and "Clear" affordance on each focus card slot, wired to `PUT /api/focus/today` and `PUT /api/focus/today/clear` respectively. |
