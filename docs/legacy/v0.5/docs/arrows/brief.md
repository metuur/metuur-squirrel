# Arrow: brief

Brief behavior: per-project briefs, "where am I" diagnostics, and global status reports — sourced from script-emitted JSON, never from re-parsing the vault in the LLM.

## Segment Boundary

- **Prefix**: `BRIEF-*`
- **Owner LLD**: docs/llds/brief.md
- **Spec catalog**: docs/specs/brief-specs.md

Specs whose IDs do not start with `BRIEF-` belong to a different segment. If a behavior crosses segment boundaries, pause and confirm before adding annotations across them.

## References

### HLD

- docs/high-level-design.md#segments

### LLD

- docs/llds/brief.md

### EARS

- docs/specs/brief-specs.md

### Tests

- []

### Code

- skills/brief/
- skills/where-am-i/
- commands/sq-brief.md
- commands/sq-where-am-i.md
- commands/sq-status.md (currently LLM-only — BRIEF-003 is the gap)
- lib/status_aggregator.py (consumed; owned by `vault`)

## Cascade Notes

When upstream intent changes (HLD or LLD), walk down: HLD → LLD → EARS specs → tests → code.

When a `BRIEF-*` spec is added, modified, or deferred:
- [ ] Update the spec entry in `docs/specs/brief-specs.md`
- [ ] Update or add the test annotation
- [ ] Update or add the code annotation
- [ ] Run `/uncle-dev-spec-scan` to confirm graph is coherent

## Open Questions

- Whether `/sq-status` should surface attention signals (deadline pressure) directly.
- Truncation policy when many projects are WIP.
