---
description: Generates a SQUIRREL package to manually transfer to the other environment (personal↔work) via email or clipboard.
allowed-tools: [Read, Glob, Grep, Bash]
---

# /sq-sync-out

Generates a package to transfer to the other environment. Arguments: $ARGUMENTS

Invokes the `squirrel:sync-out` skill, which:
1. Determines the scope (intent / project / research / decisions / manual)
2. Collects files from the local vault
3. Runs a compliance check (secret scanning, address validation)
4. Composes a Markdown package with header, SHA-256 hash, payload
5. Shows the package on screen
6. Offers: copy to clipboard / open mailto: / save to file / just show
7. Logs the export in `<vault>/.squirrel/outgoing/log.jsonl`

Valid scopes:
- `--scope=<TAG>` — a specific intent
- `--scope=<PROJECT>:research` — all of a project's research
- `--scope=<PROJECT>:decisions` — decisions only
- `--scope=<PROJECT>:*` — the entire project
- `--since=<DATE>` — modified since a date
- `--manual` — interactive selection

Additional flags:
- `--encrypt` — pass through GPG (if configured)
- `--no-shutdown-notes` — exclude shutdown notes (lighter package)
- `--vault NAME` — operate on a specific vault (default if omitted)
