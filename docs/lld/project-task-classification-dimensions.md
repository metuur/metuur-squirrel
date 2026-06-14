# Project & Task Classification Dimensions — Low-Level Design

## Architecture

```
Classification Dimensions — touched components only
│
├── ~/.squirrel/config.toml                         [TOUCHED — user data]
│   └── [classification]
│         type       = [ ... ]
│         mode       = [ ... ]
│         horizon    = [ ... ]
│         focus_risk = [ ... ]
│         status     = [ ... ]
│
├── apps/cli/lib/config_loader.py                   [TOUCHED]
│   ├── DEFAULT_CLASSIFICATION: dict[str,list[str]]   [NEW] built-in defaults
│   └── get_classification(config_path=None) -> dict  [NEW]
│         # returns {type,mode,horizon,focus_risk,status: [...]}
│         # merges [classification] over DEFAULT_CLASSIFICATION per-key
│         # (a present key fully replaces its default list)
│
├── apps/cli/lib/classification.py                  [NEW — small pure module]
│   ├── PROJECT_DIMENSIONS = ("type","mode","horizon","focus_risk","status")
│   ├── TASK_DIMENSIONS    = ("mode","focus_risk","status")
│   ├── STATUS_FOLDER = { THE_THING:01-Active-Projects, ACTIVE:01-Active-Projects,
│   │                     COOLDOWN:01-Active-Projects, BLOCKED:01-Active-Projects,
│   │                     PARKED:02-Parking-Lot, DONE:06-Archive }
│   ├── normalize(value, allowed) -> str
│   │     # case/space-insensitive match into `allowed`;
│   │     # unmatched value returned verbatim (soft)
│   └── target_folder_for_status(status) -> str | None
│         # None when status is not a folder-driving value
│
├── apps/cli/lib/status_aggregator.py               [TOUCHED]
│   ├── analyze_project(): read dict gains mode/horizon/focus_risk;
│   │     `type` now read as taxonomy (no A/B/C semantics, no type/ tag)
│   └── finishing-tax critical alert (lines ~263-268)  [RE-HOMED]
│         # see Key Decision 4
│
├── apps/cli/lib/new_project_writer.py              [TOUCHED]
│   ├── _PROJECT_PAGE_TEMPLATE: drop A/B/C type line + type/{tipo} tag;
│   │     emit type/mode/horizon/focus_risk/status from config defaults
│   ├── _VALID_TIPOS / _validate_tipo                 [REMOVED]
│   └── project_status_move(vault, slug, new_status, *, force) [NEW]
│         # the risky write path — see Data flow below
│
├── apps/backend/server.py                          [TOUCHED]
│   ├── GET /api/classification                       [NEW]
│   │     # → { type:[...], mode:[...], horizon:[...],
│   │     #     focus_risk:[...], status:[...] }
│   ├── api_project_save (project edit save)          [SUPERSET]
│   │     # after writing frontmatter, if status changed AND
│   │     # target_folder_for_status(new) != current folder:
│   │     #   → require `confirm`/`force` per gate (archive / WIP)
│   │     #   → move dir, return new slug/path
│   └── api_note_save (task edit save)                [UNCHANGED move-wise]
│         # writes status as a label; never moves the file
│
└── apps/backend/app/src/                            [TOUCHED]
    ├── api/client.ts
    │     ├── ClassificationVocab interface           [NEW]
    │     ├── getClassification(): Promise<…>          [NEW]
    │     └── NewProjectRequest.type → string (was 'A'|'B'|'C')
    ├── pages/ProjectEditPage.tsx                     [TOUCHED]
    │     # ENUM_OPTIONS map seeded from /api/classification;
    │     # selects for all 5 keys; preserve out-of-list value;
    │     # confirm dialog when status change implies archive/move
    ├── pages/NoteEditPage.tsx                        [TOUCHED]
    │     # ENUM_OPTIONS for mode/focus_risk/status only; label-only status
    └── components/NewProjectModal.tsx                [TOUCHED]
          # A/B/C segmented control → config-driven `type` select
          # + optional mode/horizon/focus_risk/status selects
```

### Data flow — project status change that moves the folder

1. User changes `status` from `ACTIVE` to `DONE` on `ProjectEditPage` and clicks Save.
2. Frontend computes that the new status implies a folder move (`DONE` → `06-Archive/`). Because the target is the archive, it shows a **confirm-on-archive** dialog before any network call.
3. On confirm, `api.projectSave(slug, body, mtime, { status_move: true })` posts the edited body plus an explicit move acknowledgement.
4. Server `api_project_save`:
   1. Writes the edited frontmatter/body to the current file (atomic, mtime-checked → 409 on conflict, existing behavior).
   2. Reads the saved `status`, computes `target = target_folder_for_status(status)`.
   3. If `target` differs from the current top-level folder:
      - If `target == 06-Archive` and `confirm` not set → HTTP 409/428 asking for confirmation.
      - If `target == 01-Active-Projects` (re-activation) and WIP is at capacity and `force` not set → HTTP 409/428 asking for WIP confirmation.
      - Else move `<current>/<TAG>/` → `<target>/<TAG>/` atomically (directory rename within the vault), validated by `is_path_inside()`.
   4. Returns the new slug/relative path so the SPA can re-route.
5. The aggregator continues to bucket the project by its (now-updated) folder on the next `GET /api/home`; the stored `status` value rides along as a label.

### Data flow — task status change (no move)

1. User changes a task's `status` to `DONE` on `NoteEditPage` and clicks Save.
2. `api.noteSave` writes the frontmatter; **no folder logic runs**. The file stays in its project directory. `DONE` is read by the existing intent status bucketing (`status_aggregator.py:213-225`).

