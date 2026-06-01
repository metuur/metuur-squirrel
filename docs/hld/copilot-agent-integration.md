# GitHub Copilot Agent Integration — High-Level Design

## Overview

Squirrel today installs its skills, slash commands, manifest text, and monitoring hooks into three agents — Claude Code, OpenAI Codex CLI, and Cursor — via `apps/cli/squirrel install --agent {claude|codex|cursor}` orchestrated from `agent-pack/install.sh` + `agent-pack/scripts/install-{agent}.sh`. Users who code through GitHub Copilot (VS Code Chat, JetBrains Copilot, Copilot CLI, JetBrains/Xcode) are excluded: they get no `/sq-*` commands, no skill bodies, no shutdown reminders, and their sessions never appear in `<vault>/.squirrel/session-manifest.jsonl`. Recovery via `/sq-recover` is silent on the Copilot side because `session_scanner.py` only reads Claude's transcripts as a fallback.

This change adds Copilot as a fourth install target. Skills land in `.github/agents/` (workspace) or `~/.copilot/agents/` (user), slash commands in `.github/prompts/` or `~/.copilot/prompts/`, the manifest as `.github/copilot-instructions.md` (workspace) or appended to `~/.copilot/copilot-instructions.md` (user). Squirrel's INT-007 hook contract gets ported to Copilot's hook system — `sessionStart`, `sessionEnd`, `userPromptSubmitted`, `postToolUse` — installed at `~/.copilot/hooks/` so a user-level install reaches every workspace. `session_scanner.py` gains `~/.copilot/session-state/*.jsonl` as a third transcript source alongside the existing Claude JSONL fallback.

The integration uses **only the local-files surface**. The Copilot Extensions / Skillsets path (GitHub App with public HTTPS endpoints) is explicitly out of scope: it requires Squirrel to operate a hosted service, which conflicts with the local-first model the rest of the product is built on.

## Stakeholders & Impact

| Stakeholder | Today's pain | After this ships |
|---|---|---|
| Primary user (Javier) when working in VS Code Copilot Chat or Copilot CLI | No `/sq-*` commands; no manifest visibility on what Copilot edited; `/sq-recover` cannot reconstruct a forgotten session because there are no manifest rows from Copilot. Manual context port-over between agents. | `squirrel install --agent copilot` lays the same skills + commands the other agents have; Copilot's session writes to `session-manifest.jsonl` via a `postToolUse` hook; `/sq-recover` finds those rows; user-prompt pattern suggestions fire in Copilot Chat the same way they fire in Claude Code. |
| `/sq-recover` (skill consumer of `session_scanner.py`) | Only two transcript fallbacks: the manifest itself, and `~/.claude/projects/*/*.jsonl`. Sessions that ran exclusively in Copilot are invisible. | A third fallback source — `~/.copilot/session-state/*.jsonl` — feeds the same scanner. Recovery from Copilot-only sessions becomes possible even when the user forgot to run `/sq-end`. |
| Install pipeline (`agent-pack/install.sh`, `apps/cli/squirrel install`) | Three agent branches (`claude`, `codex`, `cursor`) plus `standalone`. Extending requires adding one branch in the Python CLI, one shell wrapper, optionally one companions/ folder, and listing the agent in `--agent` choices. | A fourth `copilot` branch in `apps/cli/squirrel` and an `install-copilot.sh` wrapper, both following the `install_canonical()` + `install_agent_integration()` pattern from `agent-pack/scripts/_lib.sh:99–128`. No restructuring of the existing branches. |
| Copilot Coding Agent (cloud) user (out-of-scope consumer) | N/A | Still out of scope. The cloud agent's hook loader reads only `.github/hooks/*.json` from the cloned repo, so a workspace-level install would reach it; but cross-machine monitoring of cloud runs is not addressed in this change. Mentioned only to confirm it is not addressed here. |

## Goals

When this ships, the following are observable and true:

1. **`squirrel install --agent copilot` exists** as a fourth choice in the CLI's `--agent` argument, accepted alongside `claude`, `codex`, `cursor`, `standalone`.
2. **`agent-pack/scripts/install-copilot.sh` exists** and follows the same shape as `install-codex.sh`: `install_canonical()` → `install_agent_integration("copilot")` → `install_post_steps()`, with the same flag surface (`--link`, `--dry-run`, `--no-config`, `--no-cli`, `--no-reminders`, `--yes`, `--prefix=PATH`).
3. **A user-level install lays down two locations**: skills under `~/.copilot/agents/squirrel-<skill>.agent.md` and slash commands under `~/.copilot/prompts/sq-<cmd>.prompt.md`. Markdown bodies are reused unchanged from the canonical install at `~/.claude/plugins/squirrel/{skills,commands}` — no per-agent rewrites.
4. **A workspace-level install option exists** via a documented `squirrel install --agent copilot --workspace` flag that targets the current git repo's `.github/agents/`, `.github/prompts/`, and `.github/copilot-instructions.md` instead of `~/.copilot/`. User-level is the default; workspace-level is opt-in.
5. **Squirrel's manifest text is published** as `~/.copilot/copilot-instructions.md` (user-level) by appending a `# Squirrel — Copilot Agent Manifest` block, mirroring how `_patch_codex_agents_md()` patches `~/.codex/AGENTS.md`. Idempotent (skip if the marker is already present).
6. **Squirrel's INT-007 hook contract reaches Copilot.** `~/.copilot/hooks/squirrel.json` (or equivalent, depending on the Copilot loader's documented schema) registers the same four event handlers Squirrel wires for Claude Code — mapped to Copilot's event names (`sessionStart`, `userPromptSubmitted`, `sessionEnd`/`agentStop`, `postToolUse`). Each handler invokes a shell command that exports `EVENT`, `PROJECT`, `TIMESTAMP`, and (for the prompt event) `USER_PROMPT` before delegating to the same inline bash bodies or `manifest_writer.py` invocation that the Claude hooks use today.
7. **`session_scanner.py` gains `~/.copilot/session-state/*.jsonl` as a third fallback source**, behind the manifest and behind `~/.claude/projects/*/*.jsonl`. Existing precedence (manifest first, then transcript fallbacks) is preserved.
8. **The README and `INSTALL.md` document the Copilot path** at parity with the existing Claude/Codex/Cursor documentation.

