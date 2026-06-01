# GitHub Copilot Agent Integration — EARS Specifications

## Unit 1: CLI surface — `squirrel install --agent copilot`

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL accept `copilot` as a value for the `--agent` argument of `squirrel install`, in addition to the existing `claude`, `codex`, `cursor`, `standalone`. |
| R-1.2 | THE SYSTEM SHALL list `copilot` in `squirrel install --help` output alongside the other agent choices. |
| R-1.3 | WHEN `squirrel install --agent copilot` is invoked without `--workspace`, THE SYSTEM SHALL install Copilot integration into user-level locations under `$COPILOT_HOME` (default `~/.copilot/`). |
| R-1.4 | WHEN `squirrel install --agent copilot --workspace` is invoked, THE SYSTEM SHALL install Copilot integration into workspace-level locations under `<repo-root>/.github/`. |
| R-1.5 | IF `--workspace` is passed AND the current working directory is not inside a git repository (`git rev-parse --show-toplevel` non-zero), THE SYSTEM SHALL exit non-zero with stderr message naming the missing repo context. |
| R-1.6 | THE SYSTEM SHALL preserve the existing behaviour of `--agent {claude,codex,cursor,standalone}` — no observable change for those branches. |
| R-1.7 | THE SYSTEM SHALL run `install_canonical()` (full plugin dir → `~/.claude/plugins/squirrel/`) before `install_agent_integration("copilot")`, identical to the Codex/Cursor order in `agent-pack/scripts/_lib.sh:99–128`. |

## Unit 2: Wrapper script `install-copilot.sh`

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL provide an executable shell script at `agent-pack/scripts/install-copilot.sh` mirroring the shape of `install-codex.sh`. |
| R-2.2 | THE SYSTEM SHALL accept the same flag surface as `install-codex.sh`: `--link`, `--dry-run`, `--no-config`, `--no-cli`, `--no-reminders`, `--yes`/`-y`, `--prefix=PATH`, `-h`/`--help`. |
| R-2.3 | THE SYSTEM SHALL additionally accept `--workspace` to switch the destination from user-level to workspace-level. |
| R-2.4 | WHEN `install-copilot.sh` runs without `--no-cli`, THE SYSTEM SHALL symlink `squirrel` into `$CLI_PREFIX` (default `~/.local/bin`) using `install_cli_to_path()` from `_lib.sh`. |
| R-2.5 | WHEN `install-copilot.sh` runs without `--no-config`, THE SYSTEM SHALL seed `~/.squirrel/config.toml` from the template using `install_config()`. |
| R-2.6 | WHEN `install-copilot.sh` runs without `--no-reminders` AND the platform is macOS, THE SYSTEM SHALL invoke the macOS reminder daemon installer using `install_macos_daemon()`. |
| R-2.7 | WHEN any non-zero exit occurs from `install_canonical`, `install_agent_integration`, or any post step, THE SYSTEM SHALL propagate the exit code unchanged and SHALL NOT continue subsequent steps. |
| R-2.8 | THE SYSTEM SHALL print a final summary block listing what was installed and the next-step hint (mirroring lines 53–73 of `install-codex.sh`). |

## Unit 3: Skill files

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN installing skills for the user-level Copilot integration, THE SYSTEM SHALL place one file per skill at `~/.copilot/agents/squirrel-<skill-name>.agent.md` (or `$COPILOT_HOME/agents/...` if `COPILOT_HOME` is set). |
| R-3.2 | WHEN installing skills for the workspace-level Copilot integration, THE SYSTEM SHALL place one file per skill at `<repo-root>/.github/agents/squirrel-<skill-name>.agent.md`. |
| R-3.3 | THE SYSTEM SHALL source skill bodies from the canonical install at `~/.claude/plugins/squirrel/skills/<skill-name>/SKILL.md` (or, equivalently, the in-repo source `agent-pack/skills/<skill-name>/SKILL.md` if installing from the repo). |
| R-3.4 | IF the canonical skill body's frontmatter is not compatible with the documented Copilot agent-file schema, THE SYSTEM SHALL prepend a Copilot-compatible YAML frontmatter block (rendered from `agent-pack/companions/copilot/frontmatter-template.yaml`) and SHALL leave the body text unchanged. |
| R-3.5 | WHEN `--link` is passed, THE SYSTEM SHALL create symlinks (`ln -s`) from the Copilot destinations to the canonical source files, instead of copying, so that edits to canonical files propagate without reinstalling. |
| R-3.6 | THE SYSTEM SHALL NOT create per-skill files for skills whose source directory name begins with `{` (template placeholders), matching the existing logic in `apps/cli/squirrel:412–414`. |
| R-3.7 | THE SYSTEM SHALL be idempotent: re-running the install SHALL overwrite existing skill files in place and SHALL NOT create duplicates or leave orphans from a prior install of a now-removed skill. |

