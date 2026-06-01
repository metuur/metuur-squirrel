# GitHub Copilot Agent Integration — Low-Level Design

## Architecture

Five components participate, all of which already exist for the other agents — this change wires Copilot into the same pipeline rather than building a parallel one.

1. **CLI install router** (`apps/cli/squirrel`, `cmd_install` around lines 388–451) — adds a `copilot` branch to the agent dispatch.
2. **Wrapper script** (`agent-pack/scripts/install-copilot.sh`) — new file; mirrors `install-codex.sh`.
3. **Manifest patcher** (extends the pattern in `_patch_codex_agents_md()` in `apps/cli/squirrel`) — new function `_patch_copilot_instructions_md()` for the user-level case, and a workspace-level variant that writes `.github/copilot-instructions.md`.
4. **Hooks file emitter** — new helper that renders `~/.copilot/hooks/squirrel.json` (or `.github/hooks/squirrel.json` for the workspace case) from a single source-of-truth mapping defined alongside `agent-pack/hooks/hooks.json`.
5. **Transcript-source adapter** (`apps/cli/lib/session_scanner.py`) — extends the existing JSONL-fallback list to include `~/.copilot/session-state/*.jsonl` (or `$COPILOT_HOME/session-state/*.jsonl` if the env var is set).

```
              User runs install-copilot.sh
                          │
                          ▼
              install_canonical()  ──► ~/.claude/plugins/squirrel/   (unchanged path; single source of truth for skill bodies)
                          │
                          ▼
        install_agent_integration("copilot")
                          │
                          ▼
        python3 squirrel install --agent copilot [--workspace]
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
       user-level path         workspace-level path
       (--workspace absent)    (--workspace present)
              │                       │
              ▼                       ▼
   ~/.copilot/agents/           .github/agents/
   ~/.copilot/prompts/          .github/prompts/
   ~/.copilot/copilot-          .github/copilot-instructions.md
       instructions.md          .github/hooks/squirrel.json
   ~/.copilot/hooks/
       squirrel.json
              │                       │
              └───────────┬───────────┘
                          ▼
        install_post_steps() ── CLI symlink, config seed, macOS daemon
```

Skill discovery at runtime continues to use the same `find` fallback every slash command already does today (locate `lib/*.py` under `~/.claude/plugins/squirrel/`), so no new path probe is needed inside Copilot itself.

### File-name mapping

| Source (canonical) | Destination (Copilot, user-level) | Destination (Copilot, workspace) |
|---|---|---|
| `agent-pack/skills/<name>/SKILL.md` | `~/.copilot/agents/squirrel-<name>.agent.md` | `.github/agents/squirrel-<name>.agent.md` |
| `agent-pack/commands/sq-*.md` | `~/.copilot/prompts/sq-*.prompt.md` | `.github/prompts/sq-*.prompt.md` |
| (synthesized from skill index template) | `~/.copilot/copilot-instructions.md` (appended block) | `.github/copilot-instructions.md` (overwrite-or-create with `# Squirrel — Copilot Agent Manifest` marker) |
| (synthesized from `agent-pack/hooks/hooks.json` mapping) | `~/.copilot/hooks/squirrel.json` | `.github/hooks/squirrel.json` |

Source file *bodies* are reused unchanged. Renaming is purely the file-name suffix (`.md` → `.agent.md` / `.prompt.md`) the Copilot loader requires. No frontmatter is added to skill files in this change unless the Copilot loader rejects them — see "Constraints → Frontmatter compatibility" below.

### Hook adapter flow

Squirrel's existing hooks (`agent-pack/hooks/hooks.json`) are Claude-Code-shaped: each hook command runs in a shell with `EVENT`, `PROJECT`, `TIMESTAMP`, `USER_PROMPT` exported by Claude (the INT-007 contract documented in `hooks.json` line 3). Copilot's hook loader documents a different invocation shape (see "Open uncertainties" in the research). The adapter resolves this without forking the inline bash bodies:

```
~/.copilot/hooks/squirrel.json
   │
   ▼ (Copilot invokes)
adapter wrapper script  (one of: env-passthrough, or stdin-JSON-parser)
   │
   ▼ (sets EVENT/PROJECT/TIMESTAMP/USER_PROMPT in env)
inline bash matcher (verbatim copy of the body from hooks.json)
   │
   ▼ (on Edit-type events)
python3 manifest_writer.py
   │
   ▼ (appends to <vault>/.squirrel/session-manifest.jsonl)
```

The wrapper script is the only Copilot-specific shim. Two implementations are required because the Copilot docs describe two delivery shapes (env vars + arguments via the local CLI, and JSON-on-stdin via the Coding Agent / VS Code surfaces). The installer ships both as `agent-pack/companions/copilot/hook-adapter.sh` (the env case) and `agent-pack/companions/copilot/hook-adapter-stdin.sh` (the JSON case). The `squirrel.json` entry references the right one per event based on the documented delivery shape for that event.

