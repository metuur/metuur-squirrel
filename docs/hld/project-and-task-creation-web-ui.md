# Project & Task Creation from Web UI — High-Level Design

## Overview

This change adds project and task (intent) creation capabilities to the Squirrel browser SPA. Currently, both operations are CLI-only (`/sq-new-project`, `/sq-capture`), even though the backend already exposes a fully functional `POST /api/projects` endpoint. This feature lifts that constraint for the browser SPA only, letting users create projects and tasks without touching the terminal.

## Stakeholders & Impact

**Primary users:** Squirrel users who manage their vault through the browser SPA and find themselves forced to context-switch to a terminal whenever they need a new project or task.

**Current pain:** Creating a project requires running `/sq-new-project` in a Claude Code session. Creating a task requires `/sq-capture`. Neither action is available in the browser SPA at all. The backend plumbing for project creation already exists; intent creation has no HTTP endpoint yet.

**After this ships:**
- Users can create a new project directly from the SPA with full field support (tag, tipo, deadline, stakeholders, description, and optionally an initial task).
- Users can add a task to any existing project by navigating to the project page and using a "New Task" form.
- If the user triggers task creation from outside a project context, they are guided to select a project first, then land on that project page with the form pre-opened.

**Secondary consumers:** None — this is purely a browser SPA surface change. The desktop popup is out of scope.

## Goals

- SPA users can create a project via a form that exposes all current backend fields (`tag`, `tipo`, `deadline`, `stakeholders`, `description`, `first_intent_tag`, `first_intent_title`).
- SPA users can create a standalone intent/task inside an existing project via a new `POST /api/intents` backend endpoint.
- Task creation initiated outside a project page routes through a project-selector step before presenting the task form.
- Inline validation catches malformed `tag` and invalid `tipo` values before the network call.

## Non-Goals

- Desktop popup: no changes.
- CLI replacement: the existing `/sq-new-project` and `/sq-capture` skills are unchanged.
- Vault folder renames, moving files between PARA categories, or any other vault structure mutation beyond creating new project/intent files.
- Authentication or RBAC changes.
- Bulk creation, import, or template selection beyond the existing `intent.md` template.

## Success Criteria

1. A user can fill the "New Project" form in the SPA and see the new project appear in the project list immediately after submission.
2. A user on a project page can click "New Task", fill the form, and see the task appear in the project's task list without a page reload.
3. A user clicking "New Task" from a non-project page is shown a project selector, then navigated to the chosen project page with the task form open.
4. Submitting a project with a `tag` that violates `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` or an invalid `tipo` is blocked client-side with a clear error message.
5. Backend errors (duplicate tag, file write failure) surface inline in the form without losing entered data.
