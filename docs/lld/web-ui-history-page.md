# Web UI Recent-Activity (History) Page — Low-Level Design

> _Backfilled from the as-built `HistoryPage.tsx` + `api_history`._

## Architecture

A thin read-only page over a single backend endpoint that ranks vault `.md` files
by modification time.

```
HistoryPage.tsx                         apps/backend/server.py :: api_history
  useFetch('history', api.history())      GET /api/history
    isLoading & !data → skeleton          rglob('*.md') under active vault
    empty             → "Nothing yet."     skip hidden parts + 05-Post-its
    rows              → <Link>             sort by st_mtime desc, take 30
                                           map → { kind, slug, note_id, title,
                                                   modified_at }
```

## Backend contract (`api_history`, `GET /api/history`)

- Walks `ctx.active.path.rglob("*.md")`.
- **Excludes** any path with a dot-prefixed part (hidden) and anything inside
  `05-Post-its`.
- Sorts candidates by `st_mtime` descending; takes the first **30**.
- For each, classifies project-page vs note: a file is a project page when its
  name equals `<parentFolder>.md`. Emits:
  ```json
  {
    "kind": "project" | "note",
    "slug": "<parentFolder>" | null,      // set for projects
    "note_id": null | "<stem>",           // set for notes
    "title": "<project title>" | "<stem>",
    "modified_at": <mtime float>
  }
  ```
  Project titles come from `vocabulary.project_title(parent, vault)`.

## Frontend behavior (`HistoryPage.tsx`)

- `useFetch('history', () => api.history())`.
- While `isLoading && !data` → animated skeleton block.
- Empty (`!data || length === 0`) → dashed panel, `history` icon, "Nothing yet.".
- Otherwise a list of `<Link>` rows:
  - `href = kind === 'project' ? '/projects/<slug>' : '/notes/<note_id>'`.
  - Icon `folder` for projects, `description` for notes.
  - Title (truncated) + right-aligned relative time via `fromNow(modified_at)`.
  - React key combines kind + slug/note_id/index for stability.

## Constraints

- Read-only; no mutation endpoints involved.
- Recency is filesystem mtime — correctness depends on writers preserving mtimes
  (atomic writes update mtime, which is the desired behavior).
- Fixed window of 30; no pagination.

## Key Decisions

- **mtime-ranked file scan over an event log** — zero new persistence; reflects
  edits from every surface (agent/CLI/popup/Obsidian) uniformly.
- **Exclude Post-its** — they live on their own board and would noise up "recent
  notes".
- **Top-30 fixed window** — a re-entry aid, not an archive; bounded work per
  request.

## Out of Scope

- Diffs / per-edit audit, pagination, filtering, Post-it inclusion.
