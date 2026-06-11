# Post-it Notes — Tasks

## Storage model

- [x] 1.1 `post_it_layout` table in SQLite schema (est: ~15m, mutex: db-schema)
  - acceptance: R-1.4 — board presentation state (x, y, rotation, z) stored only in `post_it_layout`, keyed by vault + Post-it id, created idempotently at schema init
  - verify: `init_schema` runs twice on a fresh temp DB without error; `post_it_layout` exists with the expected columns

- [x] 1.2 `post_it_writer.py` — create/update/archive/restore/delete/record_conversion (est: ~45m)
  - acceptance: R-1.1 — create writes `PI-NNN.md` (zero-padded next free number) under `05-Post-its/`, creating the folder, via atomic temp-file-and-rename; R-1.2 — frontmatter has `id`, `type: post_it`, `state`, `color`, `label`, `pinned`, `created`, `converted_to`, body is the text; R-1.3 — never writes `status`, `reminder_date`, or `due`
  - verify: unit tests on a temp vault — create allocates sequential ids, file parses with exact key set, update/archive/restore/delete round-trip

- [x] 1.3 `post_it_scanner.py` — scan + ordering (deps: 1.2, est: ~30m)
  - acceptance: R-2.1 (ordering half) — active Post-its returned pinned-first then newest-first; archived list separate; files with missing/extra frontmatter keys degrade gracefully instead of being dropped
  - verify: unit tests with seeded files covering pinned/unpinned mix, archived, and a hand-mangled frontmatter file

## Backend API

- [x] 2.1 `GET /api/post-its` with layout join and deterministic defaults (deps: 1.1, 1.3, est: ~40m, mutex: server-py)
  - acceptance: R-2.1 — returns active Post-its with `id`, `text`, `color`, `label`, `pinned`, `state`, `created`, `converted_to`, `layout`; R-2.2 — `?include=archived` adds archived; R-1.5 — missing layout row yields deterministic non-overlapping default (grid slot from creation order, jitter/rotation from id)
  - verify: backend tests — seeded vault returns ordered payload; two notes without rows never get identical positions; same vault yields identical defaults across two calls

- [x] 2.2 `POST /api/post-its` (deps: 1.2, est: ~20m, mutex: server-py)
  - acceptance: R-2.3 — non-empty `text` (+ optional `color`, `label`) → 201 with created item; empty/missing `text` → 400 with no write; R-2.9 — vault cache invalidated
  - verify: backend tests — 201 creates file, 400 leaves folder untouched, subsequent GET sees the new item without restart

- [x] 2.3 Item routes — PATCH fields/layout/archive/restore, DELETE (deps: 2.1, est: ~40m, mutex: server-py)
  - acceptance: R-2.4 — PATCH `{text,color,label,pinned}` updates the file; R-2.5 — PATCH `/layout` upserts the SQLite row without touching Markdown; R-2.6 — `/archive` and `/restore` flip `state`; R-2.7 + R-1.6 — DELETE removes file and layout row; R-2.8 — unknown id → 404; R-2.9 — cache invalidated on mutation
  - verify: backend tests per route, including file mtime unchanged after `/layout`, 404 for `PI-999`, layout row gone after DELETE

## Conversion

- [x] 3.1 Convert endpoint — `quick_task` target (deps: 2.3, est: ~35m, mutex: server-py)
  - acceptance: R-3.1 — creates a Quick Task via the existing flow including active-cap behavior; R-3.4 — on success sets `state: archived`, records `converted_to`, returns the reference; R-3.5 — on failure Post-it unchanged; R-6.6 (backend half) — cap rejection returns a structured cap-full error
  - verify: backend tests — success archives source with pointer; cap-full leaves Post-it active and returns the structured error; create-first ordering asserted (target exists before source is marked)

- [x] 3.2 Convert endpoint — `project_task` and `project_note` targets (deps: 3.1, est: ~30m, mutex: server-py)
  - acceptance: R-3.2 — `project_task` + valid slug creates via intent-template flow; R-3.3 — `project_note` + valid slug creates via capture writer; R-3.6 — missing/unknown slug → 400 with nothing created
  - verify: backend tests — both targets produce files in the project folder and archive the source; bad slug creates nothing and Post-it stays active

## Capture surfaces

