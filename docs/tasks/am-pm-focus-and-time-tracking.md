# AM/PM Focus Slots & Time Tracking — Tasks

Source specs: `docs/hld/am-pm-focus-and-time-tracking.md`, `docs/lld/am-pm-focus-and-time-tracking.md`, `docs/ears/am-pm-focus-and-time-tracking.md`.

Dependency layers:
```
1.1 (db.py + schema)
 │
 ├─ 1.2 (server startup: init_schema + orphan-close)
 │
 ├─ 3.1 (focus_picks INSERT/UPDATE) ──► 4.3 (GET /history)
 │
 └─ 5.1 (POST /checkin) ──► 5.2 (POST /checkout) ──► 5.4 (POST /recalculate)
         │                        │
         └────────────────────────┴──► 8.2 (checkin/out tests)

2.1 (focus_picker _token_now + _slot_key for today_pm)
 │
 ├─ 2.2 (strip-pass slot isolation) ──► 2.3 (get_manual_focus: today_pm)
 │                                           │
 │                                           └─ 4.2 (GET /api/focus: today_pm field)
 │                                                    │
 │                                                    └─ 7.1 (tray morning prompt)
 │
 └─ 4.1 (PUT /api/focus/today: slot param) ──► 8.1 (AM/PM slot tests)

4.1, 4.2, 5.1, 5.2
 └──────────────────► 6.1 (client.ts) ──► 6.2 (FocusPickerModal) ──► 6.3 (HomePage cards)

4.3 ──► 8.3 (history tests)
```

---

## Unit 1: SQLite Foundation

- [x] **1.1** Create `apps/cli/lib/db.py` with `get_conn()` and `init_schema()` (est: ~45m)
  - acceptance: R-2.1, R-2.2, R-2.3 — `get_conn()` opens `{state_dir}/squirrel.db` with `PRAGMA journal_mode=WAL`; `init_schema()` creates `focus_picks` and `work_sessions` tables if they do not exist; each call returns a new connection (no shared global).
  - verify: pytest — call `init_schema(get_conn())` twice on a temp db path; assert both tables exist and the second call is idempotent (no error, no duplicate tables). Assert `PRAGMA journal_mode` returns `wal`.

- [ ] **1.2** Call `init_schema()` and auto-close orphan sessions at server startup in `server.py` (deps: 1.1, est: ~20m)
  - acceptance: R-2.2, R-3.5 — On startup, `init_schema()` is called once; a single SQL UPDATE closes `work_sessions` rows where `checkout_at IS NULL AND date < date('now','localtime')` by setting `checkout_at = date || 'T23:59:59'`.
  - verify: seed a temp db with one open session dated yesterday; start the server init block (or call the startup function directly); assert the row now has `checkout_at` set and no open sessions remain for past dates.

---

## Unit 2: AM/PM Focus Slots

- [x] **2.1** Extend `_token_now()` and `_slot_key()` in `focus_picker.py` for `"today_pm"` (est: ~20m)
  - acceptance: R-1.1, R-1.2 — `_token_now("today_pm")` returns `YYYY-MM-DD-PM` (local date); `_slot_key("today_pm")` returns `"focus_today_pm"`; invalid slot still raises `ValueError`.
  - verify: unit test — freeze clock; assert `_token_now("today_pm") == "2026-05-30-PM"` and `_slot_key("today_pm") == "focus_today_pm"`.

- [x] **2.2** Update strip-pass in `set_manual_focus()` to isolate AM and PM keys (deps: 2.1, est: ~30m, mutex: focus_picker)
  - acceptance: R-1.3 — Setting `"today"` removes `focus_today` from other files but never touches `focus_today_pm`. Setting `"today_pm"` removes `focus_today_pm` from other files but never touches `focus_today`.
  - verify: pytest — two intent files: A has `focus_today: <today>`, B has `focus_today_pm: <today>-PM`. Call `set_manual_focus(vault, "today", new_project, C)`. Assert A loses `focus_today`; B still has `focus_today_pm`; C gains `focus_today`.

