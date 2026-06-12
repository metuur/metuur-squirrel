# Obsidian → squirrel-vault Migration — Low-Level Design

> _Backfilled from the as-built `apps/cli/lib/vault_migrator.py`._

## Architecture

A single stdlib-only Python module is the engine; an agent skill/command is the
thin operator UI. The engine is two pure-ish phases joined by a JSON plan
document, so the scan (read-only) and the write are separable and the plan is
reviewable between them.

```
[/sq-migrate-vault <source> [--dest active] [--vault NAME]]   (agent command)
   └ skill: agent-pack/skills/squirrel-migrate-vault/SKILL.md
       │ delegates all I/O to the lib (no inline file ops)
       ▼
vault_migrator.py
   plan  : build_plan(source, vault_path, dest_bucket) -> plan(dict)
           format_plan(plan) -> human summary           (shown for confirmation)
   apply : apply_plan(plan) -> summary(dict)            (writes into vault_path)
       │
       ▼
   squirrel vault (target)
     02-Parking-Lot/<TAG>/<TAG>.md          project page (from folder-note)
     02-Parking-Lot/<TAG>/<TAG>-NOTE-NNN.md flattened intents
     04-Daily/<copied as-is>                daily notes
     99-Resources/Inbox/UNFILED-NNN.md      loose root notes
     99-Resources/Obsidian-Attachments/...  non-md files
```

## Public API (`vault_migrator.py`)

- `build_plan(source: Path, vault_path: Path, dest_bucket: str) -> dict` — read-only
  scan; returns a plan mapping every source item to a target with its render kind.
  `dest_bucket` is `02-Parking-Lot` (default) or `01-Active-Projects`.
- `apply_plan(plan: dict) -> dict` — executes a saved plan; returns a summary
  (written / skipped / copied counts and paths). Never overwrites; skip + report.
- `format_plan(plan: dict) -> str` — human-readable rendering of a plan for the
  confirmation step.
- `main() -> int` — CLI entrypoint exposing `plan` and `apply` subcommands.

## Mapping heuristics

| Source shape | Target | Notes |
|--------------|--------|-------|
| Top-level folder containing notes | project `<dest_bucket>/<TAG>/` | `TAG` sanitized to `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` via `_sanitize_tag` |
| Folder-note `Foo/Foo.md` | becomes the project page body `<TAG>/<TAG>.md` | `_render_project_page` |
| Other notes in a project folder (recursive, flattened) | `<TAG>-NOTE-NNN.md` intents | required frontmatter injected; `_render_intent` |
| Daily-notes folder (`daily`/`diario` name, or ≥80% date-named files) | copied as-is into `04-Daily/` | `_is_daily_dir` |
| Loose notes at vault root | `99-Resources/Inbox/UNFILED-NNN.md` captures | numbering continues existing inbox via `_next_unfiled_start` |
| Non-markdown files | `99-Resources/Obsidian-Attachments/<relpath>` | wikilinks resolve by filename |
| Hidden dirs, `.obsidian`, `.trash`, `.squirrel` | skipped | `_SKIP_DIRS` |

### Frontmatter handling

- `_OWNED_KEYS = {id, project, status, created, tags, type, migrated_from}` are
  normalized/replaced by the migrator; every other original key is passed through
  verbatim.
- `status` values are normalized through `_STATUS_MAP` (e.g. `completed`→`done`,
  `wip`→`in-progress`, `waiting`→`blocked`).
- `migrated_from` records the source relpath for provenance.
- `created` is derived from existing frontmatter or the file's timestamp
  (`_note_created`).
- `_ensure_h1` guarantees each rendered note has an H1 title.

## Write safety

- All writes go through `fs_atomic.atomic_write_text` (write-temp + fsync +
  rename), shared with the rest of the CLI.
- `_write_new` / `_copy_new` refuse to overwrite: if the target exists, the item
  is recorded as **skipped** in the summary and left as-is, making `apply`
  re-runnable.
- The source root is only ever read; no source path is opened for writing.

## CLI exit codes

| Code | Meaning |
|------|---------|
| 0 | success |
| 2 | `NO_CONFIG` — no config / no default vault |
| 3 | `VAULT_MISSING` — target vault path missing on disk |
| 4 | `VAULT_UNKNOWN` — named vault not found |
| 5 | `SOURCE_INVALID` — source missing, equal to target, or already a squirrel vault |
| 6 | `PLAN_INVALID` — plan file missing or malformed |
| 7 | `NOTHING_TO_MIGRATE` |

## Registration & operator surface

- `vault_migrator` is listed in `apps/cli/pyproject.toml` `py-modules`.
- `agent-pack/skills/squirrel-migrate-vault/SKILL.md` (skill `squirrel-migrate-vault`)
  and `agent-pack/commands/sq-migrate-vault.md` follow the `new-project` pattern:
  the skill delegates all filesystem work to the lib, renders the dry-run plan,
  and requires explicit confirmation before calling `apply`.

## Constraints

- Copy-only: the source vault must be unmodified after any invocation.
- Target-folder names follow the code readers (`status_aggregator.py:60-63`), not
  the `sq-init` scaffold, to avoid drift between writers and readers.
- Stdlib only (`argparse`, `json`, `pathlib`, `re`, `shutil`); the only intra-repo
  deps are `intent_parser.parse_frontmatter` and `fs_atomic.atomic_write_text`.

## Key Decisions

- **Two-phase plan/apply over one-shot import** — the JSON plan is the review
  surface; it lets the skill show exactly what will happen and lets `apply` be a
  pure execution of an approved decision.
- **Skip-not-overwrite on apply** — makes the operation safe to retry after a
  partial failure and prevents clobbering anything the user already curated.
- **Flatten project sub-notes to numbered intents** — Squirrel's project model is
  flat (`<TAG>-NOTE-NNN.md`), so nested Obsidian structure is linearized rather
  than preserved as folders.

## Out of Scope

- In-place move/rename of the source.
- Merge of colliding target files.
- Link rewriting beyond filename-resolvable wikilinks.
- Ongoing/two-way sync.
