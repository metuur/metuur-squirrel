# Squirrel — Codex Agent Manifest

squirrel is a session-management plugin for engineers. It persists
cognitive state across sessions, projects, and air-gapped environments via a
Markdown vault. Scripts do all deterministic work; the agent only does judgment.

## Skill index

Skills are installed at `~/.codex/skills/`. Invoke them when the user's request
matches the trigger phrases below.

| Skill | Trigger phrases | File |
|---|---|---|
| `session-start` | "let's work on X", "let's pick up Y", "what was I doing", `/sq-start` | `session-start/SKILL.md` |
| `session-end` | "we're done for today", "shutdown", "I'm going to pause", `/sq-end` | `session-end/SKILL.md` |
| `brief` | "give me the brief", "status update", "summarize the project", `/sq-brief` | `brief/SKILL.md` |
| `capture` | "save this", "note this down", "save this", `/sq-capture` | `capture/SKILL.md` |
| `decision` | "we decided to use X", "we're going to do Y", `/sq-decision` | `decision/SKILL.md` |
| `where-am-i` | "what am I working on?", "where am I", `/sq-where-am-i` | `where-am-i/SKILL.md` |
| `sync-out` | "export context", "I need to take this to work", `/sq-sync-out` | `sync-out/SKILL.md` |
| `sync-in` | pastes a `<!-- SQUIRREL-PACKAGE` block, `/sq-sync-in` | `sync-in/SKILL.md` |
| `chunk-intent` | "break down intent X", "breaks this into chunks", `/sq-chunk-intent` | `chunk-intent/SKILL.md` |
| `task-initiation` | "I can't get started", "stuck", "paralysis", `/sq-task-initiation` | `task-initiation/SKILL.md` |
| `parakeet` | "what are my deadlines?", `/sq-parakeet` | `parakeet/SKILL.md` |
| `hyperfocus-guardian` | (auto-triggered by long sessions or drift signals) | `hyperfocus-guardian/SKILL.md` |

## Slash commands

Commands are installed at `~/.codex/commands/`. All are prefixed `/sq-`.

```
/sq-start [TAG]          — load project context
/sq-end [--quick]        — save shutdown notes
/sq-brief [TAG]          — 6-section project brief
/sq-status               — vault health dashboard
/sq-where-am-i           — focus snapshot
/sq-capture <content>    — save a note
/sq-decision <topic>     — record an ADR
/sq-chunk [N]h           — decompose task into chunks
/sq-estimate <time>      — focus-buffered time estimate
/sq-chunk-intent [TAG]   — decompose intent into chunks
/sq-task-initiation [TAG] — anti-paralysis protocols
/sq-parakeet             — deadline reminder with tone
/sq-deadlines            — deadline report by urgency
/sq-sync-out             — export context package
/sq-sync-in              — apply pasted package
/sq-recover              — recover interrupted session
/sq-dashboard            — generate HTML vault dashboard
```

## Configuration

`~/.squirrel/config.toml` must exist. Minimal example:

```toml
vault_path = "~/vault-squirrel"
environment_name = "personal"

[compliance]
strict = false
allowed_inbound_environments = ["personal", "work"]
```

Run `sq install --agent codex` to set up files.
Run `/sq-init` (or edit config manually) to configure the vault path.

## Scripts

All scripts are in `~/.codex/skills/<skill>/../../lib/` (relative to the skills tree,
or at the original repo path). Scripts are stdlib-only Python 3.9+.

| Script | Function |
|---|---|
| `status_aggregator.py` | Vault-wide project/intent status |
| `deadline_scanner.py` | Deadline urgency classification (6 levels) |
| `intent_parser.py` | Frontmatter + section parser for vault files |
| `switch_tracker.py` | Context-switch counter, focus_score |
| `estimate_buffer.py` | focus time multiplier |
| `chunk_helper.py` | Task decomposition into ≤50-min chunks |
| `session_scanner.py` | Recoverable session finder |
| `dashboard_generator.py` | HTML vault dashboard |
| `package_protocol.py` | Sync package generate/validate/apply |
