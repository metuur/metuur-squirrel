# scripts/ — full-stack installers per agentic tool

> 💡 **Most users should run `./install.sh`** from the repo root instead. It's an interactive TUI that detects your installed agents, lets you pick targets, asks about options, shows a summary, and runs everything end-to-end. The per-agent scripts in this directory are for scripted / CI installs where you already know what you want.

Each script performs a **complete** install of every Squirrel component for one target. Pick the one that matches your AI assistant (or `standalone` for terminal-only use).

| Script | Target |
|---|---|
| `install-claude.sh` | Claude Code |
| `install-codex.sh` | OpenAI Codex CLI |
| `install-cursor.sh` | Cursor / VSCode |
| `install-standalone.sh` | Terminal only (no AI agent) |

## What every installer installs

| Component | Path |
|---|---|
| **Skills** (13) — AI prompts | inside the canonical plugin dir + agent dir |
| **Slash commands** (20) — `/sq-*` | inside the canonical plugin dir + agent dir |
| **Python lib** (11 scripts) — the brains | `~/.claude/plugins/squirrel/lib/` |
| **Hooks** (`hooks.json`) | `~/.claude/plugins/squirrel/hooks/` |
| **Templates** (intent.md, package-out.md, dashboards) | `~/.claude/plugins/squirrel/templates/` |
| **Plugin manifest** (`plugin.json`) | `~/.claude/plugins/squirrel/.claude-plugin/` |
| **Standalone CLI** — `squirrel` binary | `~/.local/bin/squirrel` (or `--prefix=PATH`) |
| **Config file** — `~/.squirrel/config.toml` | seeded from template if missing |
| **macOS reminder daemon** — launchd | `~/Library/LaunchAgents/org.squirrel.reminders.plist` (macOS only, opt-in prompt) |

### Plus agent-specific integration

| Script | Extra |
|---|---|
| `install-claude.sh` | Plugin is auto-discovered by Claude Code (no extra step). |
| `install-codex.sh` | Skills → `~/.codex/skills/`, commands → `~/.codex/commands/`, `~/.codex/AGENTS.md` patched with "Context Bridge" block. |
| `install-cursor.sh` | Skills → `~/.cursor/rules/squirrel/`. Prints a rule-pointer line for you to paste in Cursor → Settings → Rules for AI. |
| `install-standalone.sh` | None (the CLI symlink is the integration). |

> 💡 The canonical install at `~/.claude/plugins/squirrel/` is created by **every** script, even if you don't use Claude Code. This is intentional: the slash commands and skills include a `find` fallback that looks there for `lib/*.py`. Without it, Codex / Cursor commands cannot find the scripts. The directory is created automatically — you don't need Claude Code installed for it to be used.

## Quick start

From the repository root:

```bash
./scripts/install-claude.sh             # full install for Claude Code
./scripts/install-codex.sh              # full install for Codex CLI
./scripts/install-cursor.sh             # full install for Cursor
./scripts/install-standalone.sh         # full install for terminal-only use
```

Add `--help` to any script for inline help.

## Flags

| Flag | Effect | Applies to |
|---|---|---|
| `--link` | Symlink files (so repo edits pick up automatically) instead of copying | all |
| `--dry-run` | Print every action without writing anything | all |
| `--yes`, `-y` | Non-interactive — accept all prompts (including macOS daemon install) | all |
| `--no-config` | Skip seeding `~/.squirrel/config.toml` | all |
| `--no-cli` | Skip symlinking `squirrel` into `~/.local/bin` | all |
| `--no-reminders` | Skip the macOS launchd daemon install | all |
| `--prefix=PATH` | Where to put the CLI symlink (default: `~/.local/bin`) | all |
| `--help`, `-h` | Print usage and exit | all |

## Prerequisites (auto-checked)

- **Python 3.9 or higher** on PATH (`python3 --version`)
- Running from inside the squirrel repository (the script finds the `squirrel` CLI at the repo root)

The destination directory for your agent (`~/.claude/`, `~/.codex/`, `~/.cursor/`) does **not** need to exist beforehand — the scripts create it and warn you if the agent itself isn't installed yet.

## Verification

After install, every script prints what it installed and the next steps. To verify the install programmatically:

```bash
# Canonical install exists
ls ~/.claude/plugins/squirrel/lib/status_aggregator.py

# CLI is on PATH (you may need to source ~/.zshrc first)
squirrel --help

# Config exists
cat ~/.squirrel/config.toml

# (macOS only) Reminder daemon loaded
launchctl list | grep org.squirrel.reminders
```

## Updating

If you installed with `--link` (symlinks), pull from git and you're done. If you copied (the default), re-run the install script — files are replaced, your config and vault are preserved.

```bash
git pull
./scripts/install-claude.sh    # or your agent's installer
```

## Uninstalling

| Component | How to remove |
|---|---|
| Canonical plugin | `rm -rf ~/.claude/plugins/squirrel/` |
| Agent integration (Codex) | `rm -rf ~/.codex/skills/{brief,capture,...} ~/.codex/commands/sq-*.md` and remove the "Context Bridge" block from `~/.codex/AGENTS.md` |
| Agent integration (Cursor) | `rm -rf ~/.cursor/rules/squirrel/` and remove the rule pointer from Cursor settings |
| CLI symlink | `rm ~/.local/bin/squirrel` |
| Config | `rm -rf ~/.squirrel/` ⚠ deletes your settings |
| macOS daemon | `bash <repo>/companions/macos-reminders/install.sh --uninstall` |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python3 not found` | Install Python 3.9+ from python.org, or `brew install python3` on macOS |
| `Cannot find <repo>/squirrel` | Run the script from inside the squirrel repo, not from elsewhere |
| Slash commands don't appear in Claude Code | Restart Claude Code completely (close all windows) |
| `squirrel: command not found` | Add `~/.local/bin` to your `PATH` (the script prints the exact line) |
| Codex / Cursor commands fail with "script not found" | The canonical install at `~/.claude/plugins/squirrel/` must exist. Re-run the installer. |
| macOS daemon install fails | Check log at `~/.squirrel/reminders-daemon.log` |

For deeper troubleshooting see [`INSTALL.md`](../INSTALL.md) and the user guide at [`docs/guides/getting-started.md`](../docs/guides/getting-started.md).
