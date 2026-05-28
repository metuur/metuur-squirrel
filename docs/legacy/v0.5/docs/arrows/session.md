# Arrow: session

Session-lifecycle behavior: loading notes on session start, structured shutdown notes on session end, inactivity prompts, and the Hemingway-trick incomplete-by-design closer.

## Segment Boundary

- **Prefix**: `SESSION-*`
- **Owner LLD**: docs/llds/session.md
- **Spec catalog**: docs/specs/session-specs.md

Specs whose IDs do not start with `SESSION-` belong to a different segment. If a behavior crosses segment boundaries, pause and confirm before adding annotations across them.

## References

### HLD

- docs/high-level-design.md#segments

### LLD

- docs/llds/session.md

### EARS

- docs/specs/session-specs.md

### Tests

- []

### Code

- skills/session-start/
- skills/session-end/
- commands/sq-start.md
- commands/sq-end.md
- hooks/hooks.json (SessionStart, Stop wiring lives in `integrations`)

## Cascade Notes

When upstream intent changes (HLD or LLD), walk down: HLD → LLD → EARS specs → tests → code.

When a `SESSION-*` spec is added, modified, or deferred:
- [ ] Update the spec entry in `docs/specs/session-specs.md`
- [ ] Update or add the test annotation
- [ ] Update or add the code annotation
- [ ] Run `/uncle-dev-spec-scan` to confirm graph is coherent

## Open Questions

- Inactivity threshold for auto-shutdown prompts.
- Whether session-start auto-opens files in the agent's context.
