# v0.2 — Four Shippable Units

> Working artifact: `.uncle-dev/specs/2026-05-24-v02-four-units.md`
> Requirements distributed into: `attention-specs.md` · `brief-specs.md` · `integrations-specs.md` · `session-specs.md`

## Lenses

**Who is affected:**
- Primary: ADHD developer using Claude Code + Markdown vault (PARA structure)
- Secondary: macOS system (launchd daemon, Unit 2); agent sessions reading recovered manifests (Unit 4)

**Pain today:**
1. Nothing nudges the user when Claude is closed — deadlines only surface if a Claude session is already open
2. `/sq-status` ignores `status_aggregator.py` — script produces JSON, command ignores it
3. `chunk_helper.py` and `estimate_buffer.py` are CLI-only — no slash command access during sessions
4. Forgetting `/sq-end` causes a session to be permanently lost — no recovery path

**What changes after this ships:**
- Deadline nudges fire proactively via macOS notifications even with Claude closed
- `/sq-status` reflects real vault state from `status_aggregator.py`
- Chunking and estimation are available mid-session as slash commands
- A forgotten session can be partially recovered within 72 h

## Intent

**Must be true when this ships:**
- User who closes Claude still receives a critical-deadline notification within the configured workday window
- `/sq-status` output is derived from `status_aggregator.py --json`
- `/sq-chunk` and `/sq-estimate` work inside a Claude session without leaving the terminal
- `/sq-recover` within 72 h of a lost session produces a 5-line summary and asks what to do with it

**Must NOT change:**
- No MCP server
- No subagent path for `/sq-recover` — `claude -p` is the only LLM mechanism
- No `sq` CLI as a prerequisite — daemon shells directly to scripts
- No React SPA
- Compliance mode continues to gate corporate data before any LLM call

## Details

**Hard constraints:**
- macOS surfaces (daemon, osascript) are opt-in — must not break non-macOS
- Daemon lives in `companions/macos-reminders/`
- LLM calls via `claude -p` only (shell-out, print mode)
- Recovery cache keyed by JSONL content hash at `vault/.squirrel/llm-cache/{hash}.md`
- `PostToolUse:Edit` hook writes manifest at `vault/.squirrel/session-manifest.jsonl`
- Workday window + dialog cap ported from `personal-initiative-tracker/server.py:244-277`

**Out of scope:**
`sq` CLI binary · subagents · `/sq-deadlines` · Dataview templates · HTML dashboard · React SPA · schema plugin · Linux daemon · manifest rotation · `repo_path` migration

## Requirements

| ID | Spec ref | EARS statement |
|----|----------|----------------|
| R-1.1 | BRIEF-003 | WHEN `/sq-status` is invoked, THE SYSTEM SHALL execute `python3 lib/status_aggregator.py --json` and render its output |
| R-1.2 | BRIEF-006 | WHEN `status_aggregator.py` exits non-zero, THE SYSTEM SHALL surface the error and exit without crashing |
| R-2.1 | ATTN-009 | WHEN `deadline_scanner.py` returns `critical` or `urgent` items, THE SYSTEM SHALL display a macOS notification with "Focus now", "Snooze", "Dismiss" |
| R-2.2 | ATTN-010 | WHILE the daemon is running, THE SYSTEM SHALL suppress notifications outside the configured workday window |
| R-2.3 | ATTN-010 | IF the per-window dialog cap is reached, THE SYSTEM SHALL suppress further notifications until the next window |
| R-2.4 | INT-010 | WHEN `/sq-reminders-install` runs, THE SYSTEM SHALL register the launchd plist and start the daemon |
| R-2.5 | INT-011 | WHEN `/sq-reminders-uninstall` runs, THE SYSTEM SHALL unload the service and remove the plist |
| R-2.6 | ATTN-011 | WHERE the host OS is not macOS, THE SYSTEM SHALL skip installation and log a no-op message |
| R-3.1 | ATTN-012 | WHEN `/sq-chunk` is invoked, THE SYSTEM SHALL execute `python3 lib/chunk_helper.py` and display the breakdown |
| R-3.2 | ATTN-013 | WHEN `/sq-estimate` is invoked, THE SYSTEM SHALL execute `python3 lib/estimate_buffer.py` and display buffered estimates |
| R-4.1 | SESSION-007 | WHEN `/sq-recover` runs, THE SYSTEM SHALL read `session-manifest.jsonl` (primary) or `~/.claude/projects/*.jsonl` (fallback, 72 h) |
| R-4.2 | SESSION-008 | WHEN recovering, THE SYSTEM SHALL exclude sessions not in `allowed_inbound_environments` |
| R-4.3 | SESSION-009 | WHEN summarising, THE SYSTEM SHALL shell out to `claude -p` and cache by JSONL content hash |
| R-4.4 | SESSION-010 | WHERE `compliance_mode` is enabled, THE SYSTEM SHALL redact corporate data before `claude -p` |
| R-4.5 | SESSION-011 | WHEN `PostToolUse:Edit` fires, THE SYSTEM SHALL append a manifest entry to `session-manifest.jsonl` |
| R-4.6 | SESSION-012 | WHEN recovery completes, THE SYSTEM SHALL present: append-to-shutdown / inbox / project / raw / discard |
