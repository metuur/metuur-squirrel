# integrations Specs

**LLD**: docs/llds/integrations.md
**Arrow**: docs/arrows/integrations.md
**Prefix**: `INT-*`

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

- [x] **INT-001**: The plugin SHALL be loadable in Claude Code by placement under `~/.claude/plugins/squirrel/` plus a valid `.claude-plugin/plugin.json`, without requiring modification of any global Claude Code configuration.
- [x] **INT-002**: The plugin SHALL be loadable in Codex CLI via a `codex-plugin.toml` manifest using the same `skills/`, `commands/`, and `lib/` directories unchanged.
- [x] **INT-003**: The system SHALL register host-side hooks for `SessionStart`, `UserPromptSubmit` (with at least 3 matchers for capture / decision / inactivity), and `Stop`, dispatching each to the appropriate skill in the owning behavior segment.
- [x] **INT-004**: Skill body files (`SKILL.md`) SHALL remain byte-identical across hosts; host-specific glue SHALL live only in the `integrations` segment (manifests, hook formats, command paths).
- [x] **INT-005**: When `/sq-init` runs, the system SHALL create the user configuration file at `~/.squirrel/config.toml` from `config/squirrel.toml.example` if it does not already exist, and SHALL NOT overwrite an existing config.
- [x] **INT-006**: The system SHALL NOT branch on host identity inside skill bodies; any host-dependent behavior SHALL be delegated to an adapter in `integrations`.
- [x] **INT-007**: All host hooks SHALL deliver a normalized payload to the invoked skill containing at least `event`, `project` (if resolvable), and `timestamp`.
- [x] **INT-008**: The system SHALL expose a standalone `cb` CLI that invokes skill functionality without requiring an agent host; any LLM-judgment step inside the CLI SHALL be delegated to `claude -p` (one-shot) rather than a persistent runtime.
- [x] **INT-009**: The system SHALL NOT ship an MCP server; an MCP-based invocation path is out of scope per HLD.
- [x] **INT-010**: When the user runs `/sq-reminders-install`, the system SHALL register the launchd plist under `companions/macos-reminders/` and start the daemon via `launchctl bootstrap`. *(Unit 2 — R-2.4)*
- [x] **INT-011**: When the user runs `/sq-reminders-uninstall`, the system SHALL unload the launchd service and remove the plist from the LaunchAgents directory. *(Unit 2 — R-2.5)*
