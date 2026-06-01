# Squirrel — Install Guide

> One-page overview of the installer: what it installs, where each component lands, and how the interactive TUI works.

For deep configuration details (GPG, compliance mode, multi-environment), see [`INSTALL.md`](INSTALL.md). For end-user usage, see [`docs/guides/getting-started.md`](docs/guides/getting-started.md).

---

## TL;DR

```bash
./install.sh           # interactive TUI — recommended
./install.sh --auto    # non-interactive, install everything for detected agents
./install.sh --help    # all flags
```

Per-agent shortcuts (scripted / CI):

```bash
./scripts/install-claude.sh
./scripts/install-codex.sh
./scripts/install-cursor.sh
./scripts/install-copilot.sh          # user-level (default)
./scripts/install-copilot.sh --workspace  # workspace-level (.github/)
./scripts/install-standalone.sh
```

---

## What gets installed

Five distinct components. Every installer installs **all** of them by default.

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. CANONICAL PLUGIN — the brains                                    │
│     ~/.claude/plugins/squirrel/                                      │
│       ├── skills/        (13 AI skill packs — capture, brief, ...)   │
│       ├── commands/      (20 slash commands: /sq-*)                  │
│       ├── lib/           (11 Python scripts — the deterministic ops) │
│       ├── hooks/         (proactive triggers, e.g., sync-in detect)  │
│       ├── templates/     (intent.md, package-out.md, dashboards)     │
│       └── .claude-plugin/plugin.json                                 │
├──────────────────────────────────────────────────────────────────────┤
│  2. AGENT INTEGRATION — varies per target                            │
│     Claude:    nothing extra (canonical IS the Claude install)       │
│     Codex:     ~/.codex/{skills,commands}/ + AGENTS.md patched       │
│     Cursor:    ~/.cursor/rules/squirrel/ + manual rule pointer       │
│     Copilot:   ~/.copilot/{agents,prompts,hooks}/ +                  │
│                copilot-instructions.md patched (user-level default)  │
│                OR .github/{agents,prompts,hooks}/ (--workspace)      │
│     Standalone: nothing                                              │
├──────────────────────────────────────────────────────────────────────┤
│  3. CLI ON PATH — the standalone terminal binary                     │
│     ~/.local/bin/squirrel  →  symlink to <repo>/squirrel             │
│     (use --prefix=PATH to install elsewhere)                         │
├──────────────────────────────────────────────────────────────────────┤
│  4. CONFIG SEED — your settings file                                 │
│     ~/.squirrel/config.toml  (copied from config/squirrel.toml.example│
│     if missing; existing config is preserved)                        │
├──────────────────────────────────────────────────────────────────────┤
│  5. macOS REMINDER DAEMON (macOS only, opt-in)                       │
│     ~/Library/LaunchAgents/org.squirrel.reminders.plist              │
│     Polls vault every 2h, sends critical-deadline notifications      │
└──────────────────────────────────────────────────────────────────────┘
```

### Why does Codex/Cursor also write to `~/.claude/plugins/squirrel/`?

That directory is the **canonical** install location. The slash commands use a `find` fallback to locate `lib/*.py` and always check there first. The directory is created automatically regardless of which agent you're installing for — you don't need Claude Code itself for it to work.

---

## The install flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   USER RUNS:  ./install.sh                                      │
│                                                                 │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────────────────────┐                               │
│   │  TTY check + preflight      │                               │
│   │  • Python 3.9+              │                               │
│   │  • Repo accessible          │                               │
│   │  • Detect ~/.claude, etc.   │                               │
│   └──────────────┬──────────────┘                               │
│                  │                                              │
│                  ▼                                              │
│   ┌─────────────────────────────┐                               │
│   │  INTERACTIVE TUI (6 steps)  │ ← skipped if --auto           │
│   │  1. Pick agents (multi)     │                               │
│   │  2. Copy vs symlink         │                               │
│   │  3. CLI on PATH?            │                               │
│   │  4. Config seed?            │                               │
│   │  5. macOS daemon?           │                               │
│   │  6. Summary + confirm       │                               │
│   └──────────────┬──────────────┘                               │
│                  │                                              │
│                  ▼                                              │
│   ┌─────────────────────────────┐                               │
│   │  EXECUTE (in order)         │                               │
│   │  1. Canonical install       │  python3 squirrel install     │
│   │  2. Agent integration       │  --agent <agent>              │
│   │  3. CLI symlink             │  ln -s ... ~/.local/bin/      │
│   │  4. Config seed             │  cp template ~/.squirrel/     │
│   │  5. macOS daemon            │  launchctl bootstrap ...      │
│   └──────────────┬──────────────┘                               │
│                  │                                              │
│                  ▼                                              │
│   ┌─────────────────────────────┐                               │
│   │  Per-agent next steps       │                               │
│   │  (restart agent, /sq-init,  │                               │
│   │   paste Cursor rule, etc.)  │                               │
│   └─────────────────────────────┘                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## TUI navigation

The TUI is **pure bash** — no `gum`, `dialog`, or other dependencies. Works on bash 3.2+ (macOS default).

| Key | Action |
|---|---|
| `↑` `↓` (or `j` `k`) | Move cursor |
| `SPACE` | Toggle selection (multi-select screens only) |
| `ENTER` | Confirm and advance |
| `b` (or `←` / `h`) | Go back to previous screen |
| `q` (or `Esc`) | Quit |

### Step 1 — Pick agents (multi-select)

```
── Step 1/6 — Which agents do you want to install Squirrel for? ──

  Pick one or more options. Press SPACE to toggle.

  ▶ [✓] Claude Code              ← cursor here
    [✓] Codex CLI
    [✓] Cursor
    [ ] Standalone CLI only

  SPACE toggle  ·  ↑/↓ move  ·  ENTER continue  ·  b back  ·  q quit
```

### Step 2 — Install method (single-select)

```
── Step 2/6 — Install method ──

  How should the files be installed on disk?

  ▶ Copy   — stable, won't change if you edit the repo (recommended)
    Symlink — auto-updates from repo on git pull (best for developers)
```

### Step 6 — Summary

```
── Step 6/6 — Summary ──

  Agents:           Claude Code, Codex CLI, Cursor
  Method:           copy
  CLI on PATH:      yes → ~/.local/bin/squirrel
  Config seed:      yes → ~/.squirrel/config.toml
  macOS daemon:     yes (launchd)
  Dry run:          no

  Proceed?
  ▶ Yes — install now
    No  — go back and change something
```

---

## File layout map

What lands where, for each combination of agent + components:

```
~/                                          (your home directory)
│
├── .claude/                                ⬅ Claude Code's home (auto-created)
│   └── plugins/
│       └── squirrel/                       ⬅ CANONICAL INSTALL — every script writes here
│           ├── .claude-plugin/
│           │   └── plugin.json
│           ├── skills/                     (13 skill packs)
│           ├── commands/                   (20 /sq-* commands)
│           ├── lib/                        (Python scripts)
│           ├── hooks/                      (hooks.json)
│           ├── templates/                  (note + dashboard templates)
│           ├── companions/                 (codex, cursor, macos-reminders)
│           └── squirrel                    (the CLI binary)
│
├── .codex/                                 ⬅ Only if --agent codex
│   ├── skills/                             (mirrors of skills/)
│   ├── commands/                           (mirrors of commands/*.md)
│   └── AGENTS.md                           (patched with Context Bridge block)
│
├── .copilot/                               ⬅ Only if --agent copilot (user-level)
│   ├── agents/                             (squirrel-<name>.agent.md files)
│   ├── prompts/                            (sq-<cmd>.prompt.md files)
│   ├── copilot-instructions.md            (Squirrel manifest block appended)
│   └── hooks/
│       └── squirrel.json                  (hook registration)
│
├── .cursor/                                ⬅ Only if --agent cursor
│   └── rules/
│       └── squirrel/                       (mirrors of skills/)
│
├── .local/bin/
│   └── squirrel                            ⬅ CLI symlink → <repo>/squirrel
│                                              (or wherever --prefix=PATH points)
│
├── .squirrel/                              ⬅ Your config
│   ├── config.toml                         (vault_path, environment_name, ...)
│   ├── state.json                          (created at runtime by /sq-start)
│   └── reminders-daemon.log                (macOS daemon log)
│
└── Library/LaunchAgents/                   ⬅ macOS only
    └── org.squirrel.reminders.plist
```

---

## How components talk to each other

```
   ┌────────────────────────────────────────────────────────────┐
   │  User in Claude Code / Codex / Cursor                      │
   └────────────────────────┬───────────────────────────────────┘
                            │ types /sq-where-am-i
                            ▼
   ┌────────────────────────────────────────────────────────────┐
   │  commands/sq-where-am-i.md   (slash command definition)    │
   └────────────────────────┬───────────────────────────────────┘
                            │ invokes skill
                            ▼
   ┌────────────────────────────────────────────────────────────┐
   │  skills/where-am-i/SKILL.md  (AI prompt + tool plan)       │
   └────────────────────────┬───────────────────────────────────┘
                            │ runs python3 lib/...
                            ▼
   ┌────────────────────────────────────────────────────────────┐
   │  lib/status_aggregator.py   (the brains — scans the vault) │
   └────────────────────────┬───────────────────────────────────┘
                            │ reads .md notes
                            ▼
   ┌────────────────────────────────────────────────────────────┐
   │  <vault>/  (your Markdown notes — the data)                │
   └────────────────────────────────────────────────────────────┘
```

---

## Flags cheat sheet

| Flag | What it does | Where it works |
|---|---|---|
| `--auto` | Skip the TUI, install for every detected agent | `install.sh` only |
| `--dry-run` | Preview every action without writing | all |
| `--link` | Symlink instead of copy (auto-update from repo) | all |
| `--yes` / `-y` | Accept all prompts (including macOS daemon) | all |
| `--no-config` | Skip seeding `~/.squirrel/config.toml` | all |
| `--no-cli` | Skip the `squirrel` CLI symlink | all |
| `--no-reminders` | Skip the macOS launchd daemon | all |
| `--prefix=PATH` | Install CLI symlink here (default `~/.local/bin`) | all |
| `--help` / `-h` | Print usage and exit | all |

---

## Common scenarios

### "Just install everything for Claude Code"

```bash
./scripts/install-claude.sh --yes
```

### "I want to see what would happen, no changes"

```bash
./install.sh --auto --dry-run --yes
```

### "I'm a developer, I want symlinks so `git pull` auto-updates"

```bash
./install.sh --auto --link --yes
```

### "Install for Claude + Codex but skip the macOS daemon"

Use the TUI:

```bash
./install.sh
# In step 1: toggle off Cursor and Standalone
# In step 5: pick "No — skip the daemon"
```

Or via flags:

```bash
./scripts/install-claude.sh --yes --no-reminders
./scripts/install-codex.sh  --yes --no-reminders --no-cli --no-config
```

### "Install only the CLI, no AI agent at all"

```bash
./scripts/install-standalone.sh --yes
```

---

## Uninstall map

| Component | Remove with |
|---|---|
| Canonical plugin | `rm -rf ~/.claude/plugins/squirrel/` |
| Codex integration | `rm -rf ~/.codex/skills/{brief,capture,…} ~/.codex/commands/sq-*.md` + edit `~/.codex/AGENTS.md` |
| Cursor integration | `rm -rf ~/.cursor/rules/squirrel/` + remove rule pointer in Cursor settings |
| Copilot integration (user) | `rm -rf ~/.copilot/agents/squirrel-* ~/.copilot/prompts/sq-*.prompt.md ~/.copilot/hooks/squirrel.json` + remove Squirrel block from `~/.copilot/copilot-instructions.md` |
| Copilot integration (workspace) | delete `.github/agents/squirrel-*`, `.github/prompts/sq-*.prompt.md`, `.github/hooks/squirrel.json`; remove Squirrel block from `.github/copilot-instructions.md` |
| CLI symlink | `rm ~/.local/bin/squirrel` |
| Config | `rm -rf ~/.squirrel/` ⚠ deletes your settings |
| macOS daemon | `bash <repo>/companions/macos-reminders/install.sh --uninstall` |

---

## Updating

If you installed with `--link`, just `git pull` in the repo — files are symlinks and refresh automatically.

If you copied (the default), re-run the installer:

```bash
git pull
./install.sh --auto --yes
```

Your `~/.squirrel/config.toml` and your vault are preserved across updates.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python3: command not found` | Install Python 3.9+ from [python.org](https://python.org/downloads), or `brew install python3` on macOS |
| `Cannot find <repo>/squirrel` | Run the installer from inside the repo, not from elsewhere |
| Slash commands don't appear in Claude Code | Restart Claude Code completely (close all windows) |
| `squirrel: command not found` after install | Add `~/.local/bin` to your `PATH` — the installer prints the exact line |
| Codex/Cursor commands fail with "script not found" | Canonical install at `~/.claude/plugins/squirrel/` is missing. Re-run any installer. |
| `Interactive mode requires a TTY` | You're piping stdin. Use `--auto` instead. |
| macOS daemon install fails | Check the log at `~/.squirrel/reminders-daemon.log` |
| TUI prints `^[[A` instead of moving cursor | You're using bash 3.2 in a terminal that's swallowing arrow keys. Use `j`/`k` (down/up) as alternatives. |

For deeper troubleshooting see [`INSTALL.md`](INSTALL.md).
