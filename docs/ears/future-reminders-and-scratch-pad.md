# Future Reminders & Scratch Pad — EARS Specifications

## Unit 1: Reminder Field on Tasks and Captures

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN a user creates or edits a task (intent) or capture, THE SYSTEM SHALL accept an optional `reminder_date` input as either an absolute ISO date (`YYYY-MM-DD`) or a relative string (`"in 1 month"`, `"in 3 months"`, `"in 6 months"`, `"in 1 year"`). |
| R-1.2 | WHEN `reminder_date` is provided as a relative string, THE SYSTEM SHALL resolve it to an absolute ISO date before writing to disk. |
| R-1.3 | WHEN `reminder_date` is set on a file, THE SYSTEM SHALL write `reminder_date: YYYY-MM-DD` into the file's YAML frontmatter. |
| R-1.4 | WHEN `reminder_date` is set on a file, THE SYSTEM SHALL also render a visible callout block (`> 📅 **Reminder:** YYYY-MM-DD`) in the markdown body immediately below the title heading. |
| R-1.5 | WHEN `reminder_date` is removed or dismissed, THE SYSTEM SHALL remove the callout block from the markdown body. |
| R-1.6 | IF a file's YAML frontmatter lacks `reminder_date`, THE SYSTEM SHALL treat it as having no reminder (no error, no default). |

---

## Unit 2: Reminder Scanning

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL scan `reminder_date` fields across all `.md` files in `01-Proyectos-Activos` and `03-Areas` at request time, via a new `reminder_scanner.py` module. |
| R-2.2 | IF a file has `estado: done`, `estado: completado`, or `estado: archived`, THE SYSTEM SHALL exclude it from all reminder scans. |
| R-2.3 | IF a file has `reminder_dismissed` set to any non-empty value, THE SYSTEM SHALL exclude it from all reminder output permanently. |
| R-2.4 | IF a file has `reminder_snoozed_until` set to a future date, THE SYSTEM SHALL suppress its reminder until that date passes. |
| R-2.5 | WHEN `reminder_date` is today or in the past and no suppression applies (R-2.3, R-2.4), THE SYSTEM SHALL classify the item as `reminder_active`. |
| R-2.6 | WHEN `reminder_date` is between 1 and 7 calendar days in the future and no suppression applies, THE SYSTEM SHALL classify the item as `reminder_approaching`. |
| R-2.7 | THE SYSTEM SHALL NOT place any item in both a deadline urgency bucket and a reminder bucket simultaneously; the two scans are independent. |

---

## Unit 3: Reminder API

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL expose `GET /api/reminders` returning `{ "approaching": [...], "active": [...] }` where each entry contains at minimum: `id`, `title`, `path`, `reminder_date`, `proyecto`. |
| R-3.2 | THE SYSTEM SHALL extend `GET /api/home` to include `reminders: { "approaching_count": N, "active_count": N }` alongside existing fields. |
| R-3.3 | THE SYSTEM SHALL expose `PATCH /api/reminder/<id>/dismiss` which writes `reminder_dismissed: <today>` to the file's frontmatter and removes the body callout. |
| R-3.4 | THE SYSTEM SHALL expose `PATCH /api/reminder/<id>/snooze` which accepts a `{ "until": "YYYY-MM-DD" }` body, writes `reminder_snoozed_until: <date>` to the file's frontmatter, and updates the body callout to show the new date. |
| R-3.5 | WHEN `PATCH /api/reminder/<id>/snooze` is called, THE SYSTEM SHALL clear any existing `reminder_dismissed` field on the same file. |
| R-3.6 | THE SYSTEM SHALL extend task and capture creation endpoints to accept an optional `reminder_date` field (absolute or relative string). |

---

## Unit 4: Reminder Display — Desktop Tray & Widget

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL display `reminder_approaching` items in a tray menu section labeled **"On your radar"**, separate from and below the existing "PRESSING NOW" section. |
| R-4.2 | THE SYSTEM SHALL display `reminder_active` items in a tray menu section labeled **"Reminder due"**, separate from and below "On your radar". |
| R-4.3 | WHILE `reminder_active` items exist, THE SYSTEM SHALL include them in OS native notification banners on the same `NOTIF_INTERVAL`, `ITEM_COOLDOWN`, and `MAX_DIALOGS_PER_DAY` guards as pressing items. |
| R-4.4 | THE SYSTEM SHALL NOT fire OS native notification banners for `reminder_approaching` items; those appear in the tray menu only. |
| R-4.5 | THE SYSTEM SHALL display a `RemindersWidget` in the desktop web UI showing `approaching` and `active` lists with **Dismiss** and **Snooze** controls per item. |
| R-4.6 | WHEN the user clicks **Dismiss** on a reminder item in the widget, THE SYSTEM SHALL call `PATCH /api/reminder/<id>/dismiss` and remove the item from the widget immediately. |
| R-4.7 | WHEN the user clicks **Snooze** on a reminder item in the widget, THE SYSTEM SHALL prompt for a new date, call `PATCH /api/reminder/<id>/snooze`, and remove the item from the active list immediately. |

---

## Unit 5: Scratch Pad Project

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | WHEN the backend server starts, THE SYSTEM SHALL check whether a project with tag `SCRATCH-PAD` exists in `01-Proyectos-Activos`. |
| R-5.2 | IF no `SCRATCH-PAD` project exists at server start, THE SYSTEM SHALL create it automatically with `tipo: C`, `protected: true`, and a default description, bypassing the WIP cap. |
| R-5.3 | THE SYSTEM SHALL write `protected: true` in the `SCRATCH-PAD` project page's YAML frontmatter. |
| R-5.4 | IF a delete request targets any project whose frontmatter contains `protected: true`, THE SYSTEM SHALL reject the request with HTTP 403 and body `{"error": "PROJECT_PROTECTED"}`. |
| R-5.5 | THE SYSTEM SHALL count the `SCRATCH-PAD` project toward the WIP cap in all WIP capacity checks. |
| R-5.6 | THE SYSTEM SHALL accept tasks, notes, and captures assigned to `SCRATCH-PAD` using all existing creation flows without special-casing. |
| R-5.7 | THE SYSTEM SHALL allow the user to move items from `SCRATCH-PAD` to any other project using existing note/task move flows. |
