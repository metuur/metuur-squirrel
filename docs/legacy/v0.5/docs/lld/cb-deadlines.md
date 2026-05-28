# /sq-deadlines — Low-Level Design

## Architecture

Single new file: `commands/sq-deadlines.md`.
Pattern identical to `commands/sq-chunk.md` and `commands/sq-estimate.md`:

1. Parse `$ARGUMENTS` for optional `--level <levels>` flag
2. Read `vault_path` from `~/.squirrel/config.toml` via inline Python
3. Discover `deadline_scanner.py` via the standard search path
4. Run `python3 <script> --vault <vault_path> [--level <levels>] --pretty`
5. Render JSON output as a grouped urgency table
6. Handle non-zero exit: surface error, stop

## Constraints

- No new lib files — wraps `deadline_scanner.py` only
- `allowed-tools: [Bash]` — same as `/sq-chunk`, `/sq-estimate`
- Must not write to vault or any state file

## Key Decisions

- **No `--project` filter**: `deadline_scanner.py` does not support it; adding
  it would require modifying the script (out of scope for this change).
- **`--pretty` always on**: human rendering needs the indented JSON.
- **Empty-level suppression**: if a level has zero items, skip its section header entirely.

## Out of Scope

- Snooze/dismiss actions (daemon's responsibility)
- Per-project filtering
- LLM summarization of deadlines
