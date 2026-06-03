# Project Name + Tag Auto-generation — Tasks

## Unit 1: Name field

- [ ] 1.1 Add Name field to NewProjectModal (est: ~15m)
  - files: `apps/backend/app/src/components/NewProjectModal.tsx`
  - acceptance: R-1.1 — THE SYSTEM SHALL render a required "Name" text input above the Tag field
  - acceptance: R-1.2 — WHEN Name is empty, THE SYSTEM SHALL disable "Create project"
  - acceptance: R-1.3 — WHEN form resets/closes, THE SYSTEM SHALL clear the Name field
  - verify: open modal → Name input appears above Tag; submit button is disabled with empty name; close and reopen → Name is blank

## Unit 2: Auto-derivation of Tag from Name

- [ ] 2.1 Wire toTag auto-derivation (deps: 1.1, est: ~10m)
  - files: `apps/backend/app/src/components/NewProjectModal.tsx`
  - acceptance: R-2.1 — WHEN user types in Name AND Tag not manually edited, Tag = toTag(name)
  - acceptance: R-2.2 — WHEN derived Tag is empty string (e.g. name is "---"), Tag field is left empty
  - acceptance: R-2.3 — WHILE Tag not manually edited, Tag stays in sync on every keystroke
  - verify: type "My Cool App" → Tag shows `MY-COOL-APP`; type "---" → Tag stays blank

## Unit 3: Manual Tag override

- [ ] 3.1 Implement tagManuallyEdited flag (deps: 2.1, est: ~5m)
  - files: `apps/backend/app/src/components/NewProjectModal.tsx`
  - acceptance: R-3.1 — WHEN user types in Tag field, auto-sync from Name stops
  - acceptance: R-3.2 — WHEN form resets, flag clears so auto-sync resumes
  - acceptance: R-3.3 — Manual tag still validated against `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`
  - verify: type name → auto-syncs; edit Tag directly → stops syncing; reset form → auto-sync resumes on next name keystroke

## Unit 4: API & markdown rendering

- [ ] 4.1 Add `name` to NewProjectRequest type (est: ~5m)
  - files: `apps/backend/app/src/api/client.ts`
  - acceptance: R-4.1 — `name: string` present in `NewProjectRequest`
  - verify: TypeScript compiles with no errors; `NewProjectRequest` has `name: string`

- [ ] 4.2 Send `name` from modal on submit (deps: 1.1, 4.1, est: ~5m)
  - files: `apps/backend/app/src/components/NewProjectModal.tsx`
  - acceptance: R-4.1 — payload includes `name` (trimmed) alongside `tag`
  - acceptance: R-4.2 — IF name empty after trim, show "Project name is required." and block submit
  - verify: network tab shows `name` in POST body; submit with blank name shows inline error

- [ ] 4.3 Extract `name` in server.py and pass to create_project (est: ~5m)
  - files: `apps/backend/server.py` — `api_project_create` handler (line ~987)
  - acceptance: backend receives `name` from payload and forwards it to `create_project(name=...)`
  - verify: after adding the line, no 500 errors on project creation

- [ ] 4.4 Use `name` as H1 in project markdown template (deps: 4.3, est: ~10m)
  - files: `apps/cli/lib/new_project_writer.py`
  - changes: add `name: str = ""` to `create_project()` + `_render_project_page()`; change `# {tag}` to `# {name}` in `_PROJECT_PAGE_TEMPLATE`; pass `name=name or tag` as fallback
  - acceptance: R-4.3 — scaffolded markdown opens with `# {name}`
  - acceptance: R-4.4 — CLI/legacy callers without name still render `# {tag}`
  - acceptance: R-4.5 — `name` does NOT appear in YAML frontmatter
  - verify: create project "My Cool App" → open `MY-COOL-APP/MY-COOL-APP.md` → first H1 is `# My Cool App`; run CLI without --name → H1 is `# SOMETAG`
