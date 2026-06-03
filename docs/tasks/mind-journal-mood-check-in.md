# Mind Journal & 4-Hour Mood Check-In — Tasks

Source specs: `docs/hld/mind-journal-mood-check-in.md`, `docs/lld/mind-journal-mood-check-in.md`, `docs/ears/mind-journal-mood-check-in.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Dependency layers:
```
1.1 (mind_journal.py skeleton + find_journal by marker)
       │
       ├──► 1.2 (ensure_mind_journal seeding + vault-state flag)
       │
       └──► 2.1 (compute_due / next_due + waking window)
                  │
        ┌─────────┴───────────────────────────────┐
       3.1 (GET /api/journal)                    3.3 (PATCH /api/journal/config)
        │                                          │
       3.2 (POST /api/journal/entry append)        │
        │                                          │
       3.4 (extend GET /api/home)                  │
        │                                          │
   ┌────┴───────────────┐                          │
  4.1 (tray + native     5.1 (entry UI form + list)─┘
       notification)
```

---

## Unit 1: Mind Journal Task Seeding

- [x] **1.1** Create `apps/cli/lib/mind_journal.py` skeleton + `find_journal()` (est: ~30m)
  - acceptance:
    - R-2.1 — `find_journal(vault_path)` locates the journal task by frontmatter marker `journal: true`, not by filename; returns the file path or `None`.
    - Module reuses `intent_parser` (`parse_frontmatter`, `write_frontmatter`, `_DELETE`) and the atomic `tmp → os.replace` write pattern from `reminder_writer.py`.
  - verify: Pytest — fixture vault with a `journal: true` file under SCRATCH-PAD returns its path; renamed file still found; vault with no marker returns `None`.

- [x] **1.2** Implement `ensure_mind_journal()` seeding with vault-state flag (deps: 1.1, est: ~40m)
  - acceptance:
    - R-1.1 — At server start, reads `mind_journal_seeded` from vault state JSON.
    - R-1.2 — IF flag absent/false, creates `01-Proyectos-Activos/SCRATCH-PAD/MIND-JOURNAL.md` with frontmatter `id: MIND-JOURNAL`, `type: C`, `status: wip`, `project: SCRATCH-PAD`, `journal: true`, `reminder_interval_hours: 4`, `waking_start: "08:00"`, `waking_end: "22:00"`, `reminder_last_logged: <creation ts>`.
    - R-1.3 — Body renders a `## Entries` heading and a line stating the task may be deleted anytime.
    - R-1.4 — On successful seed, sets `mind_journal_seeded: true` in vault state JSON.
    - R-1.5 — IF flag true, does NOT create the task even when none exists.
    - R-1.6 — No `protected` field written.
    - R-1.8 — Seeding failure is logged; server still starts.
  - verify: Pytest — fresh vault seeds the file + sets flag; second call with flag=true is a no-op; deleting the file then calling again does not recreate it; forced write error is caught and logged.

- [x] **1.3** Wire `ensure_mind_journal` into server startup + confirm delete is unguarded (deps: 1.2, est: ~20m)
  - acceptance:
    - R-1.1 — `server.py` calls `ensure_mind_journal` at the same startup point as `ensure_scratch_pad` (`_ensure_scratch_pad_once` / startup path).
    - R-1.7 — A delete request targeting `MIND-JOURNAL` uses the existing task delete flow and does NOT return HTTP 403 (only `protected: true` triggers 403; journal has none).
  - verify: Start server against fresh vault → file present. Delete via existing delete endpoint → HTTP 2xx, file gone. Restart → not recreated.

---

## Unit 2: Recurrence & Due Computation

- [x] **2.1** Implement `compute_due()` / `next_due` with waking window (deps: 1.1, est: ~45m)
  - acceptance:
    - R-2.2 — `reminder_interval_hours` is the interval, defaulting to 4 when absent/unparseable.
    - R-2.3 — Next boundary = `reminder_last_logged + interval`, falling back to `created` then now.
    - R-2.4 — Waking window = `[waking_start, waking_end]` local wall-clock, defaulting `08:00`–`22:00`.
    - R-2.5 — `due` is true WHEN now ≥ boundary AND now's time-of-day is within the window.
    - R-2.6 — `due` is false WHILE outside the waking window, regardless of boundary.
    - R-2.7 — IF boundary falls outside the window, `next_due` reported as next `waking_start`.
    - R-2.8 — Computed at request time; no background scheduler.
  - verify: Pytest with injectable `now` — last=10:00/interval=4: not due at 13:00, due at 14:00; boundary at 03:00 → not due, `next_due` = next 08:00; missing fields fall back to defaults.

