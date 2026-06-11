---
description: Processes a SQUIRREL package received by email/clipboard. Auto-detection too: if you paste a SQUIRREL-PACKAGE block, it triggers on its own.
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# /sq-sync-in

Applies the package pasted into the chat (or the last one saved in `<vault>/.squirrel/incoming/`).

Invokes the `squirrel-sync-in` skill, which:
1. Parses the SQUIRREL-PACKAGE block (start/end markers)
2. Validates the SHA-256 hash
3. Verifies that the `to` field matches this environment
4. For each file: checks for conflicts with the local vault
5. Shows the apply plan (a table of operations)
6. Shows diffs for conflicts/updates
7. Asks for confirmation (all / selective / cancel)
8. Applies operations atomically
9. Links new intents from Project Pages
10. Logs the application in `<vault>/.squirrel/applied/<timestamp>-<hash>.json`

Flags:
- `--dry-run`: only shows what would happen, without writing
- `--from-file <path>`: reads the package from a file instead of the clipboard/chat
- `--force-hash`: applies even if the hash doesn't match (dangerous)
- `--vault NAME`: operate on a specific vault (default if omitted)
