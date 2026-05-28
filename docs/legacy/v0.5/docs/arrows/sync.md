# Arrow: sync

Air-gap sync behavior: the `SQUIRREL-PACKAGE` protocol, hash-verified package generation and application, diff-then-confirm semantics, and the append-only audit log.

## Segment Boundary

- **Prefix**: `SYNC-*`
- **Owner LLD**: docs/llds/sync.md
- **Spec catalog**: docs/specs/sync-specs.md

Specs whose IDs do not start with `SYNC-` belong to a different segment. If a behavior crosses segment boundaries, pause and confirm before adding annotations across them.

## References

### HLD

- docs/high-level-design.md#segments

### LLD

- docs/llds/sync.md

### EARS

- docs/specs/sync-specs.md

### Tests

- []

### Code

- skills/sync-out/
- skills/sync-in/
- commands/sq-sync-out.md
- commands/sq-sync-in.md
- lib/package_protocol.py

## Cascade Notes

When upstream intent changes (HLD or LLD), walk down: HLD → LLD → EARS specs → tests → code.

When a `SYNC-*` spec is added, modified, or deferred:
- [ ] Update the spec entry in `docs/specs/sync-specs.md`
- [ ] Update or add the test annotation
- [ ] Update or add the code annotation
- [ ] Run `/uncle-dev-spec-scan` to confirm graph is coherent

## Open Questions

- Protocol schema_version and migration story (currently v1).
- Conflict resolution when the same note diverges on both sides.
- Whether audit records should snapshot prior file state or only the hash.
