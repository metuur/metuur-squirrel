# Project & Task Classification Dimensions — EARS Specifications

Arrow of intent: HLD → LLD → **EARS** → code/tests. To change a behavior, edit the matching requirement here first.

## Unit 1: Config-defined vocabularies

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL read classification vocabularies from `~/.squirrel/config.toml` under a `[classification]` table with the keys `type`, `mode`, `horizon`, `focus_risk`, and `status`, each an inline array of strings. |
| R-1.2 | WHERE a `[classification]` key is present in `config.toml`, THE SYSTEM SHALL use its array verbatim as the allowed values for that dimension, fully replacing the built-in default for that key. |
| R-1.3 | IF the `[classification]` table or a given key is absent, THE SYSTEM SHALL fall back to the built-in default vocabulary for that dimension. |
| R-1.4 | THE SYSTEM SHALL ship built-in defaults equal to: `type` = WORK, SIDE_PROJECT, PERSONAL, FAMILY, HEALTH, FINANCE, LEARNING, mission-critical, important, experimental, ADMINISTRATIVE; `mode` = DEEP_FOCUS, EXECUTION, RESEARCH, ADMIN, URGENT, MAINTENANCE; `horizon` = MICRO, SHORT, MEDIUM, LONG, PERMANENT; `focus_risk` = DOPAMINE_HIGH, DOPAMINE_LOW, HYPERFOCUS_RISK, CONTEXT_HEAVY, EASY_RESTART; `status` = THE_THING, ACTIVE, COOLDOWN, PARKED, BLOCKED, DONE. |
| R-1.5 | THE SYSTEM SHALL load the `[classification]` table using the existing config TOML loader on both the `tomllib` (Python 3.11+) and fallback (3.9/3.10) paths, without extending the parser. |
| R-1.6 | IF the `[classification]` table is malformed or unreadable, THE SYSTEM SHALL fall back to the built-in default vocabularies and SHALL NOT fail vault resolution or other config reads. |

## Unit 2: Classification API

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL expose `GET /api/classification` that returns a JSON object with arrays for `type`, `mode`, `horizon`, `focus_risk`, and `status`. |
| R-2.2 | WHEN `GET /api/classification` is called, THE SYSTEM SHALL return the effective vocabularies (config values where present, built-in defaults otherwise). |
| R-2.3 | THE SYSTEM SHALL resolve the vocabularies per the active vault/config context for the request, consistent with how other endpoints resolve config. |

## Unit 3: Frontmatter data contract

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL treat `type`, `mode`, `horizon`, `focus_risk`, and `status` as project-page frontmatter dimensions. |
| R-3.2 | THE SYSTEM SHALL treat `mode`, `focus_risk`, and `status` as task/intent frontmatter dimensions, and SHALL NOT offer `type` or `horizon` as managed dimensions on tasks. |
| R-3.3 | THE SYSTEM SHALL read these dimension values into the project/intent model surfaced by `analyze_project` (and the project/note detail payloads). |
| R-3.4 | WHERE a dimension key is absent from a file, THE SYSTEM SHALL treat its value as unset (null) and SHALL NOT error. |
| R-3.5 | THE SYSTEM SHALL preserve any dimension key that is not in the managed set for an entity (e.g. a hand-added `type` on a task) without rewriting or removing it. |

## Unit 4: Soft validation & normalization

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN reading a dimension value, THE SYSTEM SHALL normalize it case- and whitespace-insensitively against the dimension's allowed values. |
| R-4.2 | IF a dimension value does not match any allowed value, THE SYSTEM SHALL preserve and surface the original value unchanged and SHALL NOT reject the read or the file. |
| R-4.3 | THE SYSTEM SHALL NOT reject any frontmatter write on the basis of an out-of-vocabulary dimension value. |
| R-4.4 | THE SYSTEM SHALL NOT bump the vault `schema_version` for the introduction of these dimensions. |

## Unit 5: Project `type` taxonomy replaces the A/B/C tier

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL treat project `type` as a taxonomy value drawn from the `type` vocabulary, and SHALL NOT constrain it to `A`/`B`/`C`. |
| R-5.2 | WHEN creating a project, THE SYSTEM SHALL NOT emit a `type/{value}` tag derived from `type`. |
| R-5.3 | THE SYSTEM SHALL remove the `_VALID_TIPOS` / `_validate_tipo` constraint and the CLI `--type` choice restriction so any vocabulary `type` value is accepted. |
| R-5.4 | THE SYSTEM SHALL retain the importance words `mission-critical`, `important`, and `experimental` as selectable `type` values in the default vocabulary. |

## Unit 6: New project scaffolding

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | WHEN a project is created, THE SYSTEM SHALL seed its page frontmatter with `type`, `mode`, `horizon`, `focus_risk`, and `status` keys. |
| R-6.2 | WHERE the creation request does not specify a dimension, THE SYSTEM SHALL seed that dimension from a configured default value (e.g. `status` = ACTIVE) and SHALL NOT seed an out-of-vocabulary value. |
| R-6.3 | THE SYSTEM SHALL create the project in `01-Active-Projects/` when the seeded/requested `status` maps to the active folder. |