---

## Unit 3: Journal API

- [x] **3.1** `GET /api/journal` (deps: 2.1, est: ~30m)
  - acceptance:
    - R-3.1 — Returns `{ task:{id,title,path}, entries:[...], due, next_due, interval_hours, waking:{start,end} }`.
    - R-3.2 — IF no journal task, returns `{ "exists": false }` HTTP 200 and does NOT recreate it.
    - R-3.11 — Entries returned in chronological order (oldest first).
  - verify: curl against seeded vault returns full shape with `due`/`next_due`; after deleting the task, returns `{"exists": false}` and no file is recreated.

- [x] **3.2** `POST /api/journal/entry` — append + advance clock (deps: 3.1, est: ~40m)
  - acceptance:
    - R-3.3 — Accepts `{ mind, doing, mood }`.
    - R-3.4 — Invalid `mood` → HTTP 400 `{"error":"INVALID_MOOD"}`.
    - R-3.5 — Appends `### <YYYY-MM-DD HH:MM> · <emoji> <mood>` + `**Mind:** …` + `**Doing:** …` under `## Entries`.
    - R-3.6 — Sets `reminder_last_logged` to now → `due` resets to false.
    - R-3.7 — No journal task → HTTP 404 `{"error":"NO_JOURNAL"}`.
    - R-3.11 — Append-only; existing entries untouched.
  - verify: POST happy/neutral/sad each append correctly; bad mood → 400; subsequent `GET /api/journal` shows `due:false` and the new entry last; delete task then POST → 404.

- [x] **3.3** `PATCH /api/journal/config` (deps: 2.1, est: ~25m)
  - acceptance:
    - R-3.8 — Accepts `{ interval_hours?, waking_start?, waking_end? }`; upserts provided fields into frontmatter.
    - R-3.9 — Non-positive `interval_hours` or time not matching `HH:MM` → HTTP 400.
  - verify: PATCH interval_hours=6 → `GET /api/journal` shows `interval_hours:6` and shifted `next_due`; PATCH waking_start="07:00" persists; invalid values → 400.

- [x] **3.4** Extend `GET /api/home` with `journal` block (deps: 3.1, est: ~15m)
  - acceptance:
    - R-3.10 — `/api/home` includes `journal: { due, next_due }`; omitted or `due:false` when no journal task exists.
  - verify: `GET /api/home` includes `journal.due`/`journal.next_due`; after deleting task, `due:false` (or block omitted) and existing home fields unchanged.

---

## Unit 4: Tray & Notification Surface

- [x] **4.1** Tray item + native notification, waking-window gated (deps: 3.4, est: ~45m)
  - acceptance:
    - R-4.1 — WHILE `due`, tray shows "Mind Journal — check in".
    - R-4.2 — WHILE `due`, fires a native notification with the two prompts, under existing `NOTIF_INTERVAL` / `ITEM_COOLDOWN` / `MAX_DIALOGS_PER_DAY` guards.
    - R-4.3 — Outside the waking window, NO journal native notification fires.
    - R-4.4 — Activating the tray item / notification opens the web UI to the journal entry form.
    - R-4.5 — Journal task never appears in the one-shot reminder buckets ("On your radar" / "Reminder due").
  - verify: With `due:true` in window → tray item + banner appear once per cadence; force time outside window → no banner; click opens journal form; confirm `reminder_scanner` output excludes MIND-JOURNAL (no `reminder_date`).

---

## Unit 5: Journal Entry UI

- [x] **5.1** Journal check-in form + entries list (deps: 3.2, 3.3, est: ~50m)
  - acceptance:
    - R-5.1 — Form has "What is your mind thinking right now?" field, "What are you doing right now?" field, and a happy/neutral/sad mood selector.
    - R-5.2 — Submit calls `POST /api/journal/entry`; on success clears the form and shows the new entry at the bottom.
    - R-5.3 — Existing entries shown chronologically with mood indicator.
    - R-5.4 — WHEN `due`, journal is visually flagged; WHEN not, shows `next_due` time.
    - R-5.5 — Interval + waking-window controls wired to `PATCH /api/journal/config`.
  - verify: Browser — submit an entry appends it and clears the form; mood indicator renders; due-state flag toggles after submit; changing interval via the control updates `next_due`.
```