## Unit 4: Slash-command (prompt) files

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN installing slash commands for the user-level Copilot integration, THE SYSTEM SHALL place one file per command at `~/.copilot/prompts/sq-<command>.prompt.md`. |
| R-4.2 | WHEN installing slash commands for the workspace-level Copilot integration, THE SYSTEM SHALL place one file per command at `<repo-root>/.github/prompts/sq-<command>.prompt.md`. |
| R-4.3 | THE SYSTEM SHALL source command bodies from `agent-pack/commands/sq-*.md` (or the equivalent canonical install path). |
| R-4.4 | THE SYSTEM SHALL preserve command body text unchanged. If the body lacks the Copilot-required prompt-file frontmatter fields (`description`, `name`, `agent`, `model`, `tools`, `argument-hint`), THE SYSTEM SHALL prepend a generated frontmatter block. |
| R-4.5 | WHEN `--link` is passed, THE SYSTEM SHALL symlink Copilot prompt files to the canonical command sources instead of copying. |
| R-4.6 | THE SYSTEM SHALL be idempotent across re-runs (R-3.7 semantics apply). |

## Unit 5: Copilot manifest (`copilot-instructions.md`)

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | WHEN installing for user-level Copilot integration, THE SYSTEM SHALL ensure `~/.copilot/copilot-instructions.md` contains a block beginning with the marker `# Squirrel — Copilot Agent Manifest`. |
| R-5.2 | IF `~/.copilot/copilot-instructions.md` already exists AND already contains the `# Squirrel — Copilot Agent Manifest` marker, THE SYSTEM SHALL skip the patch (no rewrite, no duplicate block). |
| R-5.3 | IF `~/.copilot/copilot-instructions.md` exists but lacks the marker, THE SYSTEM SHALL append the manifest block after a single blank line, preserving all prior file content. |
| R-5.4 | IF `~/.copilot/copilot-instructions.md` does not exist, THE SYSTEM SHALL create it containing only the manifest block. |
| R-5.5 | WHEN installing for workspace-level Copilot integration, THE SYSTEM SHALL apply R-5.1 through R-5.4 against `<repo-root>/.github/copilot-instructions.md`. |
| R-5.6 | THE SYSTEM SHALL render the manifest block from a single source-of-truth template (analogous to `_CODEX_AGENTS_BLOCK` referenced near `apps/cli/squirrel:364–382`). |
| R-5.7 | THE SYSTEM SHALL log to stdout one of `created`, `patched`, or `skipped (already present)` for the manifest step. |

