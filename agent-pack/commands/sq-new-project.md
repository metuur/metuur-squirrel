---
description: Creates a new project in the vault (project page + optional intent). Usage: /sq-new-project [TAG] [--type A|B|C] [--deadline YYYY-MM-DD] [--description "..."] [--first-intent-tag TAG-X-001 --first-intent-title "..." [--first-intent-filename FILENAME]] [--stakeholders "@a,@b"] [--vault NAME] [--force]
allowed-tools: [Bash, Read, Write]
---

# /sq-new-project

Creates a new project in the vault with arguments `$ARGUMENTS`.

Invokes the `squirrel-new-project` skill, which:

1. Validates the project tag (UPPERCASE, no intent scheme).
2. Validates `type` (A/B/C), `deadline` (ISO date), and the optional first-intent tag.
3. Checks the vault's WIP capacity (rejects if at the cap unless `--force`).
4. Writes `01-Active-Projects/<TAG>/<TAG>.md` (project page) and, if requested,
   `01-Active-Projects/<TAG>/<FIRST-INTENT>.md` from `templates/intent.md`.
   The intent's filename is taken from `--first-intent-filename` if provided;
   if omitted, it uses the value of `--first-intent-tag` as the filename.
5. Doesn't overwrite — if the project exists, it exits with an error.

## Examples

```
/sq-new-project MYAPP --type C
/sq-new-project VISA-FAMILIA-2027 --type B --deadline 2027-01-15
/sq-new-project SIDEPROJECT-WIDGET --type C --first-intent-tag SIDEPROJECT-WIDGET-SETUP-001 --first-intent-title "Initialize repo and CI"
/sq-new-project SIDEPROJECT-WIDGET --type C --first-intent-tag SIDEPROJECT-WIDGET-SETUP-001 --first-intent-title "Initialize repo and CI" --first-intent-filename SETUP-INIT
```

## Notes

- `--first-intent-filename` is optional. When omitted, the first intent's file is named the same as `--first-intent-tag` (e.g. `SIDEPROJECT-WIDGET-SETUP-001.md`).
- When provided, it controls the filename independently of the tag. It must match the pattern `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` (e.g. `SETUP-INIT`, `PHASE1`).

If required fields are missing (`tag`, `type`), the skill asks before writing.
