# Project & Task Classification Dimensions — Tasks

Source specs: `docs/hld/project-task-classification-dimensions.md`, `docs/lld/project-task-classification-dimensions.md`, `docs/ears/project-task-classification-dimensions.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.
Test command: `make test-cli`. Constraints: Python 3.9+ stdlib only; reuse `write_frontmatter`/`is_path_inside`; soft validation only; no `schema_version` bump; greenfield vault (no migration); no-cross-page-helper convention.

Dependency layers:

```
A  (data layer — risky-write-free; proves on greenfield vault)
 │   A.1 config get_classification + defaults + parse-isolation
 │   A.2 classification.py pure module (dimensions, STATUS_FOLDER, normalize)
 │   A.3 status_aggregator reads new keys + drops A/B/C type semantics
 │   A.4 re-home finishing-tax staleness alert
 │   A.5 new_project_writer template + remove _VALID_TIPOS
 │
 ├─ B  (API: GET /api/classification)                      [deps A.1]
 │
 ├─ C  (risky write path — own tests + isolation)          [deps A.2, A.5]
 │      C.1 project_status_move (dir move + collision refuse)
 │      C.2 server project-save gate (archive-confirm + WIP + authority) [deps C.1]
 │      C.3 task save label-only                            [deps A.2]
 │      C.4 read-side drift semantics (find_projects unchanged)
 │
 └─ D  (frontend)                                          [deps B, C.2]
        D.1 client.ts vocab types + getClassification + type:string
        D.2 ProjectEditPage selects (5) + out-of-list + confirm UX  [deps D.1]
        D.3 NoteEditPage selects (3) + label-only                   [deps D.1]
        D.4 NewProjectModal config-driven type + dimension selects  [deps D.1]
                                                                      │
                                                                      E (integration/regression: make test-cli green + backward-compat) [deps C.2, D.2, D.3, D.4]
