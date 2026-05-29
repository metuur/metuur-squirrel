# Manual Focus Pick (Today & Week) — EARS Specifications

## Unit 1: Frontmatter storage contract

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL store today's manual focus as a single frontmatter key `focus_today` on the chosen intent file, with value equal to the user's local date in `YYYY-MM-DD` format. |
| R-1.2 | THE SYSTEM SHALL store this-week's manual focus as a single frontmatter key `focus_week` on the chosen intent file, with value equal to the current ISO-8601 year-week token in `GGGG-Www` format (e.g. `2026-W22`). |
| R-1.3 | THE SYSTEM SHALL compute "today's local date" and "current ISO week" using the host machine's local timezone — NOT UTC. |
| R-1.4 | WHEN reading a `focus_today` value, IF the value does NOT equal today's local date token, THE SYSTEM SHALL treat the slot as unset (do not return it via the API; do not mutate the file). |
| R-1.5 | WHEN reading a `focus_week` value, IF the value does NOT equal the current ISO-week token, THE SYSTEM SHALL treat the slot as unset. |
| R-1.6 | THE SYSTEM SHALL preserve all other frontmatter keys, key order, and comments when writing to an intent file. A round-trip read → no-op write SHALL produce a byte-identical file. |
| R-1.7 | WHEN clearing a slot, THE SYSTEM SHALL delete the key from the frontmatter entirely. THE SYSTEM SHALL NOT write `focus_today: null`, `focus_today: ""`, or any sentinel value. |
| R-1.8 | THE SYSTEM SHALL NOT store the manual focus in `~/.squirrel/`, in `apps/backend/`, or in any location outside the vault. |

## Unit 2: Single-pick invariant

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the user sets a new value for `focus_today` via the API or CLI, THE SYSTEM SHALL first scan all intent files under the vault's active-projects root and strip any existing `focus_today` key whose value equals today's local date, BEFORE writing the new key. |
| R-2.2 | Equivalent invariant for `focus_week`: WHEN setting a new value, THE SYSTEM SHALL strip every other intent file's `focus_week` key whose value equals the current ISO-week token, before writing the new key. |
| R-2.3 | WHEN setting `focus_today` and `focus_week` independently, THE SYSTEM SHALL NOT touch the other slot's key. |
| R-2.4 | IF after the strip step the API discovers that the target intent file already carries the same key with today's/this-week's token, THE SYSTEM SHALL still rewrite the value (idempotent set). |
| R-2.5 | THE strip step SHALL skip intent files whose `focus_today` value is a date OTHER than today's (lazy cleanup is bounded to the slot's current token only). |
| R-2.6 | IF a vault read discovers two or more intent files with the same slot's current token (e.g. due to a manual Obsidian edit), THE SYSTEM SHALL return the one with the most-recent file mtime and SHALL NOT error. |

## Unit 3: `/api/focus/*` endpoints

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL expose `GET /api/focus` returning a JSON object of shape: `{ today: ManualPick \| null, week: ManualPick \| null }` where `ManualPick = { project_slug: string, project_title: string, intent_slug: string, intent_title: string, next_action: string \| null, picked_on: string }`. |
| R-3.2 | THE `picked_on` field SHALL be the YAML value verbatim (the date for `today`, the ISO-week token for `week`). |
| R-3.3 | THE SYSTEM SHALL expose `PUT /api/focus/today` accepting a JSON body of one of: `{ "project_slug": string, "intent_slug": string }` OR `{ "clear": true }`. |
| R-3.4 | THE SYSTEM SHALL expose `PUT /api/focus/week` with the same body shapes. |
| R-3.5 | WHEN `PUT /api/focus/today` receives `{ "clear": true }`, THE SYSTEM SHALL delete the `focus_today` key from every intent file in the vault carrying that key with today's token, and SHALL return the updated `{today, week}` object. |
| R-3.6 | IF `PUT /api/focus/<slot>` receives a body that resolves to no existing intent file (unknown project_slug or intent_slug), THE SYSTEM SHALL return HTTP 404 with body `{ "error": "intent_not_found" }` and SHALL NOT mutate any file. |
| R-3.7 | IF the body is missing both `project_slug` and `clear`, THE SYSTEM SHALL return HTTP 400 with body `{ "error": "bad_request" }`. |
| R-3.8 | THE `/api/focus/*` endpoints SHALL be bound to `127.0.0.1` only, matching the existing binding policy of `apps/backend/server.py`. |

