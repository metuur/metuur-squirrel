# Arrow: attention

ADHD-specific attention support: parakeet deadline classification, append-only switches ledger with focus scoring, ADHD time-estimate buffering, and task chunking. All deterministic, all script-backed.

## Segment Boundary

- **Prefix**: `ATTN-*`
- **Owner LLD**: docs/llds/attention.md
- **Spec catalog**: docs/specs/attention-specs.md

Specs whose IDs do not start with `ATTN-` belong to a different segment. If a behavior crosses segment boundaries, pause and confirm before adding annotations across them.

## References

### HLD

- docs/high-level-design.md#segments

### LLD

- docs/llds/attention.md

### EARS

- docs/specs/attention-specs.md

### Tests

- tests/test_foundation.py (covers deadline_scanner, switch_tracker, estimate_buffer, chunk_helper)

### Code

- lib/deadline_scanner.py
- lib/switch_tracker.py
- lib/estimate_buffer.py
- lib/chunk_helper.py
- vault/.squirrel/switches.jsonl (runtime data, append-only)
- skills/parakeet/ (planned v0.3)
- skills/hyperfocus-guardian/ (planned v0.3)
- skills/task-initiation/ (planned v0.3)
- skills/chunk-intent/ (planned v0.3)

## Cascade Notes

When upstream intent changes (HLD or LLD), walk down: HLD → LLD → EARS specs → tests → code.

When an `ATTN-*` spec is added, modified, or deferred:
- [ ] Update the spec entry in `docs/specs/attention-specs.md`
- [ ] Update or add the test annotation
- [ ] Update or add the code annotation
- [ ] Run `/uncle-dev-spec-scan` to confirm graph is coherent

## Open Questions

- Multiplier configurability (per-user, per-task, or learned).
- Parakeet thresholds: fixed or configurable.
- Whether `hyperfocus-guardian` belongs here or as its own segment.