- [x] **2.3** Update `get_manual_focus()` to return `today_pm` slot (deps: 2.2, est: ~20m, mutex: focus_picker)
  - acceptance: R-1.4, R-1.5 — Returns a dict with keys `today`, `today_pm`, `week`. `today_pm` is `None` when no matching token exists for today. If `today_pm` is not set, callers treat `today` as covering both halves.
  - verify: pytest — vault with one intent carrying `focus_today_pm: 2026-05-30-PM`; assert `get_manual_focus(vault)["today_pm"]` is not None and `["today"]` is None.

---

## Unit 3: Focus Pick History

- [ ] **3.1** Wire `set_manual_focus()` and `clear_manual_focus()` to INSERT/UPDATE `focus_picks` in SQLite (deps: 1.1, 2.2, mutex: focus_picker, est: ~40m)
  - acceptance: R-2.4, R-2.5 — Every `set_manual_focus()` call INSERTs a row into `focus_picks` (`cleared_at = NULL`). Every `clear_manual_focus()` call UPDATEs the matching open row setting `cleared_at = now`.
  - verify: pytest — call `set_manual_focus()` for slot `"today_pm"`, then read `focus_picks`; assert one row with correct vault/slot/date/project_slug/intent_slug and `cleared_at IS NULL`. Call `clear_manual_focus()`, assert same row now has `cleared_at` set.

---

## Unit 4: API Extensions

- [x] **4.1** Update `PUT /api/focus/today` to accept `slot: "am"|"pm"` body param (deps: 2.2, est: ~30m)
  - acceptance: R-5.1, R-5.2 — `slot` defaults to `"am"` when omitted (backwards compatible). `"am"` routes to `set_manual_focus("today", ...)`; `"pm"` routes to `set_manual_focus("today_pm", ...)`.
  - verify: HTTP test — `PUT /api/focus/today` with `{project_slug, intent_slug}` (no slot) → intent gets `focus_today`; same call with `{..., slot: "pm"}` → intent gets `focus_today_pm`.

- [x] **4.2** Extend `GET /api/focus` response to include `today_pm` field (deps: 2.3, est: ~20m)
  - acceptance: R-5.3 — Response shape: `{today: ManualPick|null, today_pm: ManualPick|null, week: ManualPick|null}`.
  - verify: HTTP test — vault with both `focus_today` and `focus_today_pm` set on different intents; assert response includes both non-null with correct `intent_slug` values.

- [ ] **4.3** Add `GET /api/focus/history` endpoint (deps: 3.1, est: ~45m)
  - acceptance: R-4.1, R-4.2, R-4.3, R-4.4 — `?date=YYYY-MM-DD` returns picks and sessions for that date; `?from=...&to=...` returns the inclusive range; no params defaults to today; `work_sessions` rows include computed `duration_minutes` (null if open).
  - verify: seed `focus_picks` and `work_sessions` with known rows; call `GET /api/focus/history?date=2026-05-30`; assert response contains expected rows and `duration_minutes` is correct for closed sessions.

---

## Unit 5: Check-in / Check-out

- [ ] **5.1** Add `POST /api/focus/checkin` endpoint (deps: 1.1, est: ~30m)
  - acceptance: R-3.1, R-5.4 — Accepts `{project_slug, intent_slug, slot}`; INSERTs a `work_sessions` row with `checkin_at = now`, `checkout_at = NULL`; returns `{session_id}`.
  - verify: HTTP test — POST checkin; assert 200 response with `session_id`; query db directly and assert row exists with `checkout_at IS NULL`.

- [ ] **5.2** Add `POST /api/focus/checkout` endpoint with `_update_time_invested()` helper (deps: 5.1, est: ~60m)
  - acceptance: R-3.2, R-3.3, R-3.4, R-3.7 — Finds the open session for current vault; sets `checkout_at = now`; computes `SUM(checkout_at - checkin_at)` across all sessions for that `intent_slug`; writes `time_invested_minutes: <n>` to the intent file's YAML frontmatter; returns `{session_id, duration_minutes, time_invested_minutes}`. Returns HTTP 409 `{"error": "no_open_session"}` if no open session exists.
  - verify: checkin → checkout sequence; assert db row is closed; assert intent file frontmatter contains `time_invested_minutes: <n>` matching computed total; second checkin → checkout; assert total accumulates correctly.

