# Project Name + Tag Auto-generation — Low-Level Design

## Architecture

### Frontend — `NewProjectModal.tsx`
- Add `name` state (`string`, required).
- Add `tagManuallyEdited` flag (`boolean`, default `false`).
- **Derivation function** `toTag(name: string): string`:
  ```
  name.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '-').replace(/^-|-$/g, '')
  ```
- `onChange` for Name input: if `!tagManuallyEdited`, also call `setTag(toTag(value))`.
- `onChange` for Tag input: set `tagManuallyEdited = true`, update tag value normally.
- Reset `tagManuallyEdited = false` on form reset.
- Name field is placed **above** Tag in the form (natural top-down flow: name → tag).
- `name` is added to `NewProjectRequest` and sent in the API payload.

### API type — `api/client.ts`
- Add `name: string` to `NewProjectRequest`.
- `name` is required; sent alongside `tag`.
- No other API type changes.

### Backend — `server.py` (API handler)
- Extract `name` from the POST payload (`payload.get("name") or ""`).
- Pass `name` to `create_project(name=...)`.

### Backend — `new_project_writer.py`
- Add `name: str = ""` parameter to `create_project()` and `_render_project_page()`.
- In `_PROJECT_PAGE_TEMPLATE`, change `# {tag}` to `# {name}`.
- In `_render_project_page`, pass `name=name or tag` so existing callers without a name fall back to the tag (backward-compatible).

## Constraints
- Tag regex unchanged: `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`
- `name` is NOT stored in frontmatter YAML — it only appears as the H1 in the markdown body.
- Callers that don't pass `name` (CLI, tests, `ensure_scratch_pad`) continue to render `# {tag}` via the fallback `name or tag`.

## Key Decisions
- **H1 = name, not tag**: the tag is the machine identifier; the name is what the human reads at the top of the project page.
- **No frontmatter `name:` field**: keeps the YAML schema minimal; title is always derivable by reading the H1.
- **`tagManuallyEdited` flag**: simpler than diffing; avoids false positives when user happens to type a matching value.
- **Name above Tag**: natural reading order — name is the primary input, tag is the derived identifier.

## Out of Scope
- Renaming existing projects (H1 in existing files is not touched).
- Storing `name` in YAML frontmatter or the database.
- Backend migration for projects created before this change.