## Unit 6: Hooks registration

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | WHEN installing for user-level Copilot integration, THE SYSTEM SHALL write a single hooks-registration file at `~/.copilot/hooks/squirrel.json` (or whatever filename the Copilot loader schema requires). |
| R-6.2 | WHEN installing for workspace-level Copilot integration, THE SYSTEM SHALL write the same hooks file at `<repo-root>/.github/hooks/squirrel.json`. |
| R-6.3 | THE SYSTEM SHALL register hook entries for the following Copilot events, mapped one-to-one to the Squirrel hooks defined in `agent-pack/hooks/hooks.json`: `sessionStart` → SessionStart, `userPromptSubmitted` → UserPromptSubmit, `sessionEnd` (or `agentStop` if `sessionEnd` is not loaded for the user's surface) → Stop, `postToolUse` → PostToolUse:Edit. |
| R-6.4 | THE SYSTEM SHALL NOT register Copilot-only events (`subagentStart`, `subagentStop`, `errorOccurred`, `permissionRequest`, `notification`, `preCompact`, `postToolUseFailure`) in this change; they may be added in a follow-up. |
| R-6.5 | THE SYSTEM SHALL overwrite the entire `squirrel.json` file on each install (generated content); it SHALL NOT attempt to merge with user-edited entries in the same file. |
| R-6.6 | IF a hooks file exists at the destination path AND contains hooks not owned by Squirrel, THE SYSTEM SHALL print a warning naming the file and SHALL NOT overwrite — the user is responsible for relocating Squirrel's hooks to a Squirrel-owned filename. |

## Unit 7: Hook adapter (INT-007 preservation)

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL ship two adapter shell scripts under `agent-pack/companions/copilot/`: `hook-adapter.sh` (env-vars + CLI args delivery) and `hook-adapter-stdin.sh` (JSON-on-stdin delivery). |
| R-7.2 | WHEN a Copilot hook fires AND the adapter is invoked, THE ADAPTER SHALL export the following environment variables before exec'ing the inline bash body: `EVENT`, `PROJECT`, `TIMESTAMP`, and (for the `userPromptSubmitted` event only) `USER_PROMPT`. |
| R-7.3 | THE ADAPTER SHALL derive `PROJECT` by reading the active project tag from `~/.squirrel/state.json` (or legacy `~/.squirrel/state/<vault>.json`), defaulting to the empty string if unresolvable. |
| R-7.4 | THE ADAPTER SHALL derive `TIMESTAMP` as ISO-8601 UTC via `date -u +%Y-%m-%dT%H:%M:%SZ`. |
| R-7.5 | THE ADAPTER SHALL derive `EVENT` as the Squirrel-side event name (`SessionStart`, `UserPromptSubmit`, `Stop`, `PostToolUse`), NOT the Copilot-side name — the bash bodies copied from `hooks.json` expect Squirrel names. |
| R-7.6 | IF stdin contains a JSON payload AND the env vars are not pre-populated by the Copilot loader, THE STDIN ADAPTER SHALL parse the payload (using `python3 -c` or `jq`, whichever is more portable) and extract the four contract fields before exec'ing the body. |
| R-7.7 | THE ADAPTER SHALL NOT modify the inline bash bodies copied from `agent-pack/hooks/hooks.json`. The bodies are run as-is via `bash -c`. |
| R-7.8 | IF either adapter cannot derive `EVENT` for any reason, THE ADAPTER SHALL exit zero without invoking the body (silent skip), and SHALL log a one-line message to stderr naming the missing field. Hooks MUST NOT cause Copilot to error. |

## Unit 8: Manifest writer compatibility

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | WHEN the `postToolUse` Copilot hook fires for an edit-class tool, THE SYSTEM SHALL invoke `apps/cli/lib/manifest_writer.py` via the same `find` lookup the Claude hook uses today (`agent-pack/hooks/hooks.json:49`). |
| R-8.2 | THE SYSTEM SHALL NOT modify the `session-manifest.jsonl` row schema (`timestamp, cwd, file, event, session`) to accommodate Copilot. Rows written from Copilot use the same shape as rows written from Claude. |
| R-8.3 | IF `manifest_writer.py` cannot be located via the find fallback, THE HOOK SHALL exit zero silently — identical to the existing Claude behaviour. |

## Unit 9: Session-state transcript fallback in `session_scanner.py`

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | THE SYSTEM SHALL extend the transcript-source list in `apps/cli/lib/session_scanner.py` to include `$COPILOT_HOME/session-state/` (defaulting to `~/.copilot/session-state/`) in addition to `~/.claude/projects/`. |
| R-9.2 | THE SYSTEM SHALL preserve the existing precedence: rows from `<vault>/.squirrel/session-manifest.jsonl` come first, transcript-fallback sources come second. |
| R-9.3 | IF `$COPILOT_HOME/session-state/` does not exist on disk, THE SYSTEM SHALL silently skip it — same behaviour as for a missing `~/.claude/projects/`. |
| R-9.4 | WHEN parsing a Copilot session JSONL row, THE SYSTEM SHALL extract only the two fields needed by `/sq-recover`: last edited file path and project hint (if present). Other fields SHALL be ignored. |
| R-9.5 | IF a Copilot JSONL row has a schema the scanner does not recognize, THE SYSTEM SHALL skip the row and continue with the next, without raising. |

## Unit 10: Documentation parity

| ID    | EARS statement |
|-------|----------------|
| R-10.1 | THE SYSTEM SHALL update `README.md` to list Copilot among the supported agents, at the same level of detail given to Claude/Codex/Cursor. |
| R-10.2 | THE SYSTEM SHALL update `agent-pack/INSTALL.md` to document `./scripts/install-copilot.sh` with its flag surface and the user-level vs. workspace-level distinction. |
| R-10.3 | THE SYSTEM SHALL update the `--agent` argument's help text in `apps/cli/squirrel` to include `copilot`. |
| R-10.4 | THE SYSTEM SHALL NOT modify documentation pages describing the existing Claude/Codex/Cursor flows except to add Copilot to lists where those agents are enumerated. |

## Unit 11: Non-regression invariants for existing agents

| ID    | EARS statement |
|-------|----------------|
| R-11.1 | AFTER running `install-copilot.sh`, THE SYSTEM SHALL leave `~/.claude/plugins/squirrel/` byte-identical to its state before the install (modulo a re-run of `install_canonical()`, which is the documented prerequisite). |
| R-11.2 | AFTER running `install-copilot.sh`, THE SYSTEM SHALL leave `~/.codex/skills/`, `~/.codex/commands/`, and `~/.codex/AGENTS.md` byte-identical to their pre-install state. |
| R-11.3 | AFTER running `install-copilot.sh`, THE SYSTEM SHALL leave `~/.cursor/rules/squirrel/` byte-identical to its pre-install state. |
| R-11.4 | THE SYSTEM SHALL NOT modify `~/.claude/plugins/known_marketplaces.json`, `~/.claude/plugins/installed_plugins.json`, or `~/.claude/settings.json` as part of the Copilot install. Those registries belong to the Claude branch. |
