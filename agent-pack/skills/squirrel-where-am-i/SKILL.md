---
name: squirrel-where-am-i
description: Show "where was I?" — full vault status with recommended focus. Use when user runs /sq-where-am-i, asks "what was I doing", "what was I working on?", "where did I leave off", or at session start when the previous activity is unclear. Accepts an optional `vault_name` argument; when omitted, the default vault is used (R-7.1, R-7.3).
token_budget: 120
---

# squirrel:where-am-i (v0.3.0 — fully script-driven)

All logic, data collection, and formatting live in
`lib/where_am_i_formatter.py`. The skill is a single shell call.

## Workflow

Run the wrapper, passing `$vault_name` only if provided:

```bash
bash ~/.claude/plugins/squirrel/scripts/sq-where-am-i.sh "$vault_name"
```

Print the script's stdout to the user **verbatim** — do not paraphrase,
re-format, summarize, or add wording. The script already emits the
final human-readable text.

## Exit codes

- `0` — success, output already printed
- `2` — no config / no default vault → tell user to run `/sq-init`
- `3` — vault path on disk is missing → show the stderr message
- `4` — named vault not found → show the stderr message (lists valid names)

## Anti-patterns

- ❌ Don't read intent files, alerts, or deadlines directly — the script did it
- ❌ Don't write inside the vault (VAULT-007 — this skill is read-only)
- ❌ Don't extend or reformat the output — change `where_am_i_formatter.py` instead
