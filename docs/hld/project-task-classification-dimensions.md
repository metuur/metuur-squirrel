# Project & Task Classification Dimensions — High-Level Design

## Overview

Today a project carries one classification field with real semantics: `type`, constrained to the importance tier `A | B | C` (`apps/cli/lib/new_project_writer.py:59`, validated by `_validate_tipo`, mirrored into the `type/{tipo}` tag). Intents carry a soft `status` and `priority`. There is no way for the user to describe a project or task along the axes they actually use to decide *how* to work on it.

This change introduces **five user-defined classification dimensions** — `type`, `mode`, `horizon`, `focus_risk`, and `status` — whose allowed values live in `~/.squirrel/config.toml` under a `[classification]` table, so the user can edit the vocabularies without touching code. The dimensions are stored as plain YAML frontmatter on project and task files (visible and editable in Obsidian), surfaced as dropdowns in the web edit pages and the New Project modal, and validated *softly* (out-of-list values are preserved, never rejected).

One dimension — **project `status`** — is also a control surface: it drives the project's folder location. Setting a project's status to `PARKED` or `DONE` moves its folder to `02-Parking-Lot/` or `06-Archive/` on save; the active statuses keep it in `01-Active-Projects/`. This makes the existing folder-as-lifecycle convention editable from metadata while keeping the folder the read-time source of truth for the aggregator.

The architectural commitments: **the config file owns the vocabularies, the vault owns the values, validation is soft, and the folder stays canonical for lifecycle bucketing.** The frontmatter parser is untouched (it already accepts arbitrary flat keys), and because the vault is greenfield there is **no data migration**.

## Stakeholders & Impact

| Stakeholder | Today's pain | After this ships |
|---|---|---|
| Primary user (Javier) | Can only tag a project by `A/B/C` importance. No way to record what kind of work it is, the cognitive mode it demands, its time horizon, or its focus risk — the things that actually drive how to approach it. | Five dropdowns on every project (three on every task) capture `type`, `mode`, `horizon`, `focus_risk`, `status`. Picking `status: DONE` archives the project from the UI. The value lists are his to edit in `config.toml`. |
| Obsidian-only sessions | Frontmatter has no agreed classification vocabulary. | The five keys are plain frontmatter lines (`type: WORK`, `mode: DEEP_FOCUS`, …), readable, searchable, and editable directly in Obsidian. |
| Backend aggregator (`status_aggregator.py`) | `type` means importance tier; the `finishing-tax`/tier critical alert (`status_aggregator.py:263-268`) keys off `priority`. | `type` becomes the taxonomy; the importance words (`mission-critical`/`important`/`experimental`) become `type` values. The tier-based critical alert loses its trigger and is explicitly re-homed or retired (see Goal 8). |
| Frontend edit pages | `status` select is hardcoded to `['pending','wip','done','blocked','paused']`; project `type` is an A/B/C control at creation only. | Selects for all five dimensions populate from `GET /api/classification`, so editing `config.toml` changes the dropdowns. Out-of-list current values are preserved as synthetic options. |
| Future LLM agents reading the vault | No machine-readable classification beyond importance tier. | Five stable, parseable frontmatter keys with config-declared vocabularies become a consistent signal across the vault. |

## Goals

When this ships, the following are observable and true:

