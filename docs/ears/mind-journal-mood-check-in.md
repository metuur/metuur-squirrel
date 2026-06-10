# Mind Journal & 4-Hour Mood Check-In — EARS Specifications

## Unit 1: Mind Journal Task Seeding

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN the backend server starts, THE SYSTEM SHALL check the vault state JSON for a `mind_journal_seeded` flag. |
| R-1.2 | IF `mind_journal_seeded` is absent or false, THE SYSTEM SHALL create a Mind Journal task at `01-Active-Projects/SCRATCH-PAD/MIND-JOURNAL.md` with frontmatter `id: MIND-JOURNAL`, `type: C`, `status: wip`, `project: SCRATCH-PAD`, `journal: true`, `reminder_interval_hours: 4`, `waking_start: "08:00"`, `waking_end: "22:00"`, and `reminder_last_logged` set to the creation timestamp. |
| R-1.3 | WHEN the Mind Journal task is created, THE SYSTEM SHALL render a `## Entries` heading in the body and an explanatory line stating the task may be deleted at any time. |
| R-1.4 | WHEN the Mind Journal task is successfully seeded, THE SYSTEM SHALL set `mind_journal_seeded: true` in the vault state JSON. |
| R-1.5 | IF `mind_journal_seeded` is true, THE SYSTEM SHALL NOT create a Mind Journal task at server start, even if no journal task exists in the vault. |
| R-1.6 | THE SYSTEM SHALL NOT write a `protected` field on the Mind Journal task. |
| R-1.7 | IF a delete request targets the Mind Journal task, THE SYSTEM SHALL delete it using the existing task delete flow without returning HTTP 403. |
| R-1.8 | IF seeding the Mind Journal task fails for any reason, THE SYSTEM SHALL log the failure and continue starting the server. |

---

## Unit 2: Recurrence & Due Computation

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL identify the Mind Journal task by the frontmatter marker `journal: true`, not by filename. |
| R-2.2 | THE SYSTEM SHALL treat `reminder_interval_hours` as the recurrence interval, defaulting to 4 when the field is absent or unparseable. |
| R-2.3 | THE SYSTEM SHALL compute the next check-in boundary as `reminder_last_logged + reminder_interval_hours`, falling back to `created` then to now when `reminder_last_logged` is absent. |
| R-2.4 | THE SYSTEM SHALL define the waking window as `[waking_start, waking_end]` local wall-clock times, defaulting to `08:00`–`22:00` when the fields are absent. |
| R-2.5 | WHEN the current time is at or past the next check-in boundary AND the current local time of day is within the waking window, THE SYSTEM SHALL classify the check-in as `due`. |
| R-2.6 | WHILE the current local time of day is outside the waking window, THE SYSTEM SHALL classify the check-in as not `due`, regardless of the boundary. |
| R-2.7 | IF the next check-in boundary falls outside the waking window, THE SYSTEM SHALL report `next_due` as the start of the next waking window rather than the raw boundary. |
| R-2.8 | THE SYSTEM SHALL compute `due` and `next_due` at request time and SHALL NOT run a background scheduler. |

---

## Unit 3: Journal API

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL expose `GET /api/journal` returning `{ task: {id, title, path}, entries: [...], due: bool, next_due: ISO, interval_hours: N, waking: {start, end} }`. |
| R-3.2 | IF no Mind Journal task exists (e.g. the user deleted it), `GET /api/journal` SHALL return `{ "exists": false }` with HTTP 200 and SHALL NOT recreate the task. |
| R-3.3 | THE SYSTEM SHALL expose `POST /api/journal/entry` accepting a body `{ mind: string, doing: string, mood: "happy"\|"neutral"\|"sad" }`. |
| R-3.4 | IF `mood` is not one of `happy`, `neutral`, `sad`, THE SYSTEM SHALL reject the request with HTTP 400 and body `{"error": "INVALID_MOOD"}`. |
| R-3.5 | WHEN `POST /api/journal/entry` succeeds, THE SYSTEM SHALL append a timestamped, mood-tagged entry under the `## Entries` heading in the journal task body, in the form `### <YYYY-MM-DD HH:MM> · <emoji> <mood>` followed by `**Mind:** <mind>` and `**Doing:** <doing>`. |
| R-3.6 | WHEN `POST /api/journal/entry` succeeds, THE SYSTEM SHALL set `reminder_last_logged` to the current timestamp in the task frontmatter, resetting `due` to false. |
| R-3.7 | IF `POST /api/journal/entry` is called when no Mind Journal task exists, THE SYSTEM SHALL return HTTP 404 with body `{"error": "NO_JOURNAL"}`. |
| R-3.8 | THE SYSTEM SHALL expose `PATCH /api/journal/config` accepting `{ interval_hours?: N, waking_start?: "HH:MM", waking_end?: "HH:MM" }` and SHALL upsert the provided fields into the task frontmatter. |
| R-3.9 | IF `PATCH /api/journal/config` receives an `interval_hours` that is not a positive number, or a waking time not matching `HH:MM`, THE SYSTEM SHALL reject the request with HTTP 400. |
| R-3.10 | THE SYSTEM SHALL extend `GET /api/home` to include `journal: { "due": bool, "next_due": ISO }`, omitting it or returning `due: false` when no journal task exists. |
| R-3.11 | THE SYSTEM SHALL append entries in chronological order (oldest first) and SHALL NOT modify or delete existing entries. |

---

## Unit 4: Tray & Notification Surface

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHILE the journal check-in is `due`, THE SYSTEM SHALL display a "Mind Journal — check in" item in the tray menu. |
| R-4.2 | WHILE the journal check-in is `due`, THE SYSTEM SHALL fire an OS native notification prompting "What is your mind thinking right now?" and "What are you doing right now?", subject to the existing `NOTIF_INTERVAL`, `ITEM_COOLDOWN`, and `MAX_DIALOGS_PER_DAY` guards. |
| R-4.3 | WHILE the current local time of day is outside the waking window, THE SYSTEM SHALL NOT fire any journal native notification. |
| R-4.4 | WHEN the user activates the journal tray item, THE SYSTEM SHALL open the journal entry form **in-app** (show the desktop window and open its in-app journal modal). THE DESKTOP APP SHALL NOT open the web UI for journaling. |
| R-4.5 | THE SYSTEM SHALL NOT include the Mind Journal task in the one-shot reminder buckets ("On your radar" / "Reminder due") produced by `reminder_scanner`. |
| R-4.6 | THE SYSTEM SHALL render a Mind Journal button in the desktop popup header that opens the in-app journal modal, and SHALL show a "due" indicator dot on it while the check-in is due. |

---

## Unit 5: Journal Entry UI

Two surfaces satisfy these requirements independently: the **web UI** page at `/journal`, and the **desktop popup** in-app `JournalModal` (the desktop app does its journaling in-app and never opens the web UI for it — see R-4.4).

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL render a journal check-in form with a free-text field for "What is your mind thinking right now?", a free-text field for "What are you doing right now?", and a mood selector offering happy, neutral, and sad. |
| R-5.2 | WHEN the user submits the form, THE SYSTEM SHALL call `POST /api/journal/entry` and, on success, clear the form and show the new entry at the bottom of the entries list. |
| R-5.3 | THE SYSTEM SHALL display the existing journal entries in chronological order with their mood indicator. |
| R-5.4 | WHEN the journal check-in is `due`, THE SYSTEM SHALL visually flag the journal as awaiting a check-in; WHEN not due, THE SYSTEM SHALL show the `next_due` time. |
| R-5.5 | THE SYSTEM SHALL expose controls to change the interval and waking window, wired to `PATCH /api/journal/config`. |
