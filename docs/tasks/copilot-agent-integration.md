# GitHub Copilot Agent Integration — Tasks

Source specs: `docs/hld/copilot-agent-integration.md`, `docs/lld/copilot-agent-integration.md`, `docs/ears/copilot-agent-integration.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Scope: local-files surface only. Copilot Extensions / Skillsets (GitHub App), VS Code chat-participant API, Windsurf, and cross-machine Coding Agent monitoring are out of scope per HLD Non-Goals.

Dependency layers:

```
1.1 (CLI: --agent copilot + --workspace) ──┐
                                            ├─► 3.1 (skill emitter) ──► 3.2 (skill frontmatter)
                                            ├─► 4.1 (prompt emitter) ─► 4.2 (prompt frontmatter)
                                            ├─► 5.1 (copilot-instructions.md patcher)
                                            └─► 7.1 (adapter wrappers) ──► 6.1 (hooks emitter)
                                                                                  │
                                                              2.1 (install-copilot.sh wrapper)
                                                              ↑ orthogonal — needs 1.1 only

8.1 (session_scanner.py fallback) — fully independent

3.1 + 4.1 + 5.1 + 6.1 + 7.1 + 2.1 ─► 9.1 (docs parity)
                                  ─► 10.1 (E2E success-criteria walk)
