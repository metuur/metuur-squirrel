# Future Reminders & Scratch Pad — Tasks

Source specs: `docs/hld/future-reminders-and-scratch-pad.md`, `docs/lld/future-reminders-and-scratch-pad.md`, `docs/ears/future-reminders-and-scratch-pad.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Dependency layers:
```
1.1 (reminder_scanner.py)     1.2 (frontmatter write + callout)
       │                             │           │
       └──────────────┬──────────────┘           │
                      │                         2.3 (extend creation endpoints)
                     2.1 (GET /api/reminders + /api/home extend)
                      │
                     2.2 (PATCH dismiss + snooze)
                      │
             ┌────────┴────────┐
            3.1               4.1 (RemindersWidget)
      (tray sections)
             │
            3.2 (OS notifications)

5.1 (ensure_scratch_pad) → 5.2 (HTTP 403 delete guard)   [independent of Units 1–4]
```

---

## Unit 1: Reminder Field & Scanner

- [x] **1.1** Write `apps/cli/lib/reminder_scanner.py` (est: ~45m)
  - acceptance:
    - R-2.1 — Scans `01-Proyectos-Activos` and `03-Areas` for `reminder_date` in frontmatter at call time.
    - R-2.2 — Files with `estado: done/completado/archived` are excluded.
    - R-2.3 — Files with `reminder_dismissed` set (any non-empty value) are excluded permanently.
    - R-2.4 — Files with `reminder_snoozed_until` set to a future date are suppressed until that date.
    - R-2.5 — `reminder_date` today or in the past, with no suppression → classified as `reminder_active`.
    - R-2.6 — `reminder_date` 1–7 calendar days in the future, with no suppression → classified as `reminder_approaching`.
    - R-2.7 — Items never appear in both a deadline bucket and a reminder bucket (scans are independent).
  - verify:
    - Pytest with fixture `.md` files covering each state: no `reminder_date`, approaching, active, snoozed (future), snoozed (expired — should show as active), dismissed, done.
    - Assert `approaching` and `active` lists are disjoint and correctly populated.

- [x] **1.2** Add frontmatter write helpers + body callout to `apps/cli/lib/intent_parser.py` or a new `reminder_writer.py` (est: ~60m)
  - acceptance:
    - R-1.1 — Accepts `reminder_date` as absolute `YYYY-MM-DD` or relative string (`"in 1 month"`, `"in 3 months"`, `"in 6 months"`, `"in 1 year"`).
    - R-1.2 — Relative strings are resolved to absolute ISO date before writing.
    - R-1.3 — `reminder_date: YYYY-MM-DD` is written into the file's YAML frontmatter atomically (`os.replace()`).
    - R-1.4 — When `reminder_date` is set, a callout block (`> 📅 **Reminder:** YYYY-MM-DD`) is written into the markdown body immediately below the title heading.
    - R-1.5 — When `reminder_dismissed` or a new `reminder_date` replaces the old one, the callout is updated or removed accordingly.
    - R-1.6 — Files without `reminder_date` are unaffected.
  - verify:
    - Pytest: load fixture intent `.md`, call write helper with relative `"in 3 months"`, assert frontmatter has correct absolute date; assert body contains callout below `# Title`; call dismiss helper, assert callout removed.
    - Round-trip: write then re-read via `parse_intent()` — `reminder_date` parses back to the same date string.

---

## Unit 2: Reminder API

- [x] **2.1** Add `GET /api/reminders` and extend `GET /api/home` in `apps/backend/server.py` (deps: 1.1, est: ~30m)
  - acceptance:
    - R-3.1 — `GET /api/reminders` returns `{ "approaching": [...], "active": [...] }` with each entry containing `id`, `title`, `path`, `reminder_date`, `proyecto`.
    - R-3.2 — `GET /api/home` includes `reminders: { "approaching_count": N, "active_count": N }` in its response alongside existing fields.
  - verify:
    - Manual: create a test `.md` file in the vault with `reminder_date` set to today. `curl http://127.0.0.1:3939/api/reminders` returns it in `active`. `curl http://127.0.0.1:3939/api/home` includes `reminders.active_count: 1`.
    - Create a file with `reminder_date` 3 days from now. Appears in `approaching`.

- [x] **2.2** Add `PATCH /api/reminder/<id>/dismiss` and `PATCH /api/reminder/<id>/snooze` in `server.py` (deps: 1.2, 2.1, est: ~30m)
  - acceptance:
    - R-3.3 — `PATCH /api/reminder/<id>/dismiss` writes `reminder_dismissed: <today>` to frontmatter and removes the body callout. Returns HTTP 200.
    - R-3.4 — `PATCH /api/reminder/<id>/snooze` accepts `{ "until": "YYYY-MM-DD" }`, writes `reminder_snoozed_until: <date>`, updates body callout.
    - R-3.5 — Snooze also clears any existing `reminder_dismissed` field.
  - verify:
    - Manual: dismiss a reminder via curl, re-read the `.md` file — `reminder_dismissed` present, callout absent; subsequent `GET /api/reminders` excludes it.
    - Snooze: write `until` 30 days from now, verify file has `reminder_snoozed_until`; verify `GET /api/reminders` excludes the item.

