---
description: Migrates an existing Obsidian vault into the squirrel-vault format (dry-run plan + confirm; source is never modified). Usage: /sq-migrate-vault SOURCE_PATH [--dest parking|active] [--vault NAME]
allowed-tools: [Bash, Read, AskUserQuestion]
---

# /sq-migrate-vault

Migrates the Obsidian vault at `$ARGUMENTS` into the squirrel vault.

Optional arguments:
- `--dest parking|active` — where migrated projects land (default `parking` → `02-Parking-Lot/`)
- `--vault NAME` — target a specific vault (default vault if omitted)

Invokes the `squirrel-migrate-vault` skill, which:

1. Runs `lib/vault_migrator.py plan --source <path>` — a read-only scan that maps
   top-level folders → projects, folder-notes → project pages, notes → intents,
   daily folders → `04-Daily/`, loose notes → Inbox captures, attachments →
   `99-Resources/Obsidian-Attachments/`.
2. Shows the migration plan and asks for confirmation. Nothing is written yet.
3. On confirmation, runs `lib/vault_migrator.py apply` — writes converted notes
   into the squirrel vault. Never overwrites existing files; re-running is safe.

## Examples

```
/sq-migrate-vault ~/Documents/old-obsidian-vault
/sq-migrate-vault ~/notes --dest active
/sq-migrate-vault ~/notes --vault work
```

## Notes

- The source vault is read-only throughout — nothing is moved, edited, or deleted.
- Migrated projects default to the Parking Lot so the WIP cap (3) stays meaningful;
  promote the ones you're actively working on afterwards.
- If a source path is missing, ask the user for it before running anything.