## Unit 7: Project status drives folder location

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL map project `status` to a vault folder: `THE_THING`, `ACTIVE`, `COOLDOWN`, `BLOCKED` → `01-Active-Projects/`; `PARKED` → `02-Parking-Lot/`; `DONE` → `06-Archive/`. |
| R-7.2 | WHEN a project edit is saved and the new `status` maps to a folder different from the project's current top-level folder, THE SYSTEM SHALL move the project directory to the target folder. |
| R-7.3 | WHEN moving a project directory, THE SYSTEM SHALL validate the source and target paths with `is_path_inside()` before any move and SHALL perform the move atomically within the vault. |
| R-7.4 | WHEN a project directory is moved, THE SYSTEM SHALL return the project's new slug/relative path so the client can re-route. |
| R-7.5 | WHEN the new `status` maps to the same folder as the current location, THE SYSTEM SHALL write the status value and SHALL NOT move the directory. |
| R-7.6 | WHERE `status` is set to a value not present in the `status` vocabulary, THE SYSTEM SHALL write the value as a label and SHALL NOT move the directory. |
| R-7.7 | IF the target folder already contains a directory with the project's name, THE SYSTEM SHALL NOT move or overwrite it and SHALL respond with a conflict, leaving both the file contents and current location intact. |

## Unit 8: Archive confirmation & WIP re-activation gate

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | IF a project status change would move the project into `06-Archive/` (status `DONE`) and the request does not carry an explicit confirmation, THE SYSTEM SHALL NOT move the directory and SHALL respond indicating confirmation is required. |
| R-8.2 | WHEN the user confirms an archive move, THE SYSTEM SHALL complete the move to `06-Archive/`. |
| R-8.3 | IF a project status change would move the project into `01-Active-Projects/` while WIP is at capacity and the request does not carry an explicit force/confirmation, THE SYSTEM SHALL NOT move the directory and SHALL respond indicating WIP-capacity confirmation is required. |
| R-8.4 | WHEN the user confirms a re-activation that exceeds WIP capacity, THE SYSTEM SHALL complete the move into `01-Active-Projects/`. |
| R-8.5 | WHEN a project is moved out of `01-Active-Projects/`, THE SYSTEM SHALL no longer count it toward the WIP count (consistent with the folder-counted WIP invariant). |

## Unit 9: Task status is a label only

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | WHEN a task/intent edit is saved with any `status` value, THE SYSTEM SHALL write the value to the task's frontmatter and SHALL NOT move the task file. |
| R-9.2 | WHEN a task `status` is `DONE`, THE SYSTEM SHALL mark the task done via the existing intent status bucketing and SHALL keep the file inside its project folder. |

## Unit 10: Read-side reconciliation (drift)

| ID     | EARS statement |
|--------|----------------|
| R-10.1 | THE SYSTEM SHALL continue to determine a project's lifecycle bucket (active / parking / archive) from its folder location, leaving `find_projects` unchanged. |
| R-10.2 | WHERE a project's stored `status` disagrees with its folder (e.g. after an Obsidian hand-edit), THE SYSTEM SHALL bucket the project by its folder and SHALL surface the stored `status` value as-is. |
| R-10.3 | THE SYSTEM SHALL reconcile a drifted `status`/folder pair only on the next app-driven save of that project, and SHALL NOT run a background sweep to detect or fix drift. |

## Unit 11: Re-homed staleness alert

| ID     | EARS statement |
|--------|----------------|
| R-11.1 | THE SYSTEM SHALL remove the `finishing-tax`/importance-tier dependency from the critical staleness alert. |
| R-11.2 | WHEN a project is stale (no activity for more than 7 days) and carries `focus_risk` = `DOPAMINE_LOW` or `status` = `BLOCKED`, THE SYSTEM SHALL raise a `critical` staleness alert equivalent to the prior nudge. |
| R-11.3 | THE SYSTEM SHALL NOT raise the old `priority == "finishing-tax"` alert, since that vocabulary no longer drives `type`. |

## Unit 12: Web edit pages — config-driven selects

| ID     | EARS statement |
|--------|----------------|
| R-12.1 | THE SYSTEM SHALL populate the project edit page's dimension dropdowns (`type`, `mode`, `horizon`, `focus_risk`, `status`) from `GET /api/classification`. |
| R-12.2 | THE SYSTEM SHALL populate the task edit page's dimension dropdowns (`mode`, `focus_risk`, `status` only) from `GET /api/classification`. |
| R-12.3 | WHERE a file's current dimension value is not in the fetched vocabulary, THE SYSTEM SHALL preserve it as a synthetic selected option rather than dropping it. |
| R-12.4 | THE SYSTEM SHALL keep the dimension keys optional (deletable) on the edit pages and SHALL NOT add them to the mandatory/locked key set. |
| R-12.5 | WHEN the user changes a project's `status` to a value that implies a folder move, THE SYSTEM SHALL prompt for confirmation before saving when the move targets `06-Archive/` (archive) or when re-activation would exceed WIP capacity. |
| R-12.6 | THE SYSTEM SHALL implement the dimension selects inline in both `ProjectEditPage.tsx` and `NoteEditPage.tsx`, honoring the no-cross-page-helper convention (no shared extracted helper). |

## Unit 13: New Project modal

| ID     | EARS statement |
|--------|----------------|
| R-13.1 | THE SYSTEM SHALL replace the New Project modal's A/B/C `type` segmented control with a `type` dropdown populated from `GET /api/classification`. |
| R-13.2 | THE SYSTEM SHALL allow the New Project modal to optionally set `mode`, `horizon`, `focus_risk`, and `status` from config-driven dropdowns. |
| R-13.3 | THE SYSTEM SHALL send the selected dimension values in the create-project request, and the create payload's `type` field SHALL accept any vocabulary string (no longer constrained to `A`/`B`/`C`). |