```

## Unit 1: Config-defined vocabularies (`apps/cli/lib/config_loader.py`)

- [ ] **A.1** Add `DEFAULT_CLASSIFICATION` and `get_classification(config_path=None) -> dict[str, list[str]]` — reads the `[classification]` table, per-key replaces defaults, isolates parse failures. (est: ~50m)
  - acceptance:
    - R-1.1 — reads `[classification]` with keys `type`, `mode`, `horizon`, `focus_risk`, `status`, each an inline string array.
    - R-1.2 — a present key's array replaces (not appends to) the built-in default for that key.
    - R-1.3 — absent table or absent key → built-in default for that dimension.
    - R-1.4 — defaults equal the exact value sets in the EARS table (type incl. mission-critical/important/experimental; mode incl. URGENT).
    - R-1.5 — works on both the `tomllib` (3.11+) and `_fallback_parse` (3.9/3.10) paths with no parser extension.
    - R-1.6 — a malformed/unreadable `[classification]` falls back to defaults and does NOT break `list_vaults`/`get_vault`.
  - verify:
    - pytest: config with custom `[classification].status` → `get_classification()["status"]` equals the custom list; other keys are defaults.
    - pytest: config with no `[classification]` → all five default lists returned.
    - pytest: config with a broken `[classification]` line but valid `[[vaults]]` → defaults returned AND `get_default_vault()` still resolves.
    - pytest (3.9/3.10 fallback): force `_fallback_parse` path → arrays parse identically.

## Unit 2: Classification core module (`apps/cli/lib/classification.py` — NEW)

- [ ] **A.2** Create pure module: `PROJECT_DIMENSIONS`, `TASK_DIMENSIONS`, `STATUS_FOLDER`, `normalize(value, allowed) -> str`, `target_folder_for_status(status) -> str|None`. No I/O. (est: ~40m)
  - acceptance:
    - R-3.1 — `PROJECT_DIMENSIONS == ("type","mode","horizon","focus_risk","status")`.
    - R-3.2 — `TASK_DIMENSIONS == ("mode","focus_risk","status")` (no type/horizon).
    - R-4.1 — `normalize` matches case- and whitespace-insensitively into `allowed`.
    - R-4.2 — an unmatched value is returned verbatim (never raises).
    - R-7.1 — `STATUS_FOLDER` maps THE_THING/ACTIVE/COOLDOWN/BLOCKED→`01-Active-Projects`, PARKED→`02-Parking-Lot`, DONE→`06-Archive`.
    - R-7.6 — `target_folder_for_status` returns `None` for a value not in `STATUS_FOLDER`.
  - verify:
    - pytest: `normalize(" done ", ["DONE"])` → matched value; `normalize("WORK", ["WORK"])` exact; `normalize("xyz", [...])` → `"xyz"`.
    - pytest: `target_folder_for_status("PARKED")` → `02-Parking-Lot`; `target_folder_for_status("WEIRD")` → `None`.

## Unit 3: Aggregator reads dimensions & drops the A/B/C tier (`apps/cli/lib/status_aggregator.py`)

- [ ] **A.3** Read `mode`/`horizon`/`focus_risk` into `analyze_project`; treat `type` as taxonomy; stop emitting/consuming A/B/C `type` semantics and the `type/{tipo}` tag. (deps: A.2, est: ~60m, mutex: type-semantics)
  - acceptance:
    - R-3.3 — `analyze_project` output carries `mode`, `horizon`, `focus_risk`, plus `type`/`status` as taxonomy values.
    - R-3.4 — absent dimension key → null, no error.
    - R-3.5 — a non-managed dimension key on a file is preserved (not stripped) on read.
    - R-5.1 — `type` is no longer constrained to A/B/C anywhere in the read path.
    - R-5.2 — no `type/{value}` tag is consumed as importance.
    - R-4.3 — out-of-vocabulary values never reject a read.
  - verify:
    - **Pre-work grep (bake into the story):** `rg "type/" apps/cli apps/backend; rg "_VALID_TIPOS|tipo|type ==|\.get\(.type.\)" apps/cli apps/backend` — enumerate every reader; confirm none other than the alert + writer + quick-task sentinel depend on A/B/C. Record the list in scratchpad.
    - pytest: fixture project with `type: WORK`, `mode: DEEP_FOCUS`, `horizon: LONG`, `focus_risk: CONTEXT_HEAVY` → all surfaced in aggregate output.
    - pytest: confirm Quick-Task detection (`type == "quick_task"`) is untouched and never collides with a taxonomy `type`.
    - `make test-cli` green.

- [ ] **A.4** Re-home the staleness critical alert from `priority == "finishing-tax"` to `focus_risk`/`status`. (deps: A.3, est: ~30m)
  - acceptance:
    - R-11.1 — the `finishing-tax`/tier dependency is removed from the alert.
    - R-11.2 — a project stale >7 days with `focus_risk == DOPAMINE_LOW` OR `status == BLOCKED` raises an equivalent `critical` alert.
    - R-11.3 — the old `priority == "finishing-tax"` alert no longer fires.
  - verify:
    - pytest: stale (`days_since_activity > 7`) project with `focus_risk: DOPAMINE_LOW` → `critical` alert present.
    - pytest: stale project with old `priority: finishing-tax` and no new trigger → no critical alert from the old path.

## Unit 4: New project scaffolding (`apps/cli/lib/new_project_writer.py`)

- [ ] **A.5** Update `_PROJECT_PAGE_TEMPLATE` to emit `type`/`mode`/`horizon`/`focus_risk`/`status` from config defaults; remove `_VALID_TIPOS`/`_validate_tipo` and the `--type` choice restriction; drop the `type/{tipo}` tag. (deps: A.1, A.2, est: ~50m, mutex: type-semantics)
  - acceptance:
    - R-6.1 — created project page carries all five dimension keys.
    - R-6.2 — unspecified dimensions seed from a configured default (e.g. `status: ACTIVE`); never an out-of-vocabulary value.
    - R-6.3 — project is created in `01-Active-Projects/` when seeded `status` maps to active.
    - R-5.3 — any vocabulary `type` value is accepted (no A/B/C validation, no CLI `choices`).
    - R-5.4 — `mission-critical`/`important`/`experimental` remain valid `type` values.
  - verify:
    - pytest: create project without `type` → page has 5 keys, `status: ACTIVE`, no `type/` tag, lands in `01-Active-Projects/`.
    - pytest: create with `type: mission-critical` → accepted, written verbatim.
    - pytest: SCRATCH-PAD auto-seed still succeeds and is unaffected.
    - `make test-cli` green.

## Unit 5: Classification API (`apps/backend/server.py`)

- [ ] **B.1** Add `GET /api/classification` returning the five effective vocabularies. (deps: A.1, est: ~30m)
  - acceptance:
    - R-2.1 — endpoint returns JSON with `type`/`mode`/`horizon`/`focus_risk`/`status` arrays.
    - R-2.2 — returns config values where present, defaults otherwise.
    - R-2.3 — resolves vocabularies per the request's active vault/config context.
  - verify:
    - curl/pytest: `GET /api/classification` → 200 with all five arrays; with a custom config the override is reflected; with none, defaults.

## Unit 6: Project status → folder move (`apps/cli/lib/new_project_writer.py` + `apps/backend/server.py`)

- [ ] **C.1** Add `project_status_move(vault, slug, new_status, *, force) -> dict` — compute target via `target_folder_for_status`, refuse on target collision, move atomically. (deps: A.2, A.5, est: ~70m)
  - acceptance:
    - R-7.2 — when new status maps to a different folder than current, the directory is moved.
    - R-7.3 — source/target validated with `is_path_inside()`; move is atomic within the vault.
    - R-7.4 — returns the new slug/relative path.
    - R-7.5 — same-folder status → write value, no move.
    - R-7.7 — if the target folder already contains a dir with the project's name → conflict, no move/overwrite, contents and location intact.
  - verify:
    - pytest: `ACTIVE→PARKED` moves `01-Active-Projects/<TAG>` → `02-Parking-Lot/<TAG>`; returns new path.
    - pytest: `ACTIVE→ACTIVE` (or COOLDOWN) → no move.
    - pytest: pre-create `06-Archive/<TAG>` then `→DONE` → conflict raised, source intact, no overwrite.
    - pytest: attempt a path escaping the vault → rejected by `is_path_inside`.

- [ ] **C.2** Integrate the move into project save with server-authoritative gates (archive-confirm + WIP). (deps: C.1, est: ~60m)
  - acceptance:
    - R-8.1 — `→DONE` (archive) without confirmation → no move, response signals confirmation required.
    - R-8.2 — confirmed archive → move to `06-Archive/`.
    - R-8.3 — move into `01-Active-Projects/` at WIP capacity without force → no move, response signals WIP confirmation required.
    - R-8.4 — confirmed re-activation over cap → move completes.
    - R-8.5 — a project moved out of `01-Active-Projects/` no longer counts toward WIP.
    - (frontmatter write keeps existing mtime→409 conflict behavior; write precedes move.)
  - verify:
    - pytest: save `→DONE` without confirm → needs-confirmation status, file unmoved; with confirm → archived.
    - pytest: parked project `→ACTIVE` while WIP==max without force → needs-confirmation; with force → moved, WIP count reflects it.
    - pytest: stale mtime on save → 409, no move.

- [ ] **C.3** Task/intent save writes `status` as a label only — never moves the file. (deps: A.2, est: ~25m)
  - acceptance:
    - R-9.1 — any task `status` value is written; file never moves.
    - R-9.2 — task `status: DONE` marks done via existing bucketing; file stays in its project folder.
  - verify:
    - pytest: set task `status: DONE` → frontmatter updated, file path unchanged, intent bucketed done.

- [ ] **C.4** Confirm read-side drift semantics — `find_projects` unchanged; stored `status` surfaced as-is. (deps: A.3, est: ~20m)
  - acceptance:
    - R-10.1 — lifecycle bucket derived from folder; `find_projects` untouched.
    - R-10.2 — a project with `status` disagreeing with folder is bucketed by folder; stored status surfaced verbatim.
    - R-10.3 — drift reconciled only on next app-driven save; no background sweep exists.
  - verify:
    - pytest: place a project in `01-Active-Projects/` with frontmatter `status: DONE` → still counted active; output shows `status: DONE` label.
    - grep: confirm no scheduler/daemon scans for status/folder drift.

## Unit 7: Web edit pages — config-driven selects (`apps/backend/app/src/`)

- [ ] **D.1** `client.ts`: add `ClassificationVocab` interface + `getClassification()`; widen `NewProjectRequest.type` to `string`. (deps: B.1, est: ~25m)
  - acceptance:
    - R-13.3 — create payload `type` accepts any vocabulary string (no `'A'|'B'|'C'` union).
    - (typed accessor for `GET /api/classification`.)
  - verify: `tsc`/build passes; `getClassification()` returns the five arrays.

- [ ] **D.2** `ProjectEditPage.tsx`: inline `ENUM_OPTIONS` seeded from `getClassification()`; selects for all 5 keys; preserve out-of-list value; confirm-on-archive / WIP UX. (deps: D.1, est: ~70m)
  - acceptance:
    - R-12.1 — project dimension dropdowns populate from `GET /api/classification`.
    - R-12.3 — a current value not in the vocab is preserved as a synthetic selected option.
    - R-12.4 — dimension keys stay optional/deletable (not added to mandatory/locked set).
    - R-12.5 — changing `status` to an archive/move value prompts confirmation before saving (archive, and WIP-exceeding reactivation).
    - R-12.6 — implemented inline (no shared cross-page helper).
  - verify: manual + component test — select renders config values; out-of-list value retained; `→DONE` shows confirm dialog; cancel aborts save.

- [ ] **D.3** `NoteEditPage.tsx`: inline `ENUM_OPTIONS` for `mode`/`focus_risk`/`status` only; status label-only (no move UX). (deps: D.1, est: ~40m)
  - acceptance:
    - R-12.2 — task dropdowns limited to mode/focus_risk/status from the API.
    - R-12.3 — out-of-list value preserved.
    - R-12.4 — keys optional/deletable.
    - R-12.6 — inline, no shared helper.
  - verify: task edit shows 3 dimension selects, no type/horizon; saving `status` never triggers a move.

- [ ] **D.4** `NewProjectModal.tsx`: replace A/B/C segmented control with config-driven `type` select; add optional `mode`/`horizon`/`focus_risk`/`status` selects. (deps: D.1, est: ~45m)
  - acceptance:
    - R-13.1 — `type` is a dropdown from `GET /api/classification`.
    - R-13.2 — optional `mode`/`horizon`/`focus_risk`/`status` selectable.
    - R-13.3 — selected values sent in the create request.
  - verify: create flow posts chosen dimensions; project page reflects them.

## Unit 8: Integration & regression

- [ ] **E.1** Full-suite green + backward-compat sweep. (deps: C.2, D.2, D.3, D.4, est: ~30m)
  - acceptance:
    - R-4.4 — no `schema_version` bump introduced.
    - existing vault (no `[classification]`, files without dimension keys) reads without error across `GET /api/home`, project, and note endpoints.
  - verify:
    - `make test-cli` green (new + existing).
    - smoke: load home/project/note with a minimal pre-existing vault → no errors; dimensions render as unset.
```