### Read-side reconciliation (drift)

- The aggregator's `find_projects` (`status_aggregator.py:50-95`) is **unchanged** — folder remains the read-time source of truth for the active/parking/archive bucket.
- The stored `status` value is surfaced as-is in `analyze_project`'s output. If an Obsidian hand-edit sets `status: DONE` while the folder is still `01-Active-Projects/`, the project still counts as active (folder wins) and shows the stale `DONE` label until the next app-driven save reconciles. This mirrors the lazy-cleanup pattern already used by manual-focus picks. No background sweep.

## Constraints

- **Python 3.9+**, stdlib only. `config_loader._load_toml` already covers `[section]` tables with inline string arrays on both the `tomllib` (3.11+) path and the 3.9/3.10 `_fallback_parse` (`config_loader.py:96-110`). `[classification]` uses exactly that subset — **no parser extension required** (add a fallback-parser test to lock it).
- **Frontmatter writes** go through the existing surgical/atomic `write_frontmatter` (`intent_parser.py:138-254`); only scalar upserts are needed for the five keys. No list-mutation of `tags` is required because the `type/{tipo}` tag is being removed, not rewritten.
- **Folder moves** are directory renames inside the vault, guarded by `is_path_inside()` (existing helper). No cross-device copy; rename is atomic on the same filesystem.
- **Soft validation everywhere** — no write path may reject an out-of-list value. UI is the only constraining surface and must preserve an out-of-list current value (existing pattern at `ProjectEditPage.tsx:207-209`).
- **No-cross-page-helper convention** — `ProjectEditPage.tsx` and `NoteEditPage.tsx` duplicate the property-editor logic by design. The `ENUM_OPTIONS` map and select rendering land inline in each file; do not extract a shared helper.
- **Backward compatibility** — absent `[classification]` → defaults; absent frontmatter key → `None`; existing vaults read without error. No `schema_version` bump (stays `"001"`).

## Key Decisions

1. **Config is the vocabulary source; built-in defaults are the floor.** `get_classification()` merges `[classification]` over `DEFAULT_CLASSIFICATION` per key — a present key *replaces* its default list (not merge-append), so the user can both extend and prune a vocabulary. Rejected: hardcoding lists in code (not user-editable, the explicit requirement); rejected: append-only merge (can't remove a value).

2. **New small module `classification.py` instead of scattering constants.** The dimension membership (`PROJECT_DIMENSIONS`/`TASK_DIMENSIONS`), the `STATUS_FOLDER` map, and `normalize()` are pure functions with no I/O, easy to unit-test, and shared by `new_project_writer`, `status_aggregator`, and `server`. Rejected: inlining the status→folder map in `server.py` (couples the move rule to the HTTP layer and hides it from CLI paths).

3. **`status` is canonical *intent*; folder is canonical *read bucket*; the save path keeps them in sync.** This avoids inverting the aggregator (which buckets by folder) while still letting the user drive lifecycle from metadata. Rejected: making the aggregator read `status` and ignore folders (large blast radius on WIP/dashboard, and breaks the move-folder muscle memory in Obsidian). Rejected: status as a pure sub-label with no move (contradicts the locked "status moves the file" decision).

4. **Re-home the `finishing-tax` critical alert onto `focus_risk`/`status`, do not silently drop it.** The current trigger (`priority == "finishing-tax"` AND `days_since_activity > 7` → `critical`, `status_aggregator.py:263-268`) depended on the importance tier vocabulary that is going away. Replacement trigger: a project with `focus_risk == DOPAMINE_LOW` (procrastination risk) OR `status == BLOCKED` that is stale `> 7` days raises the same `critical` alert. This keeps the staleness nudge alive under the new vocabulary. The exact predicate is implemented in `analyze_project` and covered by a test; if the user prefers full retirement, it is a one-line removal flagged in the plan.

5. **Drop `_VALID_TIPOS`/`_validate_tipo` and the `--type` CLI choice constraint.** `type` becomes free-text-from-vocabulary like the other dimensions. `create_project` accepts any `type` string; the template seeds it from `get_classification()["type"][0]`-style default or an explicit arg. Rejected: keeping A/B/C as a parallel hidden field (two importance concepts, exactly the collision we're removing).

6. **Confirm-on-archive and WIP-gate-on-reactivate are server-enforced, UI-prompted.** The server is the authority (returns a needs-confirmation response); the UI renders the dialog. This keeps the guard correct even for non-UI callers (CLI, future agents). Mirrors the existing create-time `WIP_CAPACITY` gate semantics (`new_project_writer` raises unless `force`).

7. **Tasks never carry `type`/`horizon`.** `TASK_DIMENSIONS` excludes them; the task edit page renders selects for only `mode`/`focus_risk`/`status`. A `type`/`horizon` key hand-added to a task is preserved (soft) but not offered as a managed dropdown.

## Out of Scope

- Driving focus recommendation, hyperfocus thresholds, shiny-object warnings, or dashboard hiding from the new dimensions (separate behavior-wiring change). Only `status`→folder and the alert re-homing are wired here.
- `RECURRING` status and any auto-generation of recurring projects (stays Areas + `frecuencia`).
- A settings-page editor for the vocabularies (this change reads them from `config.toml`; editing them is done in the file or deferred to a later settings-UI change).
- Migrating or rewriting any existing vault content (greenfield).
- Multi-value / tag-style classification per dimension.
- Background drift reconciliation between `status` and folder.
