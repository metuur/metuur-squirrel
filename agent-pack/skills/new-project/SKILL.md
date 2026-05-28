---
name: squirrel-new-project
description: Scaffold a new project in the vault. Creates the project page (and optionally a first intent) under `01-Proyectos-Activos/<TAG>/`. Use when the user says "create a new project", "nuevo proyecto", "agregar proyecto", or invokes `/sq-new-project`. Refuses to overwrite an existing project and refuses to exceed the WIP cap unless `--force` is passed. Accepts an optional `vault_name`; when omitted, writes to the default vault (R-7.1, R-7.3).
token_budget: 200
---

# squirrel:new-project (v0.1.0 — script-driven)

All validation and writes live in `lib/new_project_writer.py`. This skill
parses the user's request, builds the argument list, runs the script, and
prints its stdout verbatim.

## Required inputs

Ask the user for any missing field before running:

- **tag** — project tag (UPPERCASE, e.g. `MYAPP`, `VISA-FAMILIA`). Must not match
  the intent-tag schema (4 parts ending in 3 digits).
- **tipo** — `A` (mission-critical), `B` (important), `C` (experimental).

## Optional inputs

- **deadline** — ISO date `YYYY-MM-DD`
- **stakeholders** — comma-separated list (e.g. `@alice,@bob`)
- **description** — one-line summary that goes under the H1 in the project page
- **first-intent-tag** — full intent tag like `MYAPP-SETUP-001`. If provided,
  the script also writes the first intent file from `templates/intent.md`.
- **first-intent-title** — used only with `first-intent-tag`
- **vault_name** — pick a non-default vault
- **force** — set when the user explicitly accepts going over WIP cap

## Workflow

```bash
bash ~/.claude/plugins/squirrel/scripts/sq-new-project.sh \
  --tag "$tag" \
  --tipo "$tipo" \
  ${deadline:+--deadline "$deadline"} \
  ${stakeholders:+--stakeholders "$stakeholders"} \
  ${description:+--description "$description"} \
  ${first_intent_tag:+--first-intent-tag "$first_intent_tag"} \
  ${first_intent_title:+--first-intent-title "$first_intent_title"} \
  ${vault_name:+--name "$vault_name"} \
  ${force:+--force}
```

Print the script's stdout verbatim. Do not paraphrase or extend it.

## Exit codes

- `0` — success, output printed
- `2` — no config → tell user to run `/sq-init`
- `3` — vault path on disk is missing → show stderr
- `4` — vault name unknown → show stderr (lists valid names)
- `5` — invalid project tag → show stderr, ask for a corrected tag
- `6` — project already exists → show stderr; offer `/sq-start <TAG>` instead
- `7` — WIP at capacity → relay the count, ask if user wants `--force` or to
  park an existing project first
- `8` — validation error (tipo / deadline / first intent) → show stderr, fix
  the offending field and re-ask

## Anti-patterns

- ❌ Don't write any vault files directly — the script does it
- ❌ Don't bypass the WIP-cap check silently; surface it and require explicit `--force`
- ❌ Don't extend or reformat the script's stdout — change `new_project_writer.py`
- ❌ Don't propose a first intent unless the user asked for one
