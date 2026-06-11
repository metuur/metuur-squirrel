---
description: Recovers the context of a forgotten session (without /sq-end). Uses session-manifest.jsonl or Claude history. Usage: /sq-recover [--scope TAG]
allowed-tools: [Bash, Read, Write]
---

# /sq-recover

Arguments: `$ARGUMENTS`

Optional arguments:
- `--vault NAME` — operate on a specific vault (default if omitted)

Recovers a lost session (when `/sq-end` was forgotten).

Invokes the `squirrel-recover` skill with the received arguments.
