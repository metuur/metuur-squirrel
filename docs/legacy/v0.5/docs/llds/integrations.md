# LLD: integrations

Agent-host integration behavior: how the same agent-agnostic core (skills, scripts, templates) is loaded by each supported host (Claude Code, Codex CLI, Cursor/VSCode), how slash commands and hooks are wired per host, and how installation/configuration work. This segment is the only place agent-specific glue may live.

---

## Segment Boundary

- **Prefix**: `INT-*`
- **EARS specs**: [docs/specs/integrations-specs.md](../specs/integrations-specs.md)
- **Arrow doc**: [docs/arrows/integrations.md](../arrows/integrations.md)
- **HLD parent section**: [docs/high-level-design.md#segments](../high-level-design.md#segments)

### What this segment owns

- `.claude-plugin/plugin.json` — Claude Code manifest
- `codex-plugin.toml` — Codex CLI manifest (planned)
- `commands/sq-*.md` — slash command definitions (`/sq-*`)
- `hooks/hooks.json` — host-side hook wiring (SessionStart, UserPromptSubmit, Stop)
- `config/squirrel.toml.example` — user config template
- `/sq-init` — first-time setup flow
- Per-host installation instructions (`INSTALL.md`)
- The standalone `sq` CLI — a host-agnostic surface that invokes skills directly and delegates any LLM-judgment step to `claude -p` (one-shot, no persistent runtime)

### What this segment does NOT own

- The behavior of any skill body — skills are agent-agnostic Markdown and belong to their owning behavior segment.
- The vault layout or scripts (owned by `vault` and other segments).
- The substance of what hooks invoke — only the wiring. The skills themselves live in `capture` / `session` / etc.
- An MCP server. Explicitly excluded per HLD; the `sq` CLI + skills + `claude -p` is the supported invocation model.

## Responsibilities

- **Glue stays here**: any code or config that names a specific agent host MUST live in this segment. Skills MUST remain identical across hosts.
- **Identical skill bodies across hosts**: a skill `SKILL.md` is copied unchanged between Claude Code, Codex, and Cursor surfaces. Only manifests differ.
- **One config file**: `~/.squirrel/config.toml` is the single user-facing configuration. No per-host config files.
- **Install is documented per host**: each supported host has a section in `INSTALL.md` with copy-pasteable steps.
- **Hook wiring is host-shaped, hook payload is host-agnostic**: each host has its own hook event names, but the skill that runs in response consumes a normalized payload (project, event, timestamp).
- **No host detection in skills**: skills MUST NOT branch on the host. If host-specific behavior is needed, it belongs in a host-specific adapter in this segment.

## Key Flows

### Flow: First-time install in Claude Code

```
1. User clones / copies the plugin into ~/.claude/plugins/squirrel/
2. Claude Code reads .claude-plugin/plugin.json on next launch
3. Slash commands /sq-* appear; skills become invocable
4. User runs /sq-init to seed vault layout + config file
```

→ EARS specs: `INT-001`, `INT-005`

### Flow: Hook wiring on Claude Code

```
1. hooks/hooks.json registers SessionStart, UserPromptSubmit, Stop with matchers
2. SessionStart hook → invokes session-start skill
3. UserPromptSubmit hook → dispatches to capture / decision skills by matcher
4. Stop hook → invokes session-end skill
```

→ EARS specs: `INT-003`, `INT-004`

### Flow: Same plugin on Codex CLI

```
1. User points Codex at the same repository
2. codex-plugin.toml is read; same skills/, commands/, lib/ are exposed
3. Codex-specific hook format is generated from a normalized source (planned)
```

→ EARS specs: `INT-002`

## Constraints

- Must not require any host-specific runtime beyond what the host already ships.
- Must not modify global host configuration; everything lives under the plugin directory or `~/.squirrel/`.
- Skill files MUST be byte-identical across hosts (verified by checksum in CI, planned).

## Open Questions

- [x] Should Codex and Cursor manifests be generated from a single source-of-truth? **Decision: yes.** Add `scripts/generate-manifests.py` + `plugin-spec.yaml`. The script emits each host's manifest format from the shared spec. Run as part of CI to catch drift; run on `/sq-init` to regenerate locally.
- [x] How do we test cross-host equivalence? **Decision: golden transcript YAML files** under `tests/golden/<host>/`. Each file specifies `input:` and `expected_output_fragments:`. LLM steps use `claude -p` one-shot; script steps run directly. Checked in CI via `scripts/run-golden-tests.sh`.
- [x] Should `/sq-init` write the config to `~/.squirrel/` or to a vault-local `.squirrel/`? **Decision: keep `~/.squirrel/config.toml` (home-dir).** The vault may be on a synced drive or shared; user config must not travel with it. The current HLD choice is correct.
