# Post-it Notes — Low-Level Design

## Architecture

### Storage — Markdown source of truth, SQLite presentation index

**Vault folder.** Post-its live in a new top-level vault folder `05-Post-its/`, outside `01-Active-Projects` (so they never enter project/task vocabulary, unlike SCRATCH-PAD artifacts). The numeric prefix is unused in every current and legacy vault layout (`01`–`04`, `06`, `99` are taken across variants). Project/status scanners iterate their own specific folders, so the new folder is naturally invisible to them.

**File format.** One Markdown file per Post-it, named `PI-NNN.md` (zero-padded sequence, same `_next_number` convention as `QT-NNN` / `UNFILED-NNN`). Frontmatter:

```yaml
---
id: PI-001
type: post_it
state: active            # active | archived
color: yellow            # one of the sticky palette keys
label: ""                # optional short corner label (e.g. "idea")
pinned: false
created: 2026-06-11T13:20:50-05:00
converted_to: ""         # e.g. "quick_task:QT-014" | "project_task:<slug>/<file>" | "project_note:<slug>/<file>"
---
<free text body>
```

Deliberately uses `state`, not `status`, and never `reminder_date`/`due` — existing reminder, deadline, and quick-task scanners key off those fields (plus their own folders), so Post-it files are doubly excluded.

**SQLite layout index.** `db.py` `init_schema` gains one idempotent table holding board presentation only:

```sql
CREATE TABLE IF NOT EXISTS post_it_layout (
  vault       TEXT NOT NULL,
  post_it_id  TEXT NOT NULL,
  x           REAL NOT NULL,   -- percentage of board width
  y           REAL NOT NULL,   -- percentage of board height
  rotation    REAL NOT NULL,   -- degrees, small range
  z           INTEGER NOT NULL DEFAULT 0,
  updated_at  TEXT NOT NULL,
  PRIMARY KEY (vault, post_it_id)
);
```

The table is rebuildable and disposable: a Post-it with no row gets a deterministic, non-overlapping default placement — grid slot from creation order, small jitter and rotation (±3°) from its id hash. Pure hash-scatter is rejected: it visibly stacks cards once the wall passes a few dozen notes. Deleting `squirrel.db` loses positions, never content. Rows for deleted/archived Post-its are removed on delete and ignored otherwise.

### Backend — Python library + server routes

New modules in `apps/cli/lib/`, following the quick-task writer/scanner split:

- `post_it_writer.py` — `create(text, color, label)` (atomic write, next-number allocation, ensures `05-Post-its/` exists), `update(id, fields)` (frontmatter/body rewrite), `archive/restore/delete`, `record_conversion(id, ref)`.
- `post_it_scanner.py` — scans `05-Post-its/*.md` for `type: post_it`, parses frontmatter + body, returns active and archived lists (pinned first, then newest-first).

Routes registered in `apps/backend/server.py` alongside the quick-task block (collection plural, item-action singular, matching `/api/quick-tasks` + `/api/quick-task/{id}/...`):

| Route | Behavior |
|---|---|
| `GET /api/post-its?include=archived` | Scanner output joined with `post_it_layout` rows; each item: `{id, text, color, label, pinned, state, created, converted_to, layout:{x,y,rotation,z}}` |
| `POST /api/post-its` | `{text, color?, label?}` → writer.create → 201 with the new item |
| `PATCH /api/post-it/{id}` | `{text?, color?, label?, pinned?}` → writer.update |
| `PATCH /api/post-it/{id}/layout` | `{x, y, rotation, z?}` → upsert `post_it_layout` row |
| `PATCH /api/post-it/{id}/archive` / `.../restore` | flips `state` |
| `DELETE /api/post-it/{id}` | removes file + layout row |
| `POST /api/post-it/{id}/convert` | `{target: "quick_task"\|"project_task"\|"project_note", project_slug?}` — delegates to `quick_task_writer.create`, the intent-template task creation path, or `capture_writer.write_capture(project_slug)` respectively; on success sets `state: archived` + `converted_to`, returns the new artifact reference |

All mutating routes invalidate the vault cache the same way `api_note_create` does. Conversion is sequenced create-target-first, then mark-source — a crash between the two leaves a duplicate (Post-it still active), never data loss.

### Desktop popup — capture only, in-app

