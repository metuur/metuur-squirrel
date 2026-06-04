# Quick Tasks — Focus Stack — Tasks

Source specs: `docs/hld/quick-tasks-focus-stack.md`, `docs/lld/quick-tasks-focus-stack.md`, `docs/ears/quick-tasks-focus-stack.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Dependency layers (LLD build sequence: lib → API → capture → tray → web):
```
A.1 (quick_task_scanner.py)   A.2 (writer: create + cap)
        │                          │
        │                   ┌──────┼───────┬──────────┐
        │                  A.3    A.4      A.5         │
        │            (complete/  (snooze) (activate/   │
        │             delete)             wake write)  │
        └──────────────┬───────────┴────────┘
                       │
        ┌──────────────┼───────────┬───────────┬───────────┐
       B.1            B.2          B.3         B.4         B.5
   (GET + wake)   (POST create) (complete/  (PATCH      (/api/home
        │              │          delete)    snooze)     extend)
        │              │            │           │           │
        │         ┌────┴────┐       │           │           │
        │        C.1       C.2 ─── C.3          │           │
        │     (shortcut) (modal)  (tray add)    │           │
        │                                       │           │
   ┌────┴───────────────┬──────────────┐        │      ┌────┴────┐
  E.1                  E.2            E.3        │     D.1  D.2  D.3
 (widget render)   (add/disabled)  (refetch)    │   (tray (notif)(blocked
        └──────────────────────────────────────-┘    section)     nudge)