## Unit 4: `/api/home` integration (additive)

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE response of `GET /api/home` SHALL gain a new top-level field `manual_focus: { today: ManualPick \| null, week: ManualPick \| null }`. |
| R-4.2 | THE existing `focus` field of `GET /api/home` SHALL retain its current shape and SHALL continue to be populated solely by the heuristic in `_recommend_focus()`. |
| R-4.3 | THE SYSTEM SHALL NOT suppress, downgrade, or modify any field of `GET /api/home.focus` based on the presence of a manual focus pick. |
| R-4.4 | THE SYSTEM SHALL NOT suppress, downgrade, or modify any field of `GET /api/home.pressing[]` based on the presence of a manual focus pick. |
| R-4.5 | WHEN no manual pick is set for a slot (or the stored value is stale per R-1.4/R-1.5), THE corresponding `manual_focus.<slot>` field SHALL be exactly `null`. |

## Unit 5: `FocusWidget` rendering

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE FocusWidget SHALL render the heuristic focus (`/api/home.focus`) as its primary card with no visual change from the pre-feature behaviour. |
| R-5.2 | THE FocusWidget SHALL render exactly two "manual focus pills" below the primary card, in order: Today, then This week. |
| R-5.3 | WHEN `manual_focus.today` is non-null, THE Today pill SHALL display `📌 Today: {project_title} — {intent_title}` and SHALL be visually distinct from the heuristic card (smaller font, secondary colour). |
| R-5.4 | WHEN `manual_focus.today` is null, THE Today pill SHALL display `📌 Pick today's focus` and SHALL act as the "open picker" trigger. |
| R-5.5 | Same shape applies to the This week pill, substituting `Today` with `This week` and the relevant data field. |
| R-5.6 | WHEN a manual pill is populated, THE pill SHALL show two trailing controls: `Change` (opens FocusPickerModal pre-selected on that slot) and `Clear` (calls `PUT /api/focus/<slot>` with `{clear: true}`). |
| R-5.7 | WHEN the heuristic focus and a manual pick point to the SAME project_slug + intent_slug, THE pill SHALL display an additional checkmark indicator `✓` and the text SHALL read `📌 Today: {…} (aligned with critical)` — making explicit that the user's pick already matches the overdue/critical signal. |
| R-5.8 | THE FocusWidget SHALL NOT hide the primary card under any condition (no "manual pick takes over the card" behaviour). |
| R-5.9 | IF backend status is offline (per Phase 2 R-1.4), THE manual pills SHALL display "—" and the picker action SHALL be disabled. |

## Unit 6: FocusPickerModal

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | WHEN the user clicks a manual pill or its `Change` control, THE FocusPickerModal SHALL open as a modal overlay above the popup. |
| R-6.2 | THE modal SHALL display a list of active projects, sourced from the cached `/api/home.projects[]`. No additional fetch is required at modal-open time for the project list. |
| R-6.3 | WHEN the user expands a project row, THE modal SHALL fetch `GET /api/projects/{slug}` (existing endpoint) once and cache the intent list for the lifetime of the modal session. |
| R-6.4 | WHEN the user clicks an intent row, THE modal SHALL issue `PUT /api/focus/{slot}` with `{project_slug, intent_slug}` and SHALL close on a 2xx response. |
| R-6.5 | IF the PUT returns non-2xx, THE modal SHALL stay open and display the server `error` field inline. The user's selection SHALL NOT be lost. |
| R-6.6 | THE modal SHALL include a `Clear current pick` action that issues `PUT /api/focus/{slot}` with `{clear: true}` and closes on 2xx. |
| R-6.7 | THE modal SHALL include a `Cancel` button that closes without any network request. |
| R-6.8 | THE modal SHALL NOT cache the project/intent list beyond its own lifetime; re-opening fetches afresh. |

## Unit 7: `/sq-focus` CLI command

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL register a new slash command `/sq-focus` in the squirrel plugin. |
| R-7.2 | WHEN invoked with no arguments, `/sq-focus` SHALL print exactly two lines: `Today: {project_title} / {intent_title}` (or `Today: (none)`) and `This week: {project_title} / {intent_title}` (or `This week: (none)`). |
| R-7.3 | WHEN invoked as `/sq-focus today {TAG}/{INTENT-SLUG}`, THE command SHALL call `PUT /api/focus/today` with that pair and print `Today's focus set: {TAG}/{INTENT-SLUG}`. |
| R-7.4 | WHEN invoked as `/sq-focus week {TAG}/{INTENT-SLUG}`, THE command SHALL behave equivalently for the week slot. |
| R-7.5 | WHEN invoked as `/sq-focus today --clear` or `/sq-focus week --clear`, THE command SHALL call `PUT /api/focus/{slot}` with `{clear: true}` and print `Today's focus cleared.` / `This week's focus cleared.`. |
| R-7.6 | IF the backend is unreachable, THE command SHALL print `Backend offline — run \`make backend-start\`` and exit with status 1. |
| R-7.7 | IF the backend returns 404 (intent_not_found), THE command SHALL print `No such intent: {TAG}/{INTENT-SLUG}` and exit with status 1. |
| R-7.8 | THE command SHALL NOT read or write intent files directly; all mutation flows through `/api/focus/*`. |