1. **Five classification dimensions exist as frontmatter**, with the value vocabularies declared in `~/.squirrel/config.toml` under `[classification]` (keys `type`, `mode`, `horizon`, `focus_risk`, `status`).
2. **The vocabularies are user-editable.** Editing the arrays in `config.toml` changes the allowed values everywhere (API, dropdowns, normalization) with no code change. When `[classification]` is absent, built-in code defaults apply (backward-compatible).
3. **The data contract is entity-specific.** Project pages carry all five (`type`, `mode`, `horizon`, `focus_risk`, `status`); tasks/intents carry three (`mode`, `focus_risk`, `status`) — never `type` or `horizon`.
4. **Validation is soft.** Values are normalized at read; an out-of-list value (e.g. a hand-edit in Obsidian) is preserved and surfaced, never rejected. The only place values are constrained is the UI `<select>`, which still preserves an out-of-list current value as a synthetic option.
5. **The backend exposes the vocabularies** via `GET /api/classification`, and both web edit pages plus the New Project modal populate their dropdowns from it rather than from hardcoded arrays.
6. **Project `status` drives folder location, kept in sync on save:** `THE_THING`/`ACTIVE`/`COOLDOWN`/`BLOCKED` → `01-Active-Projects/`, `PARKED` → `02-Parking-Lot/`, `DONE` → `06-Archive/`. A status whose target folder differs from the file's current folder moves the file on save.
7. **Task/intent `status` is a label only** — it never moves the file (a task lives inside its project folder; `DONE` just marks it done).
8. **The dropped A/B/C tier is reconciled.** `type` no longer means importance; the `type/{tipo}` tag mirror is removed; and the `finishing-tax`/tier-based critical alert at `status_aggregator.py:263-268` is explicitly re-homed (onto `focus_risk`/`status`) or retired — decided in the LLD, not left dangling.
9. **Archiving is intentional.** Moving a project to `06-Archive/` (status `DONE`) requires explicit confirmation in the UI before the move completes.
10. **WIP capacity is respected on re-activation.** A status change that would move a project *into* `01-Active-Projects/` while WIP is at capacity requires explicit confirmation, consistent with the existing create-time WIP gate.

## Non-Goals

Out of scope for this change:

- **Hard enum validation.** Values are never rejected on write; the config vocabularies drive UI guidance and normalization only.
- **A data migration.** The vault is greenfield (only `SCRATCH-PAD` exists). No existing files are rewritten.
- **Touching the frontmatter parser.** `parse_frontmatter` already accepts arbitrary flat keys; no parser change.
- **`RECURRING` as a status.** Recurrence stays the Areas concept (`03-Areas/` + `frecuencia`); it is not a value in the `status` vocabulary.
- **A background reconciliation sweep.** If a hand-edit in Obsidian desyncs `status` from folder, the folder wins for lifecycle bucketing and the next app-driven save reconciles. No daemon scans for drift.
- **New behavior wiring beyond folder-sync.** Driving focus selection, hyperfocus thresholds, or shiny-object warnings from the new dimensions is deferred to a separate change. This change captures and stores the data, exposes the vocabularies, and wires only the `status`→folder move and the alert re-homing.
- **Per-dimension multi-select.** Each dimension holds a single value.
- **Intent-level `type`/`horizon`.** Tasks never carry these two.

## Success Criteria

This is done when:

1. A `config.toml` with a `[classification]` table is read at startup; `GET /api/classification` returns the five arrays verbatim. Removing the table falls back to the built-in defaults and the endpoint still returns them.
2. On a project edit page, all five dimensions render as dropdowns whose options come from `GET /api/classification`; on a task edit page, only `mode`, `focus_risk`, `status` render as dropdowns.
3. Editing a project's `status` to `PARKED` and saving moves the project folder from `01-Active-Projects/<TAG>/` to `02-Parking-Lot/<TAG>/`, and the project drops out of the WIP count.
4. Editing a project's `status` to `DONE` prompts for confirmation; on confirm, the folder moves to `06-Archive/<TAG>/`; on cancel, nothing moves and the status is unchanged.
5. Editing a parked project's `status` to `ACTIVE` while WIP is at capacity prompts for confirmation (WIP gate); on confirm it moves into `01-Active-Projects/`.
6. Editing a task's `status` to `DONE` marks it done in frontmatter and does **not** move the file out of its project folder.
7. Hand-editing a project's `type` to a value not in the config list (in Obsidian) does not break any read; `GET /api/home` and the edit page both still load, showing the out-of-list value preserved.
8. A newly created project's page carries `type`, `mode`, `horizon`, `focus_risk`, `status` seeded from config defaults, with no `type/A`-style tag and no `A/B/C` constraint.
9. The `finishing-tax`/tier critical-alert path is either firing from its new trigger or is removed, and the existing CLI test suite (`make test-cli`) is green with new tests for config loading, soft normalization, and the status→folder move covering pass.

If all nine pass, the feature ships.
