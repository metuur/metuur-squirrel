# Web UI Recent-Activity (History) Page — EARS Specifications

> _Backfilled from the as-built `HistoryPage.tsx` + `api_history`._

## Unit 1: Backend — GET /api/history

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN `GET /api/history` is called, THE SYSTEM SHALL scan the active vault for `.md` files and return the 30 most recently modified, newest first. |
| R-1.2 | THE SYSTEM SHALL exclude files whose path contains any dot-prefixed (hidden) segment. |
| R-1.3 | THE SYSTEM SHALL exclude files inside the `05-Post-its` directory. |
| R-1.4 | THE SYSTEM SHALL classify a file as a `project` when its filename equals `<parentFolder>.md`, and as a `note` otherwise. |
| R-1.5 | THE SYSTEM SHALL return each entry with `kind`, `slug` (for projects), `note_id` (for notes), `title`, and `modified_at` (the file modification time). |
| R-1.6 | THE SYSTEM SHALL resolve a project entry's `title` via the project-title vocabulary, and a note entry's `title` from its filename stem. |

## Unit 2: Page rendering

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL render a "Recent activity" page listing the entries returned by `GET /api/history`, newest first. |
| R-2.2 | WHILE the list is loading and no data is yet available, THE SYSTEM SHALL show a skeleton placeholder. |
| R-2.3 | WHEN there is no recent activity, THE SYSTEM SHALL show an explicit "Nothing yet." empty state. |
| R-2.4 | THE SYSTEM SHALL link a project entry to `/projects/<slug>` and a note entry to `/notes/<note_id>`. |
| R-2.5 | THE SYSTEM SHALL show a relative "time ago" for each entry derived from its `modified_at`, and a kind-appropriate icon (folder for projects, document for notes). |