- [x] 4.1 Desktop popup capture — client method, modal, hook, trigger (deps: 2.2, est: ~45m)
  - acceptance: R-4.3 — Post-it trigger alongside existing capture actions opens the modal; R-4.4 — submit with text (+ selected color) posts to `/api/post-its`, confirms visually, closes; empty text does not submit
  - verify: component tests for `PostItCaptureModal` (submit, empty-block, color selection); manual popup check that the trigger opens it and a file lands in `05-Post-its/`

- [x] 4.2 Tray "Add Post-it" item (deps: 4.1, est: ~25m)
  - acceptance: R-4.1 — tray item next to "Add Quick Task"; R-4.2 — selecting it foregrounds the popup and opens the modal in-app, never the web UI; R-4.5 — no new global shortcut registered
  - verify: build + manual tray check; grep confirms no new `register` call in the shortcut setup

- [x] 4.3 Web board composer (deps: 2.2, 5.1, est: ~20m)
  - acceptance: R-4.6 — composer on `/post-its` creates a Post-it with chosen text/color and shows the card at its default position without full reload
  - verify: component test — submit adds a card to the rendered wall from the POST response

## Post-it board (Web UI)

- [x] 5.1 `/post-its` route, sidebar entry, sticky-card wall (deps: 2.1, est: ~60m)
  - acceptance: R-5.1 — route under shared layout with sidebar entry; R-5.2 — every active Post-it renders as a sticky card (color fill, body text, optional corner label, pin indicator) positioned/rotated per layout; R-5.9 — locally bundled handwriting font with `cursive` fallback, no remote assets
  - verify: component test renders seeded payload with positions applied; network panel / build output shows the font served from the bundle

- [x] 5.2 Drag-to-reposition with click threshold (deps: 5.1, 2.3, est: ~40m)
  - acceptance: R-5.3 — drop persists via the layout endpoint and survives reload; drag activates only past ~5px so plain clicks open the card
  - verify: component test simulating pointer drag (>5px persists, <5px opens); manual reload check

- [x] 5.3 Card actions — edit popover, pin, archive view, delete (deps: 5.1, 2.3, est: ~50m)
  - acceptance: R-5.4 — pinned cards render above unpinned; R-5.5 — popover edits text/color/label and offers pin/archive/delete/convert via the API; R-5.7 — archived toggle shows archived cards with restore/delete, restore returns the card to the wall; R-5.8 — delete asks in-app confirmation first (no `window.confirm`)
  - verify: component tests per action; z-order assertion for pinned card; confirm dialog is an in-app element

- [x] 5.4 Convert UI (deps: 5.3, 3.2, est: ~35m)
  - acceptance: R-5.6 — convert offers Quick Task / project task / project note with a project picker for the latter two; success removes the card from the active wall; R-6.6 (UI half) — cap-full error rendered as guidance ("complete a Quick Task first"), card unchanged
  - verify: component tests — each target calls the endpoint with the right payload; cap-full error path shows guidance and keeps the card

## Search and isolation

- [x] 6.1 Note-endpoint wall-off (deps: 1.2, est: ~20m, mutex: server-py)
  - acceptance: R-6.5 — `/api/notes/{id}` (detail and save) returns 404 for ids under `05-Post-its/`
  - verify: backend test — `GET/POST /api/notes/PI-001` → 404 while `/api/post-its` still serves it

- [ ] 6.2 Search classification and board navigation (deps: 5.1, est: ~30m, mutex: server-py)
  - acceptance: R-6.1 — search hits on Post-it bodies are returned classified `kind: post_it`; R-6.2 — selecting such a hit navigates to `/post-its` and highlights the matching card
  - verify: backend test for classification; component test that a `post_it` result navigates to `/post-its?focus=PI-NNN` and the card gets the highlight state

- [x] 6.3 Isolation regression check (deps: 1.2, est: ~25m)
  - acceptance: R-6.3 — Post-it files excluded from Quick Task scanning, reminder scanning, deadline scanning, project listings, `/api/home`; R-6.4 — note/project/journal/focus behavior unchanged while Post-it files exist
  - verify: backend test seeding `05-Post-its/` files, asserting quick-task list, reminder/deadline scans, project listings, and `/api/home` payloads are byte-identical to a vault without them
