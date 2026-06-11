# Project & Task Creation from Web UI — Tasks

## Unit 1: Project Creation Form

- [x] 1.1 Add missing optional fields to `NewProjectModal` (est: ~30m)
  - context: `NewProjectModal.tsx` already exists and is wired via Sidebar "+" button. `client.ts` already has all `NewProjectRequest` types. Only the UI fields for `stakeholders`, `first_intent_tag`, and `first_intent_title` are missing from the form.
  - files: `apps/backend/app/src/components/NewProjectModal.tsx`
  - acceptance: R-1.2, R-1.5 — WHEN optional fields `stakeholders`, `first_intent_tag`, or `first_intent_title` are filled, they are included in the `POST /api/projects` payload; IF `first_intent_tag` is filled and `first_intent_title` is empty, an inline error blocks submission.
  - verify: Open the "New project" modal from the Sidebar "+", confirm all three new fields render; fill `first_intent_tag` without `first_intent_title` and confirm submission is blocked with an inline error; submit a project with all fields and confirm the backend response includes `intent_id`.

---

## Unit 2: Standalone Intent (Task) Creation

- [x] 2.1 Add `POST /api/intents` backend endpoint (est: ~45m)
  - files: `apps/backend/server.py`
  - acceptance: R-2.1 – R-2.6 — endpoint accepts `project_slug`, `tag`, `title`, and optionally `description` and `deadline`; validates vault path via `is_path_inside()`; returns 404 for unknown project, 409 for duplicate tag, 422 for invalid tag; on success writes `<vault>/01-Active-Projects/<project_slug>/<tag>.md` from `agent-pack/templates/intent.md` and returns HTTP 201.
  - verify: `curl -s -X POST http://127.0.0.1:3939/api/intents -d '{"project_slug":"<existing>","tag":"TEST","title":"Test task"}' -H 'Content-Type: application/json'` → 201; repeat → 409; use a bad tag → 422; use unknown project → 404.

- [x] 2.2 Add `intentCreate` to browser SPA `client.ts` (deps: 2.1, est: ~15m)
  - files: `apps/backend/app/src/api/client.ts`
  - acceptance: R-2.1 — `NewIntentRequest` and `NewIntentResult` types are exported; `api.intentCreate(req)` calls `POST /api/intents` with the correct payload.
  - verify: TypeScript compiles without errors (`npm run build` in `apps/backend/app`); the type shape matches the backend's expected fields.

---

## Unit 3: Task Creation Form (Project Page)

- [x] 3.1 Create `NewTaskModal` component (deps: 2.2, est: ~30m)
  - files: `apps/backend/app/src/components/NewTaskModal.tsx` (new file)
  - acceptance: R-3.1, R-3.2, R-3.3, R-3.4, R-3.5 — modal accepts `projectSlug` prop; renders `tag` (with client-side regexp validation) and `title` (required), `description` and `deadline` (optional); calls `api.intentCreate`; on 201 invokes `onCreated()` callback and closes; on error displays error inline without losing field values; invalid `tag` is blocked client-side before the network call.
  - verify: Render the modal in isolation (or via Storybook / direct route); submit with a lowercase tag → inline error, no fetch; submit valid fields against the running backend → modal closes and `onCreated` fires.

- [x] 3.2 Wire "New Task" button and `?newTask=true` handling into `ProjectPage` (deps: 3.1, est: ~25m)
  - files: `apps/backend/app/src/pages/ProjectPage.tsx`
  - acceptance: R-3.1, R-3.2, R-3.3, R-3.4 — a "New Task" button appears in the project page action bar; clicking it opens `NewTaskModal` with `projectSlug` from the URL param; on `onCreated`, the task list re-fetches; on mount, if `?newTask=true` is in the URL, the modal opens automatically.
  - verify: Navigate to an existing project page; click "New Task"; fill the form and submit → new task appears in the "Recent notes" list without full page reload. Then navigate to `/projects/<slug>?newTask=true` and confirm the form opens immediately.

---

## Unit 4: Cross-Context Task Creation Routing

- [x] 4.1 Add `ProjectSelectorModal` and global "New Task" trigger (deps: 3.1, est: ~35m)
  - files: `apps/backend/app/src/components/ProjectSelectorModal.tsx` (new), `apps/backend/app/src/components/layout/Sidebar.tsx`
  - acceptance: R-4.1, R-4.2, R-4.3 — a "New task" button is present in the Sidebar (alongside the existing "New project" "+" button); clicking it from any non-project page opens `ProjectSelectorModal` listing active projects from `api.projects()`; selecting a project navigates to `/projects/<slug>?newTask=true`; the project page then auto-opens the task form (covered by 3.2).
  - verify: From the Home page, click the Sidebar "New task" trigger; select a project from the list; confirm navigation lands on the correct project page with the task form open.
