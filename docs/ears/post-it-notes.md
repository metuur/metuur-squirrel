# Post-it Notes — EARS Specifications

## Unit 1: Storage model

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN a Post-it is created, THE SYSTEM SHALL write a Markdown file named `PI-NNN.md` (zero-padded, next free number) under `05-Post-its/` in the configured vault, creating the folder if absent, using an atomic temp-file-and-rename write. |
| R-1.2 | THE SYSTEM SHALL store Post-it frontmatter with keys `id`, `type: post_it`, `state` (`active` or `archived`), `color`, `label`, `pinned`, `created`, and `converted_to`, with the captured text as the body. |
| R-1.3 | THE SYSTEM SHALL NOT write `status`, `reminder_date`, or `due` keys into Post-it frontmatter. |
| R-1.4 | THE SYSTEM SHALL store board presentation state (x, y, rotation, z) only in the `post_it_layout` SQLite table in `~/.squirrel/state/squirrel.db`, keyed by vault and Post-it id, created idempotently at schema init. |
| R-1.5 | IF a Post-it has no `post_it_layout` row, THE SYSTEM SHALL place it at a deterministic, non-overlapping default position (grid slot from creation order, small jitter and rotation derived from its id). |
| R-1.6 | WHEN a Post-it is deleted, THE SYSTEM SHALL remove both its Markdown file and its `post_it_layout` row. |

## Unit 2: Backend API

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN `GET /api/post-its` is requested, THE SYSTEM SHALL return all active Post-its ordered pinned-first then newest-first, each with `id`, `text`, `color`, `label`, `pinned`, `state`, `created`, `converted_to`, and `layout` joined from the SQLite index. |
| R-2.2 | WHEN `GET /api/post-its?include=archived` is requested, THE SYSTEM SHALL additionally return archived Post-its. |
| R-2.3 | WHEN `POST /api/post-its` is received with non-empty `text` and optional `color` and `label`, THE SYSTEM SHALL create the Post-it and respond 201 with the created item; IF `text` is empty or missing, THE SYSTEM SHALL respond 400 without writing. |
| R-2.4 | WHEN `PATCH /api/post-it/{id}` is received with any of `text`, `color`, `label`, `pinned`, THE SYSTEM SHALL update those fields in the Markdown file. |
| R-2.5 | WHEN `PATCH /api/post-it/{id}/layout` is received with `x`, `y`, `rotation` and optional `z`, THE SYSTEM SHALL upsert the corresponding `post_it_layout` row without modifying the Markdown file. |
| R-2.6 | WHEN `PATCH /api/post-it/{id}/archive` or `PATCH /api/post-it/{id}/restore` is received, THE SYSTEM SHALL set `state` to `archived` or `active` respectively. |
| R-2.7 | WHEN `DELETE /api/post-it/{id}` is received, THE SYSTEM SHALL delete the Post-it per R-1.6. |
| R-2.8 | IF a Post-it id in any item route does not resolve to a file under `05-Post-its/`, THE SYSTEM SHALL respond 404. |
| R-2.9 | WHEN any Post-it mutation succeeds, THE SYSTEM SHALL invalidate the vault cache as existing note creation does. |

## Unit 3: Conversion

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN `POST /api/post-it/{id}/convert` is received with `target: quick_task`, THE SYSTEM SHALL create a Quick Task from the Post-it text via the existing Quick Task creation flow, including its active-cap behavior. |
| R-3.2 | WHEN `POST /api/post-it/{id}/convert` is received with `target: project_task` and a valid `project_slug`, THE SYSTEM SHALL create a task in that project via the existing intent-template creation flow. |
| R-3.3 | WHEN `POST /api/post-it/{id}/convert` is received with `target: project_note` and a valid `project_slug`, THE SYSTEM SHALL create a capture note in that project via the existing capture writer. |
| R-3.4 | WHEN conversion target creation succeeds, THE SYSTEM SHALL set the Post-it `state` to `archived`, record the new artifact reference in `converted_to`, and return that reference. |
| R-3.5 | IF conversion target creation fails, THE SYSTEM SHALL leave the Post-it unchanged and return the failure. |
| R-3.6 | IF `target` is `project_task` or `project_note` and `project_slug` is missing or unknown, THE SYSTEM SHALL respond 400 without creating anything. |

