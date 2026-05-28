# Arrow: vault

Vault behavior: PARA layout, semantic tag schema, intent-file frontmatter contract, and the deterministic parsers and aggregators every other segment depends on.

## Segment Boundary

- **Prefix**: `VAULT-*`
- **Owner LLD**: docs/llds/vault.md
- **Spec catalog**: docs/specs/vault-specs.md

Specs whose IDs do not start with `VAULT-` belong to a different segment. If a behavior crosses segment boundaries, pause and confirm before adding annotations across them.

## References

### HLD

- docs/high-level-design.md#segments

### LLD

- docs/llds/vault.md

### EARS

- docs/specs/vault-specs.md

### Tests

- tests/test_foundation.py (covers intent_parser, status_aggregator)
- tests/fixtures/vault-minimal/

### Code

- lib/intent_parser.py
- lib/status_aggregator.py
- lib/tag_parser.py (planned — referenced by VAULT-003)
- templates/intent.md
- templates/project-page.md

## Cascade Notes

When upstream intent changes (HLD or LLD), walk down: HLD → LLD → EARS specs → tests → code.

When a `VAULT-*` spec is added, modified, or deferred:
- [ ] Update the spec entry in `docs/specs/vault-specs.md`
- [ ] Update or add the test annotation
- [ ] Update or add the code annotation
- [ ] Run `/uncle-dev-spec-scan` to confirm graph is coherent

## Open Questions

- Tag depth cap (3 dash-segments) — feature or limitation.
- Malformed-frontmatter policy: skip-with-warning vs fail-loud.
- Whether `.squirrel/` should live inside the vault or under a user-config dir.