F.1 (scanner isolation check) — after A.2, independent of API/UI
```

---

## Unit A: Backend lib — writer & scanner

- [x] **A.1** Write `apps/cli/lib/quick_task_scanner.py` (est: ~40m)
  - acceptance:
    - R-2.1 / R-2.7 — `scan(vault_path)` returns `active[]` sorted ascending by `qt_created_at` (oldest first).
    - R-2.2 — Defines `active_count` as count of `quick_task: true` files in `SCRATCH-PAD` with `qt_state == active`.
    - R-2.6 — Tasks with `qt_state` in `snoozed`/`done` are excluded from `active` and from `active_count`.
    - R-4.1 / R-4.5 — Snoozed tasks returned in a `snoozed[]` bucket (kept visible), each flagged `wake_due` = (`qt_snoozed_until <= now`).
  - verify:
    - Pytest with fixture `QT-*.md` files: active×3 (distinct `qt_created_at`), snoozed-future, snoozed-expired, done.
    - Assert `active` is sorted oldest-first, `active_count == 3`, snoozed-expired carries `wake_due: true`, done excluded entirely.

- [x] **A.2** Write `apps/cli/lib/quick_task_writer.py` — create + hard cap (deps: A.1, est: ~40m)
  - acceptance:
    - R-1.2 / R-1.7 — `create_quick_task(vault_path, text)` allocates `QT-NNN` via `_next_number(folder, "QT-")` and writes frontmatter `type: quick_task`, `quick_task: true`, `qt_state: active`, `qt_created_at: now`, `qt_snooze_count: 0`, `status: open` + body callout.
    - R-2.3 / R-2.5 — Raises `QuickTaskError("QUICK_TASK_LIMIT_REACHED")` when `active_count == 5`; succeeds when `< 5`.
    - R-6.3 / R-6.4 — Write is atomic (temp + `os.replace()`) and target resolves under `SCRATCH-PAD` only.
    - R-6.6 — Re-reads live active count immediately before the cap check (no cached count).
  - verify:
    - Pytest: create into an empty stack → file exists with expected frontmatter; create when 5 active → raises `QUICK_TASK_LIMIT_REACHED`, no 6th file written.
    - Assert two sequential creates get distinct, non-reused `QT-NNN` ids.

- [x] **A.3** Writer — `complete_quick_task` / `delete_quick_task` (deps: A.2, est: ~20m)
  - acceptance:
    - R-3.1 — `complete_quick_task(path)` sets `qt_state: done` and `status: done` (slot freed).
    - R-3.2 — `delete_quick_task(path)` removes the file (slot freed).
    - R-3.6 — After either, `quick_task_scanner` reports `active_count` decreased by one.
  - verify:
    - Pytest: with 5 active, complete one → `active_count == 4`; delete one → file gone, `active_count == 3`.

- [x] **A.4** Writer — `snooze_quick_task` + `resolve_snooze_until` (deps: A.2, est: ~30m)
  - acceptance:
    - R-3.3 — Sets `qt_state: snoozed`, `qt_snoozed_until`, increments `qt_snooze_count`; removed from active count.
    - R-3.4 — `resolve_snooze_until` maps `"15m"`, `"1h"` (default), `"next_block"` (AM/PM focus boundary) → absolute ISO timestamp; bare ISO passes through.
    - R-3.5 — Raises `QuickTaskError("QUICK_TASK_SNOOZE_LIMIT")` when `qt_snooze_count >= 2`.
  - verify:
    - Pytest: snooze once → state snoozed, count 1, `active_count` down by one; snooze a task already at count 2 → raises `QUICK_TASK_SNOOZE_LIMIT`.
    - Assert `resolve_snooze_until("1h")` ≈ now + 3600s; `"next_block"` resolves to the next AM/PM boundary.

- [x] **A.5** Writer — `activate_quick_task` (wake re-stamp) (deps: A.2, est: ~15m)
  - acceptance:
    - R-4.2 — Sets `qt_state: active`, deletes `qt_snoozed_until`, re-stamps `qt_created_at = now` so the task sorts to the bottom of the FIFO stack.
  - verify:
    - Pytest: activate a snoozed task whose original `qt_created_at` is oldest → after activate it has the newest `qt_created_at` and `qt_snoozed_until` is absent.

## Unit B: Backend API — `server.py`

- [x] **B.1** `GET /api/quick-tasks` + capacity-aware wake-commit (deps: A.1, A.5, est: ~35m)
  - acceptance:
    - R-2.1 / R-2.7 — Returns `{ active, snoozed, active_count, limit: 5 }` with `active` oldest-first.
    - R-4.4 — Processes `wake_due` snoozed tasks ascending by `qt_snoozed_until`, activating while `active_count < 5`.
    - R-4.2 — Each activated task re-enters at the bottom (via A.5).
    - R-4.3 / R-4.5 — Still-due tasks that cannot fit stay `snoozed`, are returned with `return_blocked: true`, and never push active past 5.
  - verify:
    - Pytest (mirror `test_web_ui_json_api.py`): 4 active + 1 expired-snoozed → GET returns 5 active, expired one at bottom; 5 active + 1 expired-snoozed → GET returns 5 active + snoozed with `return_blocked: true`.

- [x] **B.2** `POST /api/quick-tasks` (deps: A.2, est: ~25m)
  - acceptance:
    - R-1.2 / R-1.5 — Creates a Quick Task from `{ text }`; returns `201` + new id.
    - R-1.3 — Empty/whitespace text → `400`, no file written.
    - R-2.3 / R-2.4 — At cap → `409 {"error":"QUICK_TASK_LIMIT_REACHED"}`.
  - verify:
    - Pytest: POST valid text → 201, file exists; POST `"  "` → 400; POST when 5 active → 409 with the exact error code.

- [x] **B.3** `PATCH …/complete` + `DELETE …/:id` (deps: A.3, est: ~20m)
  - acceptance:
    - R-3.1 — `PATCH /api/quick-task/<id>/complete` marks done, frees slot.
    - R-3.2 — `DELETE /api/quick-task/<id>` removes file, frees slot.
    - R-3.6 / R-6.4 — Both resolve `<id>` under `SCRATCH-PAD` only and invalidate the home cache.
  - verify:
    - Pytest: complete then GET → task absent from active, `active_count` reduced; delete then GET → same; unknown id → 404.

- [x] **B.4** `PATCH …/snooze` (deps: A.4, est: ~20m)
  - acceptance:
    - R-3.3 / R-3.4 — Body `{ until? }` (default `"1h"`); snoozes and frees slot.
    - R-3.5 — Past snooze limit → `409 {"error":"QUICK_TASK_SNOOZE_LIMIT"}`.
  - verify:
    - Pytest: snooze → GET shows it under `snoozed`, `active_count` reduced; snooze a count-2 task → 409 with the exact code.

- [x] **B.5** Extend `GET /api/home` with `quick_tasks` summary (deps: A.1, est: ~20m)
  - acceptance:
    - R-5.1 — Adds `quick_tasks: { active: [...top N], active_count, snoozed_count, oldest }`.
    - R-4.3 — Surfaces `return_blocked` when any due-snoozed task is waiting for a slot.
    - R-6.2 — Adding this section does not alter existing `/api/home` fields.
  - verify:
    - Pytest: snapshot existing `/api/home` keys unchanged; with 2 active + 1 blocked snoozed, `quick_tasks.active_count == 2`, `oldest` is the top task, `return_blocked` present.

## Unit C: Capture surfaces (Tauri + frontend)

- [x] **C.1** Register `Ctrl+Cmd+Q` global shortcut in `lib.rs` (deps: B.2, est: ~30m)
  - acceptance:
    - R-1.1 / R-1.4 — On press, shows+focuses the window (reusing the `Ctrl+Cmd+S` activation path) and emits Tauri event `quick-task://capture-open`; focus returns to the prior app on close.
    - R-1.6 — If the shortcut cannot be registered, log and continue; other capture surfaces stay functional.
  - verify:
    - `cargo build` succeeds; manual: press `Ctrl+Cmd+Q` from another app → Squirrel window appears and the capture modal opens; check log line on registration.

