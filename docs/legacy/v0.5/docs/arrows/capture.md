# Arrow: capture

Capture behavior: how the plugin records notes and architectural decisions to the vault on demand or via detected triggers, with semantic tags applied at write time.

## Segment Boundary

- **Prefix**: `CAPTURE-*`
- **Owner LLD**: docs/llds/capture.md
- **Spec catalog**: docs/specs/capture-specs.md

Specs whose IDs do not start with `CAPTURE-` belong to a different segment. If a behavior crosses segment boundaries, pause and confirm before adding annotations across them.

## References

### HLD

- docs/high-level-design.md#segments

### LLD

- docs/llds/capture.md

### EARS

- docs/specs/capture-specs.md

### Tests

- []

### Code

- skills/capture/
- skills/decision/
- commands/sq-capture.md
- commands/sq-decision.md

## Cascade Notes

When upstream intent changes (HLD or LLD), walk down: HLD → LLD → EARS specs → tests → code.

When a `CAPTURE-*` spec is added, modified, or deferred:
- [ ] Update the spec entry in `docs/specs/capture-specs.md`
- [ ] Update or add the test annotation
- [ ] Update or add the code annotation
- [ ] Run `/uncle-dev-spec-scan` to confirm graph is coherent

## Open Questions

- Multi-project ambiguity at capture time when no session is active.
- Retroactive decision-capture linking to a prior intent.
