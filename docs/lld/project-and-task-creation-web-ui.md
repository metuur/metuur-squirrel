# Project & Task Creation from Web UI — Low-Level Design

## Architecture

### Backend changes

**New endpoint: `POST /api/intents`**

`apps/backend/server.py` — add a route alongside the existing project routes (near line 205).

Request body (JSON):
```json
{
  "project_slug": "<slug>",
  "tag": "<INTENT-TAG>",
  "title": "<title>",
  "description": "<optional>",
  "deadline": "<optional ISO date>"
}
```

Handler logic:
1. Resolve vault path via the existing `squirrel_vault` cookie (same pattern as all other write routes).
2. Validate `tag` against the same regexp used for project tags in `new_project_writer.py:57`.
3. Resolve the target project directory: `<vault>/01-Active-Projects/<project_slug>/`.
4. Return 404 if the project directory does not exist.
5. Check for a conflicting file `<project_dir>/<tag>.md` — return 409 if present.
6. Write the intent file by rendering `agent-pack/templates/intent.md` with the supplied fields.
7. Return 201 with the new intent's relative vault path.

No new writer module needed — the file write is simple enough to live in the handler directly (template substitution + `open(..., 'w')`).

---

### Frontend changes

**New Project form**

Location: a new page or modal reachable from the global nav / project list header (exact placement determined during implementation — a "+" button in the project list is the expected entry point).

Component: `apps/desktop/src/components/NewProjectModal.tsx` (or equivalent SPA page).

Fields (maps directly to `POST /api/projects` payload):
| Field | Type | Required | Validation |
|---|---|---|---|
| `tag` | text | yes | `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` (client-side, matches backend) |
| `type` | select: A / B / C | yes | one of three values |
| `deadline` | date | no | |
| `stakeholders` | text | no | |
| `description` | textarea | no | |
| `first_intent_tag` | text | no | same regexp as `tag` |
| `first_intent_title` | text | no | required if `first_intent_tag` is filled |

On success: navigate to the new project page.
On error: display backend error message inline; keep form data intact.

---

**New Task form — in project page**

Location: `apps/desktop/src/components/ProjectPage.tsx` (or equivalent) — "New Task" button that opens an inline form or modal.

Calls: `POST /api/intents`

Fields:
| Field | Type | Required |
|---|---|---|
| `tag` | text | yes |
| `title` | text | yes |
| `description` | textarea | no |
| `deadline` | date | no |

`project_slug` is inferred from the current project page context (URL param / component prop).

On success: append new task to the project's task list (optimistic or re-fetch).
On error: display inline.

---

**Project-selector routing for task creation outside project context**

When a "New Task" trigger exists outside a project page (e.g. a global action bar), it opens a `ProjectSelectorModal` that:
1. Lists active projects (fetched from `GET /api/projects` or local state).
2. On selection, navigates to `/<project_slug>` and passes a `?newTask=true` query param (or equivalent router state).
3. The project page reads that param on mount and auto-opens the task creation form.

---

## Constraints

- Vault path security: all file writes must pass through the existing `is_path_inside()` guard (`server.py:704-705`). The new intent handler must call this check before writing.
- `tag` validation regexp is the source of truth in `new_project_writer.py:57` — the frontend must mirror it exactly (copy the pattern, not import from backend).
- The browser SPA is the only target surface; no changes to the desktop Tauri popup or CLI skills.
- Intent file format must match `agent-pack/templates/intent.md` exactly — no deviation from the template.

## Key Decisions

**Why a new `POST /api/intents` endpoint instead of reusing the project create side-effect?**
The side-effect path (`POST /api/projects` with `first_intent_tag`) only works at project creation time. Standalone intent creation for existing projects has no other path — a dedicated endpoint is the only clean option.

**Why inline the intent write logic instead of a new writer module?**
The write is a single template render + file write with three fields. Extracting a module would add indirection without reuse value. If the template logic grows, extraction can happen then.

**Why navigate-to-project for cross-context task creation instead of a global modal?**
The task form needs the project slug in context for the API call and for the resulting task list refresh. Routing to the project page naturally provides that context and avoids threading project state through a global modal.

**Scoped exception to N7 non-goal**
The v0.5 HLD explicitly excluded vault structure mutations from the UI. This change lifts that for project and intent *creation only*. Renaming, moving, and deleting vault files remain out of scope — the exception is the minimum needed to close the creation gap.

## Out of Scope

- Desktop popup changes
- CLI skill changes (`/sq-new-project`, `/sq-capture`)
- Intent deletion or rename from the UI
- Project archival or deletion from the UI
- Bulk / batch creation
- Template selection (always uses `agent-pack/templates/intent.md`)