## Non-Goals

- **No Copilot Extensions / Skillsets surface.** That requires running a public HTTPS service backed by a GitHub App; it is a different operational model and is explicitly deferred.
- **No VS Code extension.** Squirrel will not ship a `vscode.chat.createChatParticipant` participant; integration is purely file-on-disk + hooks.
- **No cross-machine cloud monitoring** of Copilot Coding Agent runs. A workspace install will reach the cloud agent's repo-level hook loader, but Squirrel will not consume the runs' output via webhooks or `repository_dispatch` in this change.
- **No Windsurf branch.** Windsurf is mentioned in the README but has no install script today; this change does not add one. Windsurf users can continue using the Cursor rule by symlink.
- **No new skill bodies.** Skills are copied as-is from the canonical install. No Copilot-specific Markdown forks.
- **No change to the existing Claude/Codex/Cursor install paths.** Their branches in `apps/cli/squirrel` and their wrapper scripts are unchanged.
- **No change to the canonical install location.** `~/.claude/plugins/squirrel/` remains the single source of truth that skill bodies read `lib/*.py` from. Copilot install only adds pointers/copies into Copilot's locations.
- **No telemetry beyond what hooks already produce.** The `session-manifest.jsonl` schema (`timestamp, cwd, file, event, session`) is not extended for Copilot; the same row shape is used.
- **No tray icon or banner UI changes** in the Tauri desktop shell. Copilot integration is CLI/installer-only.

## Success Criteria

Done when the following are observable on a fresh macOS install with VS Code + Copilot Chat already configured:

1. **CLI fourth-branch test.** `squirrel install --agent copilot` runs to completion without error. `squirrel install --help` lists `copilot` among the `--agent` choices.
2. **User-level install test.** After `./agent-pack/scripts/install-copilot.sh --yes`, the following exist:
   - `~/.copilot/agents/squirrel-session-start.agent.md` and one `.agent.md` per skill that lives in `agent-pack/skills/`.
   - `~/.copilot/prompts/sq-start.prompt.md` and one `.prompt.md` per command in `agent-pack/commands/`.
   - `~/.copilot/copilot-instructions.md` contains `# Squirrel — Copilot Agent Manifest`.
   - `~/.copilot/hooks/squirrel.json` (or whatever name matches the Copilot loader's schema) contains four hook entries.
   - `~/.claude/plugins/squirrel/` is unchanged (canonical install untouched).
3. **Workspace-level install test.** `squirrel install --agent copilot --workspace` inside a git repo creates `.github/agents/squirrel-*.agent.md`, `.github/prompts/sq-*.prompt.md`, `.github/copilot-instructions.md`, and `.github/hooks/squirrel.json`. Idempotent on re-run (no duplicate blocks, no errors).
4. **Manifest write through Copilot test.** Open VS Code in a repo registered as a Squirrel vault project, edit a file via Copilot Chat ("update foo.py to add X"). After the edit, `<vault>/.squirrel/session-manifest.jsonl` has a new line with `file` matching the edited path and `event` matching the Copilot `postToolUse` event mapped through the INT-007 adapter.
5. **Recovery from Copilot-only session test.** With no entries in `session-manifest.jsonl` for the test session, but with `~/.copilot/session-state/<session-id>.jsonl` present, `/sq-recover` reconstructs at least the project tag and the last-edited file from the Copilot transcript.
6. **User-prompt pattern detection test.** In a Copilot Chat session, typing a message containing `decidimos usar X` triggers the same "Detecté lenguaje decisional. Considerá /sq-decision" suggestion the Claude hook already produces. Mechanism: `userPromptSubmitted` hook → INT-007 env adapter → same inline bash matcher.
7. **Idempotency test.** Running `install-copilot.sh` twice produces no duplicated entries in `~/.copilot/copilot-instructions.md` and no duplicated hook entries in `~/.copilot/hooks/squirrel.json`.
8. **Existing agents untouched test.** After `install-copilot.sh`, `diff` of `~/.claude/plugins/squirrel/`, `~/.codex/skills/`, `~/.codex/AGENTS.md`, and `~/.cursor/rules/squirrel/` against their pre-install state shows zero changes.
9. **Documentation parity test.** `README.md` and `agent-pack/INSTALL.md` reference the Copilot path with the same level of detail as the Codex and Cursor paths (one paragraph each, install command shown, locations listed).