- Tray: new "Add Post-it" item next to "Add Quick Task" (`tray.rs`), emitting `post-it-capture-open` and foregrounding the popup — same mechanics as `quick-task-capture-open` at `tray.rs:429`. No Rust data commands; React owns the API call (matches existing capture architecture).
- React: `usePostItCapture` hook (mirror of `useQuickTaskCapture.ts`) listens for the event; `PostItCaptureModal.tsx` renders a minimal capture box — one text line, a row of color swatches, Enter to save — calling a new `api.postItCreate(text, color)` in `apps/desktop/src/api/client.ts`.
- Popup UI: a Post-it trigger alongside the existing capture actions in `App.tsx` opens the same modal. Existing `CaptureModal` (notes) is untouched.
- No global shortcut registered; no board view in the popup.

### Web UI — `/post-its` board

- Route: `/post-its` added to `apps/backend/app/src/App.tsx` under the shared `Layout`, plus a sidebar entry.
- `PostItsPage.tsx`: fetches `GET /api/post-its`; renders a wall of absolutely-positioned sticky cards inside a relative container. Per the visual reference: sticky-note color fills with a darker top strip, slight per-card rotation, soft shadow, handwritten-style display font (bundled locally in the app — no CDN; `cursive` fallback), optional small corner label.
- Interactions: drag a card → on drop, `PATCH .../layout` (pointer-event drag like the home board's drag/drop, but free-position instead of lanes); drag activates only past a small movement threshold (~5px) so plain clicks reliably open the card; click card → edit popover (text, color swatches, label, pin toggle, archive, delete, convert); pinned cards render with top z-order and a pin indicator; an "Archived" toggle swaps the wall to archived cards with restore/delete actions.
- Capture: a "New Post-it" composer on the board page (text + color), posting to `POST /api/post-its` and placing the card at the default position.
- Search: `/api/search` already scans all vault Markdown, so Post-it bodies are hits for free; the search handler classifies files under `05-Post-its/` as `kind: post_it`, and the header navigates those hits to `/post-its?focus={id}`, which scrolls to and briefly highlights the card.

## Constraints

- Local-first: no network fonts, no cloud storage; the handwriting font ships with the app bundle.
- Markdown remains the user-content source of truth (product positioning: "Markdown source of truth, SQLite where history matters"); SQLite holds only rebuildable presentation state.
- Writes are atomic (temp file + rename) like `capture_writer._atomic_write`.
- Existing scanners (quick task, reminder, deadline, status aggregator) must not change behavior; isolation is by folder and by absence of their trigger fields.
- Tauri webview: no `window.prompt/alert/confirm` — all input via in-app modals.
- The tray action completes in-app (popup modal), never by opening the web UI.

## Key Decisions

- **Hybrid persistence, with a strict split.** Markdown holds everything semantic (text, color, label, pinned, state, conversion); SQLite holds only x/y/rotation/z. Rejected: SQLite-primary (breaks Markdown-source-of-truth positioning for user content); pure-Markdown with positions in frontmatter (every drag would rewrite the user's content file and churn mtimes/conflict handling).
- **New top-level `05-Post-its/` folder.** Rejected: inside `SCRATCH-PAD` (drags Post-its into project/task vocabulary and quick-task scanner territory); inside `99-Resources/Inbox` (conflates with unfiled captures, which remain note-flavored).
- **`state` key instead of `status`.** Existing scanners filter on `status` values; a disjoint key makes accidental pickup structurally impossible rather than convention-dependent.
- **Post-its are walled off from the note system.** `_find_note` resolves note ids vault-wide, so without an explicit exclusion `PI-NNN` would render and be editable at `/notes/PI-NNN` — a second surface that would mangle Post-it frontmatter. Note detail/edit endpoints return 404 for ids under `05-Post-its/`, and search classifies that folder as `post_it` so hits route to the board instead.
- **Conversion delegates to existing writers.** Quick Task, intent-template task, and project-note capture flows already encode their own invariants (caps, numbering, templates); Post-it conversion calls them instead of re-implementing, then archives the source with a `converted_to` pointer. Rejected: moving/renaming the Post-it file itself into the target shape (loses the capture history, duplicates writer logic).
- **Default layout is deterministic from the id.** Same scatter on every machine and after index loss; no stored randomness, no `Math.random` divergence between loads.
- **Separate capture surfaces rather than extending existing modals.** The existing note/quick-task modals each encode a classification; adding a "kind picker" to them would reintroduce the decision pressure Post-its exist to remove.

## Out of Scope

- Global keyboard shortcut for Post-it capture (candidate `Ctrl+Cmd+P`, deferred).
- Post-it wall inside the desktop popup; Post-its on the Home board.
- Tags, multi-line rich text rendering, images, or free-form board zoom/pan.
- Bulk operations (multi-select archive/delete).
- Converting a Post-it into a whole new project.
- Indexed (database) search; Post-its ride the existing linear Markdown scan.