## Unit 4: Capture surfaces

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL show an "Add Post-it" item in the tray menu alongside "Add Quick Task". |
| R-4.2 | WHEN the tray "Add Post-it" item is selected, THE SYSTEM SHALL foreground the desktop popup and open the Post-it capture modal in-app, without opening the web UI. |
| R-4.3 | WHERE the desktop popup is open, THE SYSTEM SHALL provide a Post-it capture trigger alongside the existing capture actions that opens the same modal. |
| R-4.4 | WHEN text is submitted in the Post-it capture modal with an optionally selected color, THE SYSTEM SHALL create the Post-it via `POST /api/post-its`, confirm visually, and close the modal; IF the submitted text is empty, THE SYSTEM SHALL NOT submit. |
| R-4.5 | THE SYSTEM SHALL NOT register a new global keyboard shortcut for Post-it capture. |
| R-4.6 | WHERE the `/post-its` page is open, THE SYSTEM SHALL provide a composer that creates a Post-it with chosen text and color and shows the new card at its default position without a full page reload. |

## Unit 5: Post-it board (Web UI)

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL serve a `/post-its` route under the shared Web UI layout with a sidebar entry. |
| R-5.2 | WHEN `/post-its` loads, THE SYSTEM SHALL render every active Post-it as a sticky-note card showing its color, body text, optional corner label, and pin indicator, positioned and rotated per its layout. |
| R-5.3 | WHEN a card is dragged and dropped, THE SYSTEM SHALL persist the new position via the layout endpoint, and the position SHALL survive a page reload. |
| R-5.4 | WHILE a Post-it is pinned, THE SYSTEM SHALL render it above unpinned cards. |
| R-5.5 | WHEN a card is opened, THE SYSTEM SHALL offer editing of text, color, and label, plus pin/unpin, archive, delete, and convert actions, applied via the corresponding API endpoints. |
| R-5.6 | WHEN the user invokes convert on a card, THE SYSTEM SHALL let them choose Quick Task, project task, or project note (with a project picker for the latter two), and on success remove the card from the active wall. |
| R-5.7 | WHEN the archived view is toggled, THE SYSTEM SHALL show archived Post-its with restore and delete actions, and restoring SHALL return the card to the active wall. |
| R-5.8 | WHEN delete is invoked on a card, THE SYSTEM SHALL ask for in-app confirmation before calling the delete endpoint. |
| R-5.9 | THE SYSTEM SHALL render board typography with a locally bundled handwriting-style font with a `cursive` fallback, fetching no remote assets. |

## Unit 6: Search and isolation

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | WHEN a search query matches Post-it body text, THE SYSTEM SHALL include the Post-it in `/api/search` results classified as kind `post_it`. |
| R-6.2 | WHEN a search result of kind `post_it` is selected in the header, THE SYSTEM SHALL navigate to `/post-its` and highlight the matching card. |
| R-6.3 | THE SYSTEM SHALL exclude Post-it files from Quick Task scanning, reminder scanning, deadline scanning, project listings, and the `/api/home` payload. |
| R-6.5 | IF a Post-it id is requested via the note detail or note edit endpoints (`/api/notes/{id}`), THE SYSTEM SHALL respond 404 — Post-its are never resolvable or editable as notes. |
| R-6.6 | IF Quick Task conversion is rejected by the active cap, THE SYSTEM SHALL return a structured cap-full error and the Web UI SHALL present it as guidance (complete a Quick Task first), leaving the Post-it unchanged. |
| R-6.4 | WHILE Post-it files exist in the vault, existing note, project, journal, and focus behavior SHALL remain unchanged. |