```

Mutex tags:
- `(mutex: cmd-install)` — 1.1, 3.1, 4.1, 5.1, 6.1 all extend the same `cmd_install` function in `apps/cli/squirrel` around lines 388–451. Sequence them or rebase carefully.
- `(mutex: frontmatter-helper)` — 3.2 and 4.2 both modify the shared frontmatter-injection helper. Sequence them.

## Unit 1: CLI surface — `squirrel install --agent copilot`

- [x] **1.1** Add `copilot` agent branch + `--workspace` flag to `apps/cli/squirrel` (est: ~30m) `(mutex: cmd-install)`
  - acceptance:
    - R-1.1 — `copilot` accepted as `--agent` value, alongside `claude`, `codex`, `cursor`, `standalone`.
    - R-1.2 — `squirrel install --help` lists `copilot` in the `--agent` choices.
    - R-1.3 — Default destination (no `--workspace`) is `$COPILOT_HOME` (fallback `~/.copilot/`).
    - R-1.4 — `--workspace` switches destination to `<repo-root>/.github/`.
    - R-1.5 — `--workspace` + no git repo → `sys.exit(non-zero)` with stderr message naming the missing repo.
    - R-1.6 — Existing branches (`claude`, `codex`, `cursor`, `standalone`) behaviour byte-identical to pre-change.
    - R-1.7 — Auto-detect block (`apps/cli/squirrel:391–399`) extended so `~/.copilot` presence picks `copilot` when `--agent` is omitted (after Claude/Codex/Cursor in priority — the existing order).
  - touchpoints:
    - `apps/cli/squirrel:716–722` — add `"copilot"` to the `--agent` `choices=[...]` and add a new `--workspace` flag (`action="store_true"`).
    - `apps/cli/squirrel:388–451` (`cmd_install` body) — add an `elif agent == "copilot":` branch after the cursor branch. Resolve `dest_root = repo_root/".github"` when `args.workspace`, else `Path(os.environ.get("COPILOT_HOME", "~/.copilot")).expanduser()`. Initial body can be a placeholder that just `mkdir -p`s the four subdirs (`agents/`, `prompts/`, `hooks/`); 3.x–6.x stories fill in the writes.
    - `apps/cli/squirrel:445–449` — extend the `hints` dict with a `"copilot"` entry: `"Restart VS Code / Copilot, then /sq-where-am-i"`.
    - `apps/cli/squirrel:391–399` — extend the auto-detect chain with `elif Path("~/.copilot").expanduser().exists(): agent = "copilot"` (after the cursor branch).
  - verify:
    - `python3 apps/cli/squirrel install --agent copilot --dry-run` exits 0 and prints the dispatch lines.
    - `python3 apps/cli/squirrel install --agent copilot --workspace --dry-run` from a non-git dir exits non-zero with the "not inside a git repository" message.
    - `python3 apps/cli/squirrel install --agent copilot --workspace --dry-run` from a git repo exits 0 and prints `.github/...` destinations.
    - `python3 apps/cli/squirrel install --agent claude --dry-run` output is byte-identical to the pre-change output (capture before, diff after).
  - skip TDD; verify block is the test (scaffolding + arg-parsing).

## Unit 2: Wrapper script `install-copilot.sh`

- [x] **2.1** Write `agent-pack/scripts/install-copilot.sh` (deps: 1.1, est: ~30m)
  - acceptance:
    - R-2.1 — Executable script exists, mirroring `install-codex.sh` shape (sources `_lib.sh`, parses common args, calls `install_canonical` → `install_agent_integration` → `install_post_steps`).
    - R-2.2 — Accepts `--link`, `--dry-run`, `--no-config`, `--no-cli`, `--no-reminders`, `--yes`/`-y`, `--prefix=PATH`, `-h`/`--help`.
    - R-2.3 — Accepts `--workspace` (added to `LEFTOVER_ARGS` parsing then passed through to the Python installer in `EXTRA_ARGS`).
    - R-2.4–R-2.6 — Calls `install_cli_to_path`, `install_config`, `install_macos_daemon` per flag.
    - R-2.7 — `set -euo pipefail` propagates exit codes.
    - R-2.8 — Prints a final summary block ("What was installed: …") naming the four Copilot destinations.
  - touchpoints:
    - New file `agent-pack/scripts/install-copilot.sh` — copy `install-codex.sh` and edit: header comment, agent name in `install_agent_integration` call, final summary block.
    - `agent-pack/scripts/_lib.sh:109–128` (`install_agent_integration`) — extend the `case "$agent"` to include a `copilot)` arm that runs `python3 "$root/squirrel" install --agent copilot "${EXTRA_ARGS[@]}"`.
    - `agent-pack/scripts/_lib.sh` `parse_common_args()` (lines 76–93) — add `--workspace` recognition: `--workspace) EXTRA_ARGS+=(--workspace) ;;`. This makes the flag pass-through clean.
  - verify:
    - `chmod +x agent-pack/scripts/install-copilot.sh && bash agent-pack/scripts/install-copilot.sh --help` prints the help block.
    - `bash agent-pack/scripts/install-copilot.sh --dry-run --yes` exits 0 and prints "would install" lines covering canonical + Copilot integration + post-steps.
    - `bash agent-pack/scripts/install-copilot.sh --workspace --dry-run --yes` inside a git repo prints `.github/` destinations.
  - skip TDD; verify block is the test (shell scaffolding).

## Unit 3: Skill files

- [x] **3.1** Emit per-skill `.agent.md` files (user + workspace destinations) (deps: 1.1, est: ~45m) `(mutex: cmd-install)`
  - acceptance:
    - R-3.1 — User-level: one file per skill at `$COPILOT_HOME/agents/squirrel-<skill>.agent.md` (default `~/.copilot/`).
    - R-3.2 — Workspace-level: one file per skill at `<repo-root>/.github/agents/squirrel-<skill>.agent.md`.
    - R-3.3 — Bodies sourced from `agent-pack/skills/<skill>/SKILL.md` (the in-repo canonical source; the install runs from the repo).
    - R-3.5 — When `--link` is passed, create symlinks via `_copy_or_link(...)` instead of copies. Reuse the helper that already exists in `apps/cli/squirrel` (used by Codex/Cursor branches).
    - R-3.6 — Skip directories whose name starts with `{` (template placeholders), matching `apps/cli/squirrel:412–414`.
    - R-3.7 — Idempotent: re-run overwrites in place; no duplicate files; no orphan removal in this story (orphans tracked in a follow-up if they bite — out of scope for v1).
  - touchpoints:
    - `apps/cli/squirrel` `cmd_install` `copilot` branch — iterate `plugin_root / "skills"` like the codex branch (lines 412–418), but write to `dest_root / "agents"` and rename `<skill>/SKILL.md` → `agents/squirrel-<skill>.agent.md`. Use `_copy_or_link` for file (not directory) copy. Note: SKILL.md is a single file inside each skill dir; the rest of the dir (`resources/`, etc.) is NOT shipped to Copilot because Copilot loaders read only the `.agent.md` file. The canonical install at `~/.claude/plugins/squirrel/skills/<skill>/` still has the full dir for `lib/*.py` discovery.
    - New helper `_copy_skill_for_copilot(src_skill_dir: Path, dst_agents_dir: Path, link: bool, dry: bool) -> None` that handles the rename + frontmatter injection placeholder (3.2 fills that in).
  - verify:
    - `python3 apps/cli/squirrel install --agent copilot --dry-run` lists every skill name with the expected `agents/squirrel-<name>.agent.md` destination.
    - Real run: `ls ~/.copilot/agents/` shows `squirrel-session-start.agent.md` and one entry per `agent-pack/skills/<name>/`.
    - Re-running the install produces no errors and the file count is unchanged.
    - `--workspace` variant inside a git repo writes to `.github/agents/`.
  - skip TDD; verify block is the test (file emission).

- [x] **3.2** Inject Copilot-compatible frontmatter into skill files (deps: 3.1, est: ~30m) `(mutex: frontmatter-helper)`
  - acceptance:
    - R-3.4 — IF the source SKILL.md frontmatter is incompatible with Copilot's `.agent.md` schema (i.e. lacks any of `description`, `name`, `agent`, `model`, `tools`, `argument-hint`), THE SYSTEM SHALL prepend a generated frontmatter block rendered from `agent-pack/companions/copilot/frontmatter-template.yaml`.
    - The original SKILL.md body remains byte-identical except for the prepended header.
    - The canonical install at `~/.claude/plugins/squirrel/skills/<skill>/SKILL.md` is NOT modified (only the Copilot copy gets the header).
  - touchpoints:
    - New file `agent-pack/companions/copilot/frontmatter-template.yaml` — template for the Copilot-shaped header, with placeholders `{{description}}`, `{{name}}` filled from the source's existing YAML frontmatter (parsed with `python3 -c "import yaml; ..."` or a hand-rolled split-on-`---` parser to avoid the new dep).
    - New helper `_inject_copilot_frontmatter(body: str, source_meta: dict) -> str` in `apps/cli/squirrel` (or a small lib module under `apps/cli/lib/`). Returns the source body unchanged if its existing frontmatter already satisfies Copilot.
    - Wire `_copy_skill_for_copilot` from 3.1 to call this helper after reading the source body, before writing the destination.
  - verify:
    - Open `~/.copilot/agents/squirrel-session-start.agent.md` and confirm it starts with a `---` block containing the Copilot fields, followed by the original SKILL.md body.
    - `diff agent-pack/skills/squirrel-session-start/SKILL.md ~/.claude/plugins/squirrel/skills/squirrel-session-start/SKILL.md` → empty (canonical untouched).
    - Manual sanity: open VS Code in the install-copilot-flow workspace, run `@<skill-name>` from Copilot Chat — the agent is recognised (loading error means the schema/frontmatter is off; rewrite template and re-run).
  - skip TDD; verify block is the test (config/template story).

## Unit 4: Slash-command (prompt) files

- [x] **4.1** Emit per-command `.prompt.md` files (user + workspace destinations) (deps: 1.1, est: ~30m) `(mutex: cmd-install)`
  - acceptance:
    - R-4.1 — User-level: one file per command at `$COPILOT_HOME/prompts/sq-<cmd>.prompt.md`.
    - R-4.2 — Workspace-level: one file per command at `<repo-root>/.github/prompts/sq-<cmd>.prompt.md`.
    - R-4.3 — Bodies sourced from `agent-pack/commands/sq-*.md` (matches the existing pattern in `apps/cli/squirrel:415–418`).
    - R-4.5 — `--link` mode creates symlinks instead of copies.
    - R-4.6 — Idempotent across re-runs.
  - touchpoints:
    - `apps/cli/squirrel` `cmd_install` `copilot` branch — extend with a loop over `plugin_root / "commands" / "*.md"`, rename `sq-<cmd>.md` → `sq-<cmd>.prompt.md`, copy/link to `dest_root / "prompts"`.
  - verify:
    - `ls ~/.copilot/prompts/` after install shows one `sq-*.prompt.md` per file in `agent-pack/commands/`.
    - `--workspace` variant writes under `.github/prompts/`.
    - `--link` mode: `readlink ~/.copilot/prompts/sq-start.prompt.md` returns the canonical source path; editing the canonical source is reflected immediately.

- [x] **4.2** Inject Copilot-compatible frontmatter into prompt files (deps: 4.1, 3.2, est: ~20m) `(mutex: frontmatter-helper)`
  - acceptance:
    - R-4.4 — Generated frontmatter block prepended IF the source command lacks the Copilot-required fields (`description`, `name`, `agent`, `model`, `tools`, `argument-hint`). Source command body otherwise unchanged.
    - Helper from 3.2 is reused (one injector serves both skill files and prompt files; field defaults differ — controlled by a `kind={"skill","prompt"}` argument).
  - touchpoints:
    - `agent-pack/companions/copilot/frontmatter-template.yaml` — add a `prompt:` section alongside the `skill:` section, with per-kind defaults.
    - `_inject_copilot_frontmatter` (added in 3.2) — extend to accept `kind` and pick the right template section.
    - The `cmd_install` `copilot` branch — pass `kind="prompt"` when emitting prompt files.
  - verify:
    - `~/.copilot/prompts/sq-start.prompt.md` begins with the Copilot frontmatter (with `name: sq-start`, etc.), followed by the source body.
    - Re-running install does not duplicate the header.

## Unit 5: Copilot manifest (`copilot-instructions.md`)

- [x] **5.1** Generate and patch `copilot-instructions.md` with the Squirrel manifest block (deps: 1.1, est: ~30m) `(mutex: cmd-install)`
  - acceptance:
    - R-5.1 — User-level: `~/.copilot/copilot-instructions.md` contains a block starting with `# Squirrel — Copilot Agent Manifest`.
    - R-5.2 — If the marker is already present, skip patching (no rewrite, no duplicate).
    - R-5.3 — If the file exists but the marker is absent, append the block after a single blank line. Preserve all prior content.
    - R-5.4 — If the file does not exist, create it containing only the manifest block.
    - R-5.5 — Workspace-level applies the same R-5.1–R-5.4 against `<repo-root>/.github/copilot-instructions.md`.
    - R-5.6 — Manifest text rendered from a single template (mirrors `_CODEX_AGENTS_BLOCK` near `apps/cli/squirrel:364–382`).
    - R-5.7 — Prints `created` | `patched` | `skipped (already present)` to stdout for observability.
  - touchpoints:
    - New module-level constant `_COPILOT_INSTRUCTIONS_BLOCK` in `apps/cli/squirrel` (or co-located in `agent-pack/companions/copilot/instructions.md`). Content: skill index + slash-command list + config pointer, mirroring `agent-pack/companions/codex/AGENTS.md` lines 1–40.
    - New helper `_patch_copilot_instructions_md(dest: Path, dry: bool) -> None` modelled on `_patch_codex_agents_md` (`apps/cli/squirrel:364–382`). The dest path comes from the `cmd_install` `copilot` branch (`dest_root / "copilot-instructions.md"`).
    - `cmd_install` `copilot` branch — call the patcher after skill/prompt files are written.
  - verify:
    - First install: `cat ~/.copilot/copilot-instructions.md | grep -c "# Squirrel — Copilot Agent Manifest"` returns `1`.
    - Second install: same `grep -c` still returns `1`; install stdout shows `skipped (already present)`.
    - Append case: `echo "existing content" > ~/.copilot/copilot-instructions.md && install...` → file ends with `existing content\n\n# Squirrel — Copilot Agent Manifest\n...`.
    - Workspace case: same checks against `.github/copilot-instructions.md`.

## Unit 6: Hooks registration

- [x] **6.1** Emit `squirrel.json` hook-registration file with INT-007 event mapping (deps: 1.1, 7.1, est: ~45m) `(mutex: cmd-install)`
  - acceptance:
    - R-6.1 — User-level: write `$COPILOT_HOME/hooks/squirrel.json` (default `~/.copilot/hooks/`).
    - R-6.2 — Workspace-level: write `<repo-root>/.github/hooks/squirrel.json`.
    - R-6.3 — Register four hooks mapping Copilot events ↔ Squirrel events: `sessionStart` ↔ SessionStart, `userPromptSubmitted` ↔ UserPromptSubmit, `sessionEnd` (with `agentStop` fallback) ↔ Stop, `postToolUse` ↔ PostToolUse:Edit. Each entry's `command` invokes the appropriate adapter wrapper from 7.1 with the Squirrel event name as the first argument.
    - R-6.4 — Do NOT register Copilot-only events (`subagentStart`, `subagentStop`, `errorOccurred`, `permissionRequest`, `notification`, `preCompact`, `postToolUseFailure`) in this change.
    - R-6.5 — Overwrite the entire file each install (generated content).
    - R-6.6 — If the file already exists AND contains entries not owned by Squirrel (detection: any top-level key/array element whose `command` does not reference Squirrel's adapter path), print a warning and skip writing. The user resolves manually.
    - R-8.1 — The `postToolUse` hook's command invokes `manifest_writer.py` via the same `find` lookup the Claude hook uses (`agent-pack/hooks/hooks.json:49`), routed through the adapter wrapper.
    - R-8.3 — The hook command exits zero silently if `manifest_writer.py` cannot be located (matches existing Claude behaviour).
  - touchpoints:
    - New module-level constant `_COPILOT_HOOKS_TEMPLATE` in `apps/cli/squirrel` (or `agent-pack/companions/copilot/hooks.json.template`). Reflects the four-entry mapping with absolute paths to the adapter scripts resolved at install time.
    - New helper `_emit_copilot_hooks_json(dest: Path, adapter_dir: Path, dry: bool) -> None` that renders the template substituting `__ADAPTER_DIR__` with the absolute path to the canonical adapter scripts (under `~/.claude/plugins/squirrel/companions/copilot/`).
    - `cmd_install` `copilot` branch — call the emitter after skill/prompt files and the manifest patcher.
    - Note: the `command` for each Copilot hook entry calls `bash <adapter_dir>/hook-adapter.sh <SquirrelEventName> <inline-bash-body>`. The inline bash bodies are pulled verbatim from `agent-pack/hooks/hooks.json` so a future edit to `hooks.json` is the single change needed.
  - verify:
    - First install: `~/.copilot/hooks/squirrel.json` exists with four entries; `jq '. | length' ~/.copilot/hooks/squirrel.json` (or the equivalent for whatever the documented schema is) confirms the count.
    - Re-install: file is overwritten; mtime updates; entry count unchanged.
    - Pre-populate `~/.copilot/hooks/squirrel.json` with a non-Squirrel entry; re-install → warning printed, file unchanged.
    - Workspace variant: `.github/hooks/squirrel.json` exists after a `--workspace` install.

## Unit 7: Hook adapter (INT-007 preservation)

- [x] **7.1** Ship `hook-adapter.sh` and `hook-adapter-stdin.sh` (deps: none, can land first; needed by 6.1, est: ~60m)
  - acceptance:
    - R-7.1 — Two scripts exist at `agent-pack/companions/copilot/hook-adapter.sh` and `agent-pack/companions/copilot/hook-adapter-stdin.sh`. Both are `chmod +x`. Canonical install at `~/.claude/plugins/squirrel/companions/copilot/` carries them too (because `install_canonical()` copies the whole agent-pack/companions/ tree).
    - R-7.2 — On invocation, the adapter exports `EVENT`, `PROJECT`, `TIMESTAMP`, and `USER_PROMPT` (the last only for `UserPromptSubmit`) into the environment, then exec's the inline bash body that was passed as `$2..$N`.
    - R-7.3 — `PROJECT` resolution: read `last_active_project` from `~/.squirrel/state.json` (or legacy `~/.squirrel/state/<vault>.json`) via `python3 -c "import json; …"`. Default empty string if unresolvable.
    - R-7.4 — `TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)`.
    - R-7.5 — `EVENT` is the Squirrel-side name (`SessionStart`, `UserPromptSubmit`, `Stop`, `PostToolUse`), taken from `$1` — the hooks.json template in 6.1 always passes the Squirrel name explicitly.
    - R-7.6 — `hook-adapter-stdin.sh`: if `stdin` is not a TTY, `read -t 1` the JSON payload, parse it (`python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('user_prompt',''))"` etc.), populate the four contract vars from the payload BEFORE exec'ing the body.
    - R-7.7 — Inline bash bodies (copied from `agent-pack/hooks/hooks.json`) are run unchanged via `bash -c "$BODY"`. Adapter MUST NOT pattern-match, rewrite, or escape them.
    - R-7.8 — On any failure to derive `EVENT`, exit `0` (silent), emit one stderr line naming the missing field. Never error out — hooks must never break Copilot sessions.
  - touchpoints:
    - New files (both with `#!/usr/bin/env bash` and `set -uo pipefail`):
      - `agent-pack/companions/copilot/hook-adapter.sh`
      - `agent-pack/companions/copilot/hook-adapter-stdin.sh`
    - Both share a small helper sourced from `agent-pack/companions/copilot/_adapter-common.sh` (`resolve_project()`, `iso_timestamp()`) to keep duplication zero.
  - verify:
    - `bash agent-pack/companions/copilot/hook-adapter.sh SessionStart 'echo "EVENT=$EVENT PROJECT=$PROJECT TS=$TIMESTAMP"'` → prints all three with non-empty values (assuming `state.json` exists).
    - Same with `''` body → no output (empty body is permitted).
    - `echo '{"user_prompt":"decidí usar X"}' | bash agent-pack/companions/copilot/hook-adapter-stdin.sh UserPromptSubmit 'echo "$USER_PROMPT"'` → prints `decidí usar X`.
    - Force failure: rename `~/.squirrel/state.json` away; adapter still exits 0; stderr has a one-line note about `state.json` not found.
    - `shellcheck agent-pack/companions/copilot/*.sh` → no errors.
  - skip TDD; verify block is the test (shell scaffolding).

## Unit 8: Session-state transcript fallback in `session_scanner.py`

- [x] **8.1** Add `~/.copilot/session-state/` as a third transcript-fallback source (deps: none, est: ~30m)
  - acceptance:
    - R-9.1 — `session_scanner.py`'s transcript-source list includes `Path(os.environ.get("COPILOT_HOME", "~/.copilot")).expanduser() / "session-state"` after `~/.claude/projects/`.
    - R-9.2 — Precedence preserved: manifest rows from `<vault>/.squirrel/session-manifest.jsonl` come first; transcript fallbacks come second.
    - R-9.3 — Missing directory is silently skipped (matches existing behaviour for `~/.claude/projects/`).
    - R-9.4 — Parser extracts only last edited file path and project hint (the two fields `/sq-recover` uses); other fields ignored.
    - R-9.5 — Unrecognised row schema → skip the row, no raise.
  - touchpoints:
    - `apps/cli/lib/session_scanner.py` — locate the existing transcript-source constant (likely a list or tuple near the top of the module). Append the Copilot path.
    - New helper `_parse_copilot_jsonl_row(line: str) -> Optional[ScannedRow]` that handles the two-field extraction with a try/except wrapper. The exact field names depend on what `~/.copilot/session-state/*.jsonl` actually carries — confirm via `ls ~/.copilot/session-state/ && head -1 ~/.copilot/session-state/<file>.jsonl` on the dev machine before implementing.
    - If the dev machine has no Copilot session-state files yet, the parser writes the `try/except` defensively with the field names from the GitHub docs and gets validated via the E2E story (10.1).
  - verify:
    - Unit test in `apps/cli/tests/test_session_scanner.py` (create if missing): construct a fake `~/.copilot/session-state/<id>.jsonl` with one valid row + one malformed row + one row with unknown schema. Run the scanner. Assert the valid row contributes a file path; the malformed row is skipped; no exception is raised.
    - Manual: with a real Copilot session, `python3 -c "from apps.cli.lib.session_scanner import scan; print(scan(vault_path, since=...))"` returns rows that include at least one Copilot-edited file.

## Unit 9: Documentation parity

- [x] **9.1** Update README, INSTALL.md, and `--help` text (deps: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, est: ~30m)
  - acceptance:
    - R-10.1 — `README.md` lists Copilot alongside Claude/Codex/Cursor at the same level of detail (one paragraph naming locations + install command).
    - R-10.2 — `agent-pack/INSTALL.md` documents `./scripts/install-copilot.sh` with flag surface and user-level vs workspace distinction.
    - R-10.3 — `python3 apps/cli/squirrel install --help` shows `copilot` in `--agent` choices (this is automatic once 1.1 lands).
    - R-10.4 — No edits to documentation describing the existing Claude/Codex/Cursor flows except to add `copilot` to enumerations.
  - touchpoints:
    - `README.md` — search for "Codex" or "Cursor" sections; mirror them with a Copilot section. Add the install command, the destination paths (both user-level and workspace), and the prerequisites (VS Code with Copilot Chat, or Copilot CLI).
    - `agent-pack/INSTALL.md` — same pattern.
    - `agent-pack/INSTALL-README.md` — extend the "Which install script do I run?" table if present.
  - verify:
    - `grep -c "copilot" README.md` ≥ 5 (rough sanity).
    - `grep -A 5 "Copilot" agent-pack/INSTALL.md` shows the install command + flag explanation.
    - Have a fresh reader (Codex agent / second pair of eyes) read the docs and confirm the Copilot flow is discoverable without reading the EARS.

## Unit 10: End-to-end verification

- [x] **10.1** Walk the nine Success Criteria from `docs/hld/copilot-agent-integration.md` (deps: 2.1, 3.2, 4.2, 5.1, 6.1, 7.1, 8.1, 9.1, est: ~45m)
  - acceptance: each of the 9 Success Criteria bullets in the HLD reproduces as written. Also R-11.1–R-11.4 (non-regression on Claude/Codex/Cursor installs).
  - verify (the checks themselves):
    1. **CLI fourth-branch test.** `python3 apps/cli/squirrel install --agent copilot --dry-run` exits 0. `python3 apps/cli/squirrel install --help` lists `copilot`.
    2. **User-level install test.** Snapshot the file trees `~/.claude/plugins/squirrel/`, `~/.codex/`, `~/.cursor/rules/squirrel/` with `find ... | xargs sha256sum > /tmp/before.txt` BEFORE the install. Run `./agent-pack/scripts/install-copilot.sh --yes`. Verify `~/.copilot/agents/squirrel-*.agent.md`, `~/.copilot/prompts/sq-*.prompt.md`, `~/.copilot/copilot-instructions.md`, `~/.copilot/hooks/squirrel.json` all exist. Re-snapshot the three other agent dirs into `/tmp/after.txt`; `diff /tmp/before.txt /tmp/after.txt` → empty (R-11.1, R-11.2, R-11.3).
    3. **Workspace-level install test.** From a fresh git clone, run `python3 apps/cli/squirrel install --agent copilot --workspace`. Verify `.github/agents/`, `.github/prompts/`, `.github/copilot-instructions.md`, `.github/hooks/squirrel.json` populated. Re-run; `git status` shows no new diffs (idempotent).
    4. **Manifest write through Copilot test.** Configure a vault in `~/.squirrel/config.toml`, open VS Code in that vault, ask Copilot Chat to edit `apps/cli/lib/session_scanner.py`. Tail `<vault>/.squirrel/session-manifest.jsonl`: a new row with `file` matching the edited path appears.
    5. **Recovery test.** Truncate the manifest. Confirm `~/.copilot/session-state/<id>.jsonl` has rows from the Copilot session. Run `/sq-recover`: at least the project tag and last-edited file are reconstructed.
    6. **User-prompt pattern detection.** In Copilot Chat, send "decidimos usar postgres en lugar de mongo". The session log (or Copilot's notification surface) shows the "Detecté lenguaje decisional. Considerá /sq-decision" hint.
    7. **Idempotency test.** Run the installer twice. `diff <(grep -c "# Squirrel — Copilot Agent Manifest" ~/.copilot/copilot-instructions.md) <(echo 1)` → empty. `~/.copilot/hooks/squirrel.json` entry count unchanged.
    8. **Existing agents untouched.** Covered by snapshot diff in step 2.
    9. **Docs parity test.** `grep -c "Copilot" README.md` reports ≥ 5 and a paragraph specifically about install paths is present.
  - On all-pass: append a one-line dated note in `.uncle-dev/learns/copilot-agent-integration.md` documenting what was verified, on what macOS version, with what Copilot CLI version, and confirm whether the Copilot hook loader supplied env vars verbatim (env adapter sufficient) or required the stdin-JSON adapter — this resolves the open uncertainty from the research doc.

## Cross-cutting notes

- **No new external deps.** Pure stdlib Python (`json`, `pathlib`, `os`, `subprocess`) and bash. `python3 -c "import yaml"` is the only "iffy" dep used (for parsing existing SKILL.md frontmatter); fall back to a hand-rolled split-on-`---` parser if PyYAML isn't available on the user's interpreter. Codex/Cursor branches don't use PyYAML today; do the same here.
- **Open uncertainty from research §"Open uncertainties".** The exact Copilot hook delivery shape (env vars vs stdin JSON) is unconfirmed at spec time. Story 7.1 ships both adapters, story 6.1 wires the env-vars one by default, and story 10.1 resolves the question empirically — switching the hooks.json to the stdin variant if the env-vars adapter sees empty `$EVENT`/`$USER_PROMPT` in a live run.
- **Effort total:** ~6.5–7 hours of focused work, comparable to runtime-trust-handshake's estimate.
- **Skill-body source-of-truth.** Bodies live in `agent-pack/skills/<name>/SKILL.md` and ship to every agent unchanged. Frontmatter injection is the only Copilot-specific transformation; it happens at install time on the destination copy, never on the canonical source. If a skill body gains a feature, no Copilot-specific edit is required.
- **Workspace-level install caveat.** When `--workspace` writes to `.github/`, the user is responsible for committing the generated files. The installer prints a one-line reminder; it does NOT run `git add`.
