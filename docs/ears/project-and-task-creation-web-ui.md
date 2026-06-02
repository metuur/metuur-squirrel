# Project & Task Creation from Web UI — EARS Specifications

## Unit 1: Project Creation Form

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN the user submits the New Project form with a valid `tag` and `type`, THE SYSTEM SHALL call `POST /api/projects` with all provided fields and navigate to the new project page on success. |
| R-1.2 | WHEN the optional fields `deadline`, `stakeholders`, `description`, `first_intent_tag`, or `first_intent_title` are filled, THE SYSTEM SHALL include them in the `POST /api/projects` request payload. |
| R-1.3 | IF `tag` does not match `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`, THE SYSTEM SHALL display an inline validation error on the `tag` field and block form submission without making a network call. |
| R-1.4 | IF `type` is not one of `A`, `B`, or `C`, THE SYSTEM SHALL display an inline validation error on the `type` field and block form submission. |
| R-1.5 | IF `first_intent_tag` is filled and `first_intent_title` is empty, THE SYSTEM SHALL display an inline validation error on `first_intent_title` and block form submission. |
| R-1.6 | WHEN `POST /api/projects` returns a non-2xx response, THE SYSTEM SHALL display the backend error message inline in the form and retain all entered field values. |
| R-1.7 | WHEN `POST /api/projects` succeeds, THE SYSTEM SHALL navigate to the newly created project's page within the SPA. |

## Unit 2: Standalone Intent (Task) Creation

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL expose a `POST /api/intents` endpoint that accepts `project_slug`, `tag`, `title`, and optionally `description` and `deadline`. |
| R-2.2 | WHEN `POST /api/intents` is called, THE SYSTEM SHALL resolve the vault path via the `squirrel_vault` cookie and validate it with `is_path_inside()` before writing any file. |
| R-2.3 | IF the project directory `<vault>/01-Proyectos-Activos/<project_slug>/` does not exist, THE SYSTEM SHALL return HTTP 404. |
| R-2.4 | IF a file `<project_dir>/<tag>.md` already exists, THE SYSTEM SHALL return HTTP 409 without overwriting the existing file. |
| R-2.5 | WHEN all validations pass, THE SYSTEM SHALL render `agent-pack/templates/intent.md` with the supplied fields and write the result to `<vault>/01-Proyectos-Activos/<project_slug>/<tag>.md`, then return HTTP 201 with the new file's relative vault path. |
| R-2.6 | IF `tag` does not match `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`, THE SYSTEM SHALL return HTTP 422. |

## Unit 3: Task Creation Form (Project Page)

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN the user is on a project page and clicks "New Task", THE SYSTEM SHALL display a task creation form pre-scoped to that project (`project_slug` inferred from the current page context). |
| R-3.2 | WHEN the user submits the task creation form with a valid `tag` and `title`, THE SYSTEM SHALL call `POST /api/intents` with the project slug and form fields. |
| R-3.3 | WHEN `POST /api/intents` returns 201, THE SYSTEM SHALL add the new task to the project's task list (via re-fetch or optimistic update) and close the form. |
| R-3.4 | WHEN `POST /api/intents` returns an error, THE SYSTEM SHALL display the error inline in the task form and retain all entered field values. |
| R-3.5 | IF `tag` does not match `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`, THE SYSTEM SHALL display an inline client-side validation error on the `tag` field and block submission. |

## Unit 4: Cross-Context Task Creation Routing

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the user triggers "New Task" from outside a project page, THE SYSTEM SHALL display a project-selector listing all active projects before showing the task form. |
| R-4.2 | WHEN the user selects a project from the selector, THE SYSTEM SHALL navigate to that project's page and automatically open the task creation form. |
| R-4.3 | THE SYSTEM SHALL pass the intent to open the task form via a URL query parameter (e.g. `?newTask=true`) or equivalent router state, so the project page can open the form on mount without additional user interaction. |
