# Quick Tasks — Focus Stack — EARS Specifications

Keywords: `THE SYSTEM SHALL` (always-on) · `WHEN <trigger>` (event) ·
`WHILE <state>` (continuous) · `IF <condition>` (conditional/gate) ·
`WHERE <context>` (scoped).

## Unit 1: Capture

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN the user activates an Add Quick Task surface (global shortcut `Ctrl+Cmd+Q`, tray menu item, or web-UI button), THE SYSTEM SHALL open a single one-line capture box focused for text entry. |
| R-1.2 | WHEN the user submits non-empty text from the capture box, THE SYSTEM SHALL create a `QT-NNN.md` file in `01-Active-Projects/SCRATCH-PAD/` with `type: quick_task`, `quick_task: true`, `qt_state: active`, `qt_created_at` set to the current timestamp, and `qt_snooze_count: 0`. |
| R-1.3 | WHEN the user submits empty or whitespace-only text, THE SYSTEM SHALL reject the capture and keep the box open without creating a file. |
| R-1.4 | WHEN a Quick Task is created via the global shortcut, THE SYSTEM SHALL return keyboard focus to the previously active application after submission or cancellation. |
| R-1.5 | THE SYSTEM SHALL route all three capture surfaces through the same `POST /api/quick-tasks` endpoint and the same capture box. |
| R-1.6 | WHERE the global shortcut `Ctrl+Cmd+Q` cannot be registered (already held by another app), THE SYSTEM SHALL log the failure and continue running, leaving the tray and web-UI capture surfaces functional. |
| R-1.7 | THE SYSTEM SHALL allocate Quick Task ids sequentially as `QT-NNN` using the existing numbering helper, with no id reuse across the existing files in `SCRATCH-PAD`. |

## Unit 2: Stack ordering & the hard cap

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL treat the Quick Task Stack as a FIFO queue ordered ascending by `qt_created_at`, with the oldest active task at the top and the newest appended at the bottom. |
| R-2.2 | THE SYSTEM SHALL define the active count as the number of `quick_task: true` files in `SCRATCH-PAD` whose `qt_state == active`. |
| R-2.3 | IF a create request arrives WHILE the active count equals 5, THE SYSTEM SHALL reject it with HTTP 409 and body `{"error":"QUICK_TASK_LIMIT_REACHED"}` and SHALL NOT create a file. |
| R-2.4 | WHEN a create is rejected for the cap, THE SYSTEM SHALL keep the capture box open and display guidance to complete, delete, or snooze an existing Quick Task first. |
| R-2.5 | WHILE the active count is below 5, THE SYSTEM SHALL accept new Quick Tasks. |
| R-2.6 | THE SYSTEM SHALL exclude tasks with `qt_state == snoozed` and `qt_state == done` from the active count. |
| R-2.7 | THE SYSTEM SHALL surface the stack as oldest-first in every view (API list, tray section, and web widget). |

## Unit 3: Complete, delete, snooze

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN the user completes a Quick Task, THE SYSTEM SHALL set its `qt_state: done` and `status: done`, removing it from the active stack and freeing a slot. |
| R-3.2 | WHEN the user deletes a Quick Task, THE SYSTEM SHALL remove its file from `SCRATCH-PAD` and free a slot. |
| R-3.3 | WHEN the user snoozes a Quick Task, THE SYSTEM SHALL set `qt_state: snoozed`, set `qt_snoozed_until` to the resolved wake time, increment `qt_snooze_count`, and remove it from the active count. |
| R-3.4 | THE SYSTEM SHALL resolve snooze duration inputs `"15m"`, `"1h"` (default), and `"next_block"` (against the AM/PM focus boundaries) to an absolute wake timestamp. |
| R-3.5 | IF a snooze request arrives WHILE the task's `qt_snooze_count` is already at the maximum (2), THE SYSTEM SHALL reject it with HTTP 409 and body `{"error":"QUICK_TASK_SNOOZE_LIMIT"}`, requiring the user to complete or delete it instead. |
| R-3.6 | WHEN a slot is freed by completing, deleting, or snoozing, THE SYSTEM SHALL permit the next create immediately. |

## Unit 4: Snooze return (wake)

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHILE a Quick Task is snoozed and its `qt_snoozed_until` is in the future, THE SYSTEM SHALL keep it out of the active stack and out of the active count. |
| R-4.2 | WHEN a snoozed task's `qt_snoozed_until` has passed AND the active count is below 5, THE SYSTEM SHALL reactivate it by setting `qt_state: active`, clearing `qt_snoozed_until`, and re-stamping `qt_created_at` to the current time so it re-enters at the bottom of the stack. |
| R-4.3 | IF a snoozed task is due to return WHILE the active count equals 5, THE SYSTEM SHALL keep it snoozed, SHALL NOT exceed the cap, and SHALL flag it as ready-to-return (`return_blocked`). |
| R-4.4 | THE SYSTEM SHALL perform wake evaluation deterministically at scan time within the `GET /api/quick-tasks` and `GET /api/home` handlers, processing due tasks in ascending `qt_snoozed_until` order until the cap is reached. |
| R-4.5 | THE SYSTEM SHALL keep snoozed tasks visible (in a snoozed section) rather than hidden, so the user always sees the full set of parked items. |

## Unit 5: Surfacing

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | WHILE at least one active Quick Task exists, THE SYSTEM SHALL show a Quick Tasks badge/section in the tray with the active count. |
| R-5.2 | WHILE at least one active Quick Task exists, THE SYSTEM SHALL surface the oldest active task as a low-key in-app notification via the existing notification center, governed by the existing per-item cooldown (3600s) and daily-dialog cap (8). |
| R-5.3 | THE SYSTEM SHALL render an always-visible Quick Task widget in the web UI showing the full stack oldest-first, with complete, snooze, and delete controls and an Add button. |
| R-5.4 | WHILE the active count equals 5, THE SYSTEM SHALL present the Add control in a disabled state with guidance to clear a slot first. |
| R-5.5 | WHEN a Quick Task is `return_blocked`, THE SYSTEM SHALL surface a single "a snoozed quick task is ready — clear a slot" nudge on the existing cooldown. |
| R-5.6 | THE SYSTEM SHALL NOT change the existing OS-notification setting or sound behavior; Quick Task surfacing rides the existing in-app notification channel. |

## Unit 6: Isolation & invariants

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE SYSTEM SHALL exclude `type: quick_task` files from the intent, deadline, focus, reminder, and project-WIP scanners. |
| R-6.2 | THE SYSTEM SHALL NOT let Quick Tasks affect focus picking, AM/PM scheduling, deadlines, or the project WIP cap. |
| R-6.3 | THE SYSTEM SHALL perform every Quick Task write atomically (temp file + `os.replace()`), consistent with existing vault writers. |
| R-6.4 | THE SYSTEM SHALL resolve every Quick Task write target within `SCRATCH-PAD` only, never elsewhere in the vault. |
| R-6.5 | THE SYSTEM SHALL leave all existing `SCRATCH-PAD` behavior (protection from deletion, WIP counting as a project, reminders) unchanged. |
| R-6.6 | THE SYSTEM SHALL read the live active count immediately before any cap-gated write, never a stale cached count. |
