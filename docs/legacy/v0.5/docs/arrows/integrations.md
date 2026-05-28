# Arrow: integrations

Agent-host integration behavior: how the same agent-agnostic core (skills, scripts, templates) loads in Claude Code, Codex CLI, Cursor, and the standalone `sq` CLI. Host-specific glue lives only here; skill bodies remain identical across hosts.

## Segment Boundary

- **Prefix**: `INT-*`
- **Owner LLD**: docs/llds/integrations.md
- **Spec catalog**: docs/specs/integrations-specs.md

Specs whose IDs do not start with `INT-` belong to a different segment. If a behavior crosses segment boundaries, pause and confirm before adding annotations across them.

## References

### HLD

- docs/high-level-design.md#segments

### LLD

- docs/llds/integrations.md

### EARS

- docs/specs/integrations-specs.md

### Tests

- []

### Code

- .claude-plugin/plugin.json
- codex-plugin.toml (planned)
- commands/*.md (10 slash commands)
- hooks/hooks.json
- config/squirrel.toml.example (planned)
- INSTALL.md
- sq CLI (planned — INT-008)

## Cascade Notes

When upstream intent changes (HLD or LLD), walk down: HLD → LLD → EARS specs → tests → code.

When an `INT-*` spec is added, modified, or deferred:
- [ ] Update the spec entry in `docs/specs/integrations-specs.md`
- [ ] Update or add the test annotation
- [ ] Update or add the code annotation
- [ ] Run `/uncle-dev-spec-scan` to confirm graph is coherent

## Open Questions

- Whether Codex/Cursor manifests should be generated from one source-of-truth.
- Cross-host equivalence testing strategy.
- Config location: home-dir vs vault-local.