- [ ] **5.3** Auto-close orphan sessions at server startup (covered by 1.2 — no separate story needed)

- [ ] **5.4** Add `POST /api/focus/recalculate` endpoint (deps: 5.2, est: ~30m)
  - acceptance: R-3.6 — For every distinct `intent_slug` in `work_sessions`, recomputes `SUM(duration)` and rewrites `time_invested_minutes` in the corresponding intent file.
  - verify: manually set `time_invested_minutes: 0` on an intent that has closed sessions in db; call `POST /api/focus/recalculate`; assert frontmatter is updated to correct total.

---

## Unit 6: Frontend

- [ ] **6.1** Add focus API calls to `client.ts` (deps: 4.1, 4.2, 5.1, 5.2, est: ~30m)
  - acceptance: R-5.1 to R-5.5 — Exports `setFocus(slot, projectSlug, intentSlug)`, `clearFocus(slot)`, `checkin(projectSlug, intentSlug, slot)`, `checkout()`, `getFocusHistory(params)`.
  - verify: TypeScript compiles without error; each function calls the correct HTTP method and path.

- [x] **6.2** Wire `FocusPickerModal.tsx` to `PUT /api/focus/today` with slot param (deps: 6.1, est: ~30m)
  - acceptance: R-7.6 — Modal accepts a `slot: "am"|"pm"` prop; on confirm calls `api.setFocus(slot, ...)` instead of the existing start-prompt flow path.
  - verify: open modal with `slot="pm"`, select an intent, confirm; assert `focus_today_pm` appears in the intent file's frontmatter.

- [ ] **6.3** Update `HomePage.tsx` — AM/PM cards, check-in/out buttons, `time_invested` display (deps: 6.1, 6.2, est: ~60m)
  - acceptance: R-7.1 to R-7.5 — One card when only `today` is set; two cards (AM/PM) when `today_pm` is also set. "Check in" / "Check out" button on active card. Active session shows pulsing indicator. `time_invested_minutes > 0` displays as "Xh Ym".
  - verify: browser test — set both AM and PM picks; assert two cards render. Check in; assert indicator appears and button changes to "Check out". Check out; assert `time_invested` text appears.

---

## Unit 7: Morning Prompt

- [ ] **7.1** Add startup focus check to `tray_alerts.rs` (deps: 4.2, est: ~45m)
  - acceptance: R-6.1 to R-6.5 — On app start, GET `/api/focus`; if `today` is null AND `last_focus_prompt` in vault state JSON ≠ today, fire tray notification "What's your focus today? Tap to pick." and write `last_focus_prompt: YYYY-MM-DD` to state JSON. Clicking notification opens `http://localhost:3939`. Does not fire if focus already set or already prompted today.
  - verify: clear `focus_today` and `last_focus_prompt`; restart desktop app; assert tray notification fires. Set focus, restart; assert notification does not fire. Same day, clear focus, restart; assert notification does not fire (already prompted today).

---

## Unit 8: Tests

- [x] **8.1** Unit tests for AM/PM slot extension in `focus_picker.py` (deps: 2.3, est: ~30m)
  - acceptance: R-1.1 to R-1.7 — Covers: token format, strip-pass isolation, duplicate tiebreak, expiry logic for `today_pm` slot.
  - verify: `make test-cli` stays green; new test file or additions to existing `test_focus_picker.py` pass.

- [ ] **8.2** Integration tests for `POST /api/focus/checkin` and `POST /api/focus/checkout` (deps: 5.2, est: ~40m)
  - acceptance: R-3.1 to R-3.4, R-3.7 — Covers: open session insert, checkout closes session, `time_invested_minutes` written to frontmatter, accumulated total across multiple sessions, 409 on missing open session.
  - verify: test suite passes; `time_invested_minutes` assertions use real db (not mock).

- [ ] **8.3** Integration tests for `GET /api/focus/history` (deps: 4.3, est: ~30m)
  - acceptance: R-4.1 to R-4.4 — Covers: date filter, range filter, default-to-today, `duration_minutes` computed correctly, null for open sessions.
  - verify: test suite passes with seeded db fixture.