- [x] **C.2** Capture modal + `useQuickTaskCapture` hook (deps: C.1, est: ~40m)
  - acceptance:
    - R-1.1 / R-1.3 — Minimal one-line input, Enter submits to `POST /api/quick-tasks`, Esc cancels; empty input is rejected client-side.
    - R-2.4 — On `409`, the modal stays open and shows "Stack is full — complete, delete, or snooze one first."
  - verify:
    - Vitest (mirror `useNotifications.test.ts`): event `quick-task://capture-open` opens modal; submit calls POST; 409 keeps modal open with the message. Manual: capture a task end-to-end.

- [x] **C.3** Tray menu "➕ Add Quick Task" item (deps: C.2, est: ~20m)
  - acceptance:
    - R-1.1 / R-1.5 — Tray item shows+focuses the window and opens the same capture modal via the same event/path.
  - verify:
    - Manual: tray → Add Quick Task → modal opens and creates via the same endpoint as the shortcut.

## Unit D: Tray surfacing — `tray_alerts.rs`

- [x] **D.1** Deserialize `quick_tasks` + tray "QUICK TASKS (N)" section/badge (deps: B.5, est: ~30m)
  - acceptance:
    - R-5.1 / R-2.7 — Extend the home struct; while active > 0, render a "QUICK TASKS (N)" section (oldest-first) below PRESSING NOW / REMINDERS DUE and light the badge via `update_badge_and_emit`.
  - verify:
    - `cargo build`; manual: with active tasks, tray shows the section with the count and badge; empty → section hidden.

- [x] **D.2** Oldest active task → in-app notification on cooldown (deps: D.1, est: ~25m)
  - acceptance:
    - R-5.2 — Fire a low-key in-app notification for the oldest active task via `insert_notification_if_new` (source `quick_task`), governed by existing `ITEM_COOLDOWN` (3600s) and `MAX_DIALOGS_PER_DAY` (8).
    - R-5.6 — No change to OS-popup setting/sound behavior.
  - verify:
    - `cargo test` for the insert path; manual: oldest task appears in the in-app notification center within one poll; repeat within cooldown does not re-fire.

- [x] **D.3** `return_blocked` nudge (deps: D.1, est: ~15m)
  - acceptance:
    - R-4.3 / R-5.5 — When `quick_tasks.return_blocked` is set, surface a single "a snoozed quick task is ready — clear a slot" nudge on the existing cooldown.
  - verify:
    - Manual: with 5 active + 1 due-snoozed, the nudge appears once per cooldown and clears after a slot is freed.

## Unit E: Web UI — `QuickTaskWidget`

- [x] **E.1** `QuickTaskWidget` renders the stack with row controls (deps: B.1, B.3, B.4, est: ~45m)
  - acceptance:
    - R-5.3 / R-2.7 / R-4.5 — Always-visible widget renders `active` oldest-first (top emphasized) plus a visible `snoozed` section; each active row offers ✓ Complete · 💤 Snooze · ✕ Delete wired to the API.
  - verify:
    - Vitest (mirror `DeadlinesWidget.test.tsx`): renders ordered rows from mocked `/api/quick-tasks`; clicking Complete/Delete/Snooze calls the right endpoint. Manual: actions update the list.

- [x] **E.2** Add button + cap-disabled state + snooze options (deps: E.1, C.2, est: ~25m)
  - acceptance:
    - R-5.4 — `+ Add Quick Task` opens the capture modal; disabled with a "clear a slot first" tooltip while `active_count === 5`.
    - R-3.4 — Snooze control offers 15m / 1h / next block, passing `until` to the API.
  - verify:
    - Vitest: button disabled at 5 active; snooze menu sends the chosen `until`. Manual: add disabled at cap, re-enabled after completing one.

- [x] **E.3** Refetch on daemon Tauri event (deps: E.1, est: ~15m)
  - acceptance:
    - R-5.3 — Widget refetches `/api/quick-tasks` on the Tauri event emitted after each daemon poll (same pattern as `useNotifications`).
  - verify:
    - Vitest: emitting the event triggers a refetch. Manual: completing a task in tray reflects in the widget within one poll.

## Unit F: Isolation & invariants

- [x] **F.1** Verify existing scanners ignore `type: quick_task` (deps: A.2, est: ~20m)
  - acceptance:
    - R-6.1 / R-6.2 — Intent, deadline, focus, reminder, and project-WIP scanners exclude `QT-*.md` (`type: quick_task`).
    - R-6.5 — Existing `SCRATCH-PAD` behavior (delete protection, WIP-as-project, reminders) is unchanged.
  - verify:
    - Pytest: create `QT-*.md` in `SCRATCH-PAD`, then run each existing scanner over the vault and assert none surface the Quick Task; existing scanner tests still pass.