If at install time the exact schema cannot be confirmed (because the Copilot loader version on the user's machine differs from the docs at time of writing), the installer falls back to the stdin-JSON adapter — it is a strict superset (it parses what's on stdin if present, otherwise reads env). One adapter, two code paths inside.

### Session-state transcript adapter

`apps/cli/lib/session_scanner.py` currently merges the manifest with `~/.claude/projects/*/*.jsonl`. The change extends `_TRANSCRIPT_SOURCES` (or equivalent constant) to include:

```python
TRANSCRIPT_SOURCES = [
    Path("~/.claude/projects").expanduser(),
    Path(os.environ.get("COPILOT_HOME", "~/.copilot")).expanduser() / "session-state",
]
```

Reading is best-effort: a missing directory is silently skipped (matches the current behaviour for the Claude path). The Copilot JSONL row schema is parsed only for the two fields `/sq-recover` actually needs — last edited file path and project hint — so a schema drift in Copilot does not break Squirrel.

## Constraints

### File-name + frontmatter compatibility

- Skill body files MUST be named `squirrel-<skill-name>.agent.md` (user) or under `.github/agents/` (workspace). Copilot's loader keys off the `.agent.md` suffix.
- Prompt files MUST be named `sq-<command-name>.prompt.md`. Copilot's loader keys off the `.prompt.md` suffix.
- IF the existing `SKILL.md` frontmatter (Claude-style YAML with `name`/`description`/`triggers`) is rejected by Copilot's loader, the install MUST inject a Copilot-compatible frontmatter header (`description`, `name`, `agent`, `model`, `tools`, `argument-hint`) above the existing content, leaving the rest of the body unchanged. The original frontmatter remains in the canonical install — only the Copilot copy is patched.
- The injection is deterministic: a header template lives at `agent-pack/companions/copilot/frontmatter-template.yaml` and the installer renders it with values pulled from the source SKILL.md's existing frontmatter.

### Hook contract preservation (INT-007)

- Every hook command Squirrel registers in Copilot MUST receive `EVENT`, `PROJECT`, `TIMESTAMP` env vars before the inline bash body runs. For `userPromptSubmitted`, also `USER_PROMPT`.
- The adapter wrapper is responsible for this contract; the inline bash bodies copied from `agent-pack/hooks/hooks.json` MUST NOT be edited.
- If the Copilot loader supplies a JSON payload on stdin instead of env vars, the wrapper MUST parse the payload and export the four variables itself before exec'ing the body.
- `PROJECT` resolution: the wrapper reads `~/.squirrel/state.json` (or the legacy `~/.squirrel/state/<vault>.json`) the same way the Claude install does — no Copilot-specific project lookup.

### Path resolution

- The wrapper script MUST honor `COPILOT_HOME` if set, falling back to `~/.copilot/`. (Source: docs.github.com — Copilot CLI.)
- `manifest_writer.py` lookup MUST use the existing find logic from `agent-pack/hooks/hooks.json` line 49 (`find "${HOME}/.claude" "${HOME}/others" -name manifest_writer.py -path "*/squirrel/*"`). No new search path is added — the canonical install lives at `~/.claude/plugins/squirrel/` regardless of which agent the user runs.

### Idempotency

- Re-running `install-copilot.sh` MUST be safe. Skill / prompt files use overwrite-or-skip semantics based on the `--link` flag (same as Codex/Cursor today).
- Manifest patcher MUST check for a marker (`# Squirrel — Copilot Agent Manifest`) and skip if present, identical to `_patch_codex_agents_md()` in `apps/cli/squirrel:367–376`.
- Hooks file emitter MUST overwrite the `squirrel.json` file as a whole — it is generated content, not user-edited. (Different from `copilot-instructions.md`, which the user may edit by hand and which we append to.)

### Workspace-level safety

- The `--workspace` flag MUST refuse to run if the cwd is not inside a git repo (cheap check: `git rev-parse --show-toplevel`). The wrapper script enforces this before calling the Python installer.
- `.github/` files are tracked in version control; the installer MUST print a one-line reminder that the user should commit and review the generated files. No automatic `git add`.

### Compatibility with the existing canonical install

- `install_canonical()` MUST be called before `install_agent_integration("copilot")`, identical to the Codex/Cursor flow. The canonical install is the source-of-truth for skill bodies and for `lib/*.py`.
- Symlink mode (`--link`) MUST symlink Copilot's per-skill `.agent.md` file at `~/.copilot/agents/squirrel-<name>.agent.md` to the canonical `~/.claude/plugins/squirrel/skills/<name>/SKILL.md`. Updates to a skill body propagate without re-running the installer, matching how `--link` behaves for Codex/Cursor.

