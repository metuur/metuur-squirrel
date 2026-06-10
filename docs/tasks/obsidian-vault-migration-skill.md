# Task: Obsidian → squirrel-vault migration skill

- **Source research:** `.uncle-dev/research/2026-06-10-obsidian-vault-migration-skill.md`
- **Date:** 2026-06-10
- **Scope decisions (user-confirmed):**
  - Copy mode — source Obsidian vault is never modified
  - Migrated projects land in `02-Parking-Lot/` by default (`--dest active` opts into `01-Active-Projects/`)
  - Auto heuristics + dry-run plan; apply only after explicit confirmation
  - Target folders follow the code readers (`status_aggregator.py:60-63`), not the sq-init scaffold drift

## Stories

- [x] **S1 — `apps/cli/lib/vault_migrator.py`**: two-phase plan/apply engine
  - `plan`: scan source vault → mapping plan (JSON + human summary). Heuristics:
    - top-level folder with notes → project (`02-Parking-Lot/<TAG>/`), folder-note becomes project page body; tag sanitized to `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`
    - notes inside a project folder (recursive, flattened) → intents `<TAG>-NOTE-NNN.md` with required frontmatter (id, project, status, created, tags); original frontmatter keys preserved, status values normalized; `migrated_from` records source relpath
    - daily-notes folders (name matches daily/diario, or ≥80% date-named files) → copied as-is to `04-Daily/`
    - root-level loose notes → captures `99-Resources/Inbox/UNFILED-NNN.md`, continuing existing numbering
    - non-md attachments → `99-Resources/Obsidian-Attachments/<relpath>` (wikilinks resolve by filename)
    - skipped: hidden dirs, `.obsidian`, `.trash`, `.squirrel`
  - `apply`: execute a saved plan; never overwrite existing target files (skip + report); re-runnable
  - Refuses a source that is already a squirrel vault; documented exit codes
  - Acceptance: unit tests cover plan mapping, apply output frontmatter, UNFILED numbering continuation, no-overwrite idempotency, source-untouched, and migrated projects visible to `aggregate_status()` in the `parking` bucket
- [x] **S2 — skill + command**: `agent-pack/skills/migrate-vault/SKILL.md` (`squirrel-migrate-vault`) and `agent-pack/commands/sq-migrate-vault.md`, following the new-project pattern (skill delegates all I/O to the lib; dry-run plan shown and confirmed before apply)
- [x] **S3 — registration**: add `vault_migrator` to `apps/cli/pyproject.toml` py-modules; targeted tests green
