---
name: squirrel-migrate-vault
description: Migrate an existing Obsidian vault's notes into the squirrel-vault format and structure. Use when the user says "migrate my obsidian vault", "import my notes", "convert my vault to squirrel", or invokes `/sq-migrate-vault`. Copy-only — the source vault is never modified. Always shows a dry-run migration plan first and writes only after the user confirms. Migrated projects land in `02-Parking-Lot/` by default (`--dest active` for `01-Proyectos-Activos/`). Accepts an optional `vault_name`; when omitted, writes to the default vault (R-7.1, R-7.3).
token_budget: 300
---

# squirrel-migrate-vault

## Purpose

Bring an existing Obsidian vault into squirrel without losing anything and without touching the original. The migrator maps free-form notes onto the structures squirrel's readers understand (projects, intents, captures, daily notes) so they show up in `/sq-status`, deadlines, and dashboards.

## When to invoke

- Explicit: `/sq-migrate-vault <source-path>`
- Implicit: the user mentions moving/importing/converting an existing Obsidian (or plain Markdown) vault into squirrel.

## Workflow

All file analysis and writes are delegated to `lib/vault_migrator.py`. Do not map or write notes manually.

### Step 1 — Plan (read-only dry run)

```bash
python3 ~/.claude/plugins/squirrel/lib/vault_migrator.py plan \
  --source "$SOURCE_PATH" \
  ${vault_name:+--vault "$vault_name"} \
  ${dest:+--dest "$dest"}
```

Exit codes: `0` plan saved · `2` no config · `3` vault path missing · `4` vault name unknown · `5` source invalid (missing, same as target, or already a squirrel vault) · `7` nothing to migrate.

The script prints a human-readable plan and saves the full plan to `~/.squirrel/migration-plan.json`. Mapping rules it applies:

- top-level folder with notes → project under the destination bucket; a folder-note (`Foo/Foo.md`) becomes the project page; other notes (recursive, flattened) become intents `<TAG>-NOTE-NNN.md`
- original frontmatter keys are preserved; `status` values are normalized (`Done`→`done`, `doing`→`in-progress`, …); `migrated_from` records the source path
- daily-notes folders → copied as-is to `04-Daily/`
- loose root notes → captures in `99-Resources/Inbox/` (continues `UNFILED-NNN` numbering)
- attachments → `99-Resources/Obsidian-Attachments/` (wikilinks keep resolving by filename)

### Step 2 — Confirm with the user

<!-- @spec migration: never write without explicit confirmation -->
Show the printed plan verbatim and ask the user to confirm. If they want changes (different destination bucket, skip a folder), re-run `plan` with adjusted flags — or tell them which folders to move/rename in the source before re-planning. Never edit the plan JSON by hand.

### Step 3 — Apply

Only after explicit confirmation:

```bash
python3 ~/.claude/plugins/squirrel/lib/vault_migrator.py apply
```

Exit codes: `0` applied · `5` source vanished · `6` plan file missing/invalid.

Apply never overwrites existing files — re-running is safe and reports skips. Report the summary (files written / skipped) and suggest `/sq-where-am-i` to see the migrated projects, plus promoting active ones out of the Parking Lot.

## Special modes / edge cases

- **Re-run after a partial migration**: just `plan` + `apply` again; existing files are skipped, only new notes land.
- **Source is already a squirrel vault**: the script refuses (`SOURCE_INVALID`). Suggest `squirrel vaults add` instead.
- **Huge vaults**: the plan output lists per-project counts; if the user balks, suggest migrating one folder at a time by pointing `--source` at a subfolder.

## Anti-patterns

- Don't write vault files directly — all writes go through `vault_migrator.py`.
- Don't apply without showing the plan and getting confirmation.
- Don't modify, move, or delete anything inside the source vault.
- Don't bypass the Parking-Lot default to "be helpful" — the WIP cap (3) counts all open projects.