- [x] **2.3** Extend task (intent) and capture creation endpoints to accept `reminder_date` (deps: 1.2, est: ~20m)
  - acceptance:
    - R-3.6 — `POST /api/intents` and `POST /api/captures` (or equivalent) accept optional `reminder_date` field (absolute or relative string).
    - If provided, `reminder_date` is written to frontmatter and body callout via the helpers from 1.2.
  - verify:
    - Create an intent via the web UI `NewTaskModal` with a reminder date — inspect the created file, confirm frontmatter and body callout are correct.

---

## Unit 3: Tray & OS Notifications

- [ ] **3.1** Add `ReminderAlert` struct and "On your radar" / "Reminder due" tray sections in `apps/desktop/src-tauri/src/tray_alerts.rs` (deps: 2.1, est: ~45m)
  - acceptance:
    - R-4.1 — `reminder_approaching` items appear in a tray section labeled **"On your radar"**, below "PRESSING NOW".
    - R-4.2 — `reminder_active` items appear in a tray section labeled **"Reminder due"**, below "On your radar".
    - R-4.4 — No OS native notification is fired for `reminder_approaching` items (tray only).
  - verify:
    - With a vault file having `reminder_date: <today>`: Squirrel tray menu shows "Reminder due" section with the item.
    - With `reminder_date: <3 days from now>`: tray shows "On your radar" section; no OS banner fired.

- [ ] **3.2** Fire OS notifications for `reminder_active` items in `tray_alerts.rs` (deps: 3.1, est: ~20m)
  - acceptance:
    - R-4.3 — `reminder_active` items are included in OS native notification banners on the same `NOTIF_INTERVAL` (120 s), `ITEM_COOLDOWN` (3600 s), and `MAX_DIALOGS_PER_DAY` (8) guards as pressing items.
  - verify:
    - Create a vault file with `reminder_date: <yesterday>`. Within 2 minutes of launching Squirrel, an OS notification banner appears for that item.
    - Confirm the same item does not fire again within 1 hour (cooldown respected).

---

## Unit 4: Web UI Widget

- [x] **4.1** Add `RemindersWidget` to the desktop web UI (`apps/backend/app/src/`) with Dismiss and Snooze controls (deps: 2.1, 2.2, est: ~60m)
  - acceptance:
    - R-4.5 — A `RemindersWidget` component displays `approaching` and `active` lists.
    - R-4.6 — Clicking **Dismiss** calls `PATCH /api/reminder/<id>/dismiss`; item removed from list immediately (optimistic update).
    - R-4.7 — Clicking **Snooze** prompts for a new date, calls `PATCH /api/reminder/<id>/snooze`; item removed from active list immediately.
  - verify:
    - With `reminder_date: <today>`: widget shows item in "Reminder due" section.
    - Click Dismiss → item disappears; re-load page → item still gone; inspect vault file → `reminder_dismissed` present.
    - Click Snooze → date prompt appears → pick 30 days out → item disappears from active; inspect file → `reminder_snoozed_until` present.

---

## Unit 5: Scratch Pad Project

- [x] **5.1** Add `ensure_scratch_pad(vault_path)` to `apps/cli/lib/new_project_writer.py` and call it at server startup (est: ~30m)
  - acceptance:
    - R-5.1 — On every server start, the function checks for `01-Proyectos-Activos/SCRATCH-PAD/`.
    - R-5.2 — If absent, creates the project with `tipo: C`, `protected: true`, bypassing the WIP cap (`force=True`).
    - R-5.3 — `protected: true` is present in `SCRATCH-PAD/SCRATCH-PAD.md` YAML frontmatter.
    - R-5.5 — SCRATCH-PAD counts toward WIP cap in all capacity checks (no special exemption added).
  - verify:
    - Delete `SCRATCH-PAD/` from the vault. Restart `server.py`. Confirm the directory and `SCRATCH-PAD.md` are recreated with `protected: true` in frontmatter.
    - Restart server again with `SCRATCH-PAD/` present — no error, no duplicate creation.

- [x] **5.2** Add HTTP 403 guard for `protected: true` projects in the delete handler of `server.py` (deps: 5.1, est: ~15m)
  - acceptance:
    - R-5.4 — Any DELETE request targeting a project whose frontmatter has `protected: true` returns HTTP 403 and `{"error": "PROJECT_PROTECTED"}`.
  - verify:
    - `curl -X DELETE http://127.0.0.1:3939/api/projects/SCRATCH-PAD` → HTTP 403, body `{"error": "PROJECT_PROTECTED"}`.
    - Delete a non-protected project → succeeds as before (no regression).
