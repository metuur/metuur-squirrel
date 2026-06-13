# Obsidian → squirrel-vault Migration — EARS Specifications

> _Backfilled from the as-built `apps/cli/lib/vault_migrator.py`._

## Unit 1: Two-phase engine & safety

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL provide a `plan` phase that scans a source vault read-only and produces a JSON migration plan mapping every source item to a Squirrel target, without writing to either vault. |
| R-1.2 | THE SYSTEM SHALL provide an `apply` phase that executes a saved plan by writing converted notes into the target Squirrel vault. |
| R-1.3 | THE SYSTEM SHALL NOT modify, move, rename, or delete any file in the source vault during either phase. |
| R-1.4 | WHEN `apply` encounters a target path that already exists, THE SYSTEM SHALL skip that item, leave the existing file unchanged, and record it as skipped in the summary. |
| R-1.5 | THE SYSTEM SHALL perform every target write via an atomic write helper (write-temp, fsync, rename). |
| R-1.6 | WHEN `apply` is run a second time on the same plan, THE SYSTEM SHALL write zero new files and report each item as skipped (re-runnable / idempotent). |

## Unit 2: Mapping heuristics

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN a top-level source folder contains notes, THE SYSTEM SHALL map it to a project under `02-Parking-Lot/<TAG>/` by default, or under `01-Active-Projects/<TAG>/` when `--dest active` is given. |
| R-2.2 | THE SYSTEM SHALL sanitize each project tag to match `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`. |
| R-2.3 | WHEN a source folder contains a folder-note (`Foo/Foo.md`), THE SYSTEM SHALL use that note as the project page body. |
| R-2.4 | THE SYSTEM SHALL map other notes inside a project folder (recursively, flattened) to intents named `<TAG>-NOTE-NNN.md`. |
| R-2.5 | WHEN a source folder's name matches `daily`/`diario` or at least 80% of its files are date-named, THE SYSTEM SHALL copy it as-is into `04-Daily/`. |
| R-2.6 | THE SYSTEM SHALL map loose notes at the source vault root to captures `99-Resources/Inbox/UNFILED-NNN.md`, continuing the existing inbox numbering. |
| R-2.7 | THE SYSTEM SHALL copy non-Markdown files to `99-Resources/Obsidian-Attachments/<relpath>` so filename-based wikilinks resolve. |
| R-2.8 | THE SYSTEM SHALL skip hidden directories and the `.obsidian`, `.trash`, and `.squirrel` directories. |

## Unit 3: Frontmatter normalization

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL inject the required frontmatter keys (`id`, `project`, `status`, `created`, `tags`) on each migrated intent. |
| R-3.2 | THE SYSTEM SHALL preserve every original frontmatter key it does not own, passing it through verbatim. |
| R-3.3 | THE SYSTEM SHALL normalize `status` values through a fixed map (e.g. `completed`→`done`, `wip`→`in-progress`, `waiting`→`blocked`). |
| R-3.4 | THE SYSTEM SHALL record the source relative path in a `migrated_from` frontmatter key. |
| R-3.5 | THE SYSTEM SHALL ensure each rendered note has an H1 title, deriving one from the filename when absent. |

## Unit 4: Validation & exit codes

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the source path is missing, equals the target vault, or is already a Squirrel vault, THE SYSTEM SHALL refuse to proceed and exit with `SOURCE_INVALID` (5) without writing. |
| R-4.2 | WHEN no config or default vault exists, THE SYSTEM SHALL exit with `NO_CONFIG` (2). |
| R-4.3 | WHEN the target vault path is missing on disk, THE SYSTEM SHALL exit with `VAULT_MISSING` (3); WHEN a named vault is not found, THE SYSTEM SHALL exit with `VAULT_UNKNOWN` (4). |
| R-4.4 | WHEN a plan file is missing or malformed, THE SYSTEM SHALL exit with `PLAN_INVALID` (6). |
| R-4.5 | WHEN a valid plan contains nothing to migrate, THE SYSTEM SHALL exit with `NOTHING_TO_MIGRATE` (7). |
| R-4.6 | WHEN a migration completes successfully, THE SYSTEM SHALL exit `0`. |

## Unit 5: Operator surface (skill/command)

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL expose the migration via the `/sq-migrate-vault` command and `squirrel-migrate-vault` skill, with the skill delegating all filesystem I/O to `vault_migrator.py`. |
| R-5.2 | WHEN the user invokes the command, THE SYSTEM SHALL show the dry-run plan (`format_plan`) and require explicit confirmation before running `apply`. |
| R-5.3 | THE SYSTEM SHALL register `vault_migrator` as a CLI module so the engine is callable from the packaged CLI. |
| R-5.4 | WHEN a migration has been applied, THE SYSTEM SHALL leave the migrated projects discoverable by `aggregate_status()` in the `parking` bucket. |