## Unit 8: macOS reminder daemon "Focus now" — deep-link signal

> **Model change.** `native-notification-banner` story 1.4 retired `show_dialog`/`open_in_web_ui`. Native banners (terminal-notifier / `osascript display notification`) have no custom action buttons; clicking a banner can only open a URL. Unit 8 was rewritten to model the new interaction: the daemon tags its banner URL with `?action=focus` so the desktop application can distinguish a focus-bearing click from any other deep-link entry point. The active-intent resolve + `PUT /api/focus/today` call moves to the desktop side (consumed by a future story in `native-notification-banner` unit 4).

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | THE daemon's `emit_banner` SHALL pass a URL of the form `squirrel://projects/<TAG>?action=focus` to `terminal-notifier -open`, where `<TAG>` is the alerted project ID. The query string `action=focus` SHALL be the sole means by which a focus-bearing click is distinguished from a plain navigation click. |
| R-8.2 | WHEN the user clicks a focus-bearing banner that opens a `squirrel://projects/<TAG>?action=focus` URL, THE desktop application SHALL resolve the active intent for `<TAG>` and SHALL call `PUT /api/focus/today` with `{project_slug: <TAG>, intent_slug: <active_intent>}`. *(Desktop-side requirement; implemented by a separate story in `native-notification-banner` unit 4. The daemon's only obligation is R-8.1.)* |
| R-8.3 | IF the daemon's selected emitter is `osascript display notification` or `show_dialog_fallback` (i.e. terminal-notifier is unavailable), THE banner SHALL still be emitted but no clickable URL SHALL be attached. This is an accepted v1 limitation; focus-set on click is only available via the terminal-notifier path. |
| R-8.4 | (REMOVED — daemon no longer issues the focus-set curl; the desktop owns that call. Backend-unreachable handling is the desktop's concern.) |
| R-8.5 | (REMOVED — daemon no longer resolves active intent; the desktop owns that resolution.) |
| R-8.6 | (REMOVED — the desktop's deep-link handler navigates to the project page as part of its R-8.2 flow; no separate `open` call from the daemon is needed.) |
| R-8.7 | (REMOVED — the daemon has no per-click feedback channel from the desktop and so cannot record per-click choice in `reminders-state.json`. Existing emission-time `update_state_after_emit` semantics (cadence/cap accounting) are unaffected.) |
| R-8.8 | THE daemon SHALL NOT change its workday window, cadence, or daily-cap behaviour as part of this feature. |
| R-8.9 | (REMOVED — no buttons exist on a banner; "Dismiss" and "Snooze" were button-model concepts. The macOS Notification Center's built-in dismiss/clear gestures are unchanged and out of scope.) |

## Unit 9: Auto-expiry semantics

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | AT any moment after local midnight, IF the `focus_today` value on the previously-picked intent file equals the *previous* day's date, THE `GET /api/focus.today` and `GET /api/home.manual_focus.today` fields SHALL return `null`. |
| R-9.2 | AT any moment after the ISO-week rollover (Monday 00:00 local), IF the `focus_week` value on the previously-picked intent equals the *previous* ISO week, THE `GET /api/focus.week` and `GET /api/home.manual_focus.week` fields SHALL return `null`. |
| R-9.3 | THE SYSTEM SHALL NOT run any background process, cron job, or launchd entry to enforce auto-expiry. Expiry is computed at API request time only. |
| R-9.4 | WHEN the user next sets a focus for an expired slot, THE single-pick invariant (R-2.1 / R-2.2) SHALL run and SHALL strip only entries matching the *new* token. Entries still carrying *old* tokens are not pruned by this write. |

## Unit 10: Invariants preserved

| ID    | EARS statement |
|-------|----------------|
| R-10.1 | The 3-rule heuristic in `apps/cli/lib/status_aggregator.py:_recommend_focus()` SHALL NOT be modified. |
| R-10.2 | The shape and content of `GET /api/home.focus`, `GET /api/home.pressing[]`, and `GET /api/home.projects[]` SHALL NOT change. |
| R-10.3 | The macOS deadline daemon's polling cadence, workday window, snooze logic, and daily-dialog cap SHALL NOT change. |
| R-10.4 | The `~/.squirrel/state.json` file written by `/sq-start` SHALL NOT be read or written by any code path in this feature. |
| R-10.5 | The Tauri Rust process SHALL NOT directly read or write any intent file. All mutations go through `apps/backend/server.py`. |