## Key Decisions

### D1 — Local files surface only. No GitHub App / Skillsets in this change.

**Decision:** Squirrel integrates with Copilot purely by placing files on disk and registering hooks. The Copilot Extensions / Skillsets path (a GitHub App that owns HTTPS endpoints) is deferred.

**Why:** The Skillsets path requires Squirrel to run a public HTTPS service that receives signed POSTs from GitHub. This contradicts the local-first design the rest of the product enforces (offline-capable Markdown vault, sync via copy-paste, no cloud account). The local-files path covers every Copilot surface the existing primary user reaches today (VS Code Chat, Copilot CLI, JetBrains), so the cost/benefit of the platform path is poor.

**Rejected alternative:** "Build a Copilot Skillset alongside the local files." Adds operational surface (TLS, signature verification, uptime) for a user base of one. Reconsider if Squirrel grows multi-user.

### D2 — User-level install is the default; workspace is an opt-in flag.

**Decision:** `squirrel install --agent copilot` writes to `~/.copilot/` by default. `--workspace` switches to `.github/` files.

**Why:** User-level matches the install model the other agents use (`~/.codex/`, `~/.cursor/rules/squirrel/`, `~/.claude/plugins/squirrel/`) and reaches every workspace the user opens. Workspace-level pollutes the repo with files the user must commit; it is the right answer for a team adopting Squirrel together but the wrong default for the single-user primary case. Making it an explicit flag forces a conscious choice.

**Rejected alternative:** "Workspace-only, like a normal `.github/` integration would expect." Forces the user to re-install in every repo, doesn't match Squirrel's existing per-agent model, and creates merge-conflict risk on `.github/copilot-instructions.md` if other tools also write there.

### D3 — One source-of-truth hook mapping, two adapter wrappers.

**Decision:** Hook events are defined once in a JSON mapping co-located with `agent-pack/hooks/hooks.json`. Two thin shell wrappers (`hook-adapter.sh`, `hook-adapter-stdin.sh`) translate Copilot's delivery shape to Squirrel's INT-007 env-var contract before exec'ing the same inline bash bodies the Claude install uses.

**Why:** Forking the inline bash bodies for each agent would mean two implementations of "is this a SQUIRREL-PACKAGE paste" and "is this decisional language" to maintain. The adapter wrapper isolates the only Copilot-specific concern (delivery shape) and leaves the matching logic shared.

**Rejected alternative:** "Re-implement the matchers in Python and call them from both adapters." More code, more bugs, more drift. The bash matchers are 3 lines each; not worth a refactor.

### D4 — `session-state/*.jsonl` is a third fallback, not a primary source.

**Decision:** `session_scanner.py` reads `~/.copilot/session-state/*.jsonl` only if the manifest has no rows for the session. The manifest, populated by the `postToolUse` hook, remains the primary source.

**Why:** The manifest schema is stable and owned by Squirrel; the Copilot JSONL schema is owned by GitHub and may drift. Treating it as a fallback isolates schema-drift risk to the recovery edge case. Recovery from a session where the user forgot to install hooks (or where the hook failed silently) is the only case where the fallback is load-bearing.

**Rejected alternative:** "Mirror Copilot JSONL rows into our manifest in real time." Doubles the I/O for no recovery benefit if the hook is working; if the hook is broken, the fallback is enough.

### D5 — Skill bodies are not forked for Copilot.

**Decision:** The same SKILL.md bodies that ship to Claude/Codex/Cursor ship to Copilot. If Copilot's loader requires a different frontmatter header, the installer injects it from a template at install time, leaving the body unchanged.

**Why:** Three forks of every skill body is a maintenance trap. Frontmatter injection is mechanical and rarely changes; body content does change and must stay one source.

**Rejected alternative:** "Maintain a `agent-pack/companions/copilot/skills/` tree with Copilot-flavored copies." High duplication, drift risk, and inconsistent behaviour across agents when skills evolve.

## Out of Scope

- Copilot Extensions / Skillsets (GitHub App, public HTTPS endpoints, signed POSTs).
- Cross-machine monitoring of Copilot Coding Agent (cloud) runs via webhooks or `repository_dispatch`.
- A VS Code extension (`vscode.chat.createChatParticipant`) shipping Squirrel as a chat participant.
- Windsurf install branch (mentioned in README but has no install script today).
- Schema changes to `session-manifest.jsonl`. The same `{timestamp, cwd, file, event, session}` shape is used regardless of agent.
- Tray icon or banner UI changes in the Tauri desktop shell.
- New skill bodies or Copilot-specific Markdown skills.
- Changes to Claude/Codex/Cursor install branches.
- Telemetry collection beyond what hooks already produce locally.
- An installer for the Copilot CLI's authentication / sign-in flow (presumed already configured by the user).
