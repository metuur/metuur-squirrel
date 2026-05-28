# vault Specs

**LLD**: docs/llds/vault.md
**Arrow**: docs/arrows/vault.md
**Prefix**: `VAULT-*`

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

- [x] **VAULT-001**: The vault SHALL be organized in a PARA-style layout with top-level folders `01-Proyectos-Activos/`, `02-Areas/`, `03-Recursos/`, `04-Archivo/`, rooted at a user-configured path.
  - `commands/sq-init.md` updated to create all 4 PARA folders.
- [x] **VAULT-002**: Every intent file SHALL carry a YAML frontmatter block with the required fields `id`, `proyecto`, `estado`, `creado`, `tags`. Optional fields SHALL be documented in `templates/intent.md`.
  - `templates/intent.md` updated to label required vs optional fields (with `prioridad`, `deadline`, `stakeholders` as optional).
- [x] **VAULT-003**: The system SHALL accept only tags that match the schema `PROYECTO-SUBÁREA-COMPONENTE-NNN` (uppercase ASCII segments joined by `-`, terminating in a zero-padded numeric suffix). `lib/tag_parser.py` SHALL be the sole authority for validation.
  - Regex `^[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-[A-Z][A-Z0-9]*-\d{3}$` enforced. `parse()` returns `{proyecto, subarea, componente, numero}`. Covered by `tests/test_vault_specs.py::TestVault003TagParser`.
- [x] **VAULT-004**: When any segment needs intent state, it SHALL obtain it via `lib/intent_parser.py` and/or `lib/status_aggregator.py`; ad-hoc YAML or regex parsing SHALL NOT be used in skills.
  - Grep of `skills/` found zero occurrences of `re.match`, `re.compile`, `yaml.load`, or `yaml.safe_load`. All skills delegate to the script layer.
- [x] **VAULT-005**: The JSON contract emitted by `lib/status_aggregator.py --json` SHALL carry a `schema_version` field; breaking changes to the shape SHALL bump the version.
  - `schema_version: "001"` present at top level. Covered by `tests/test_vault_specs.py::TestVault005SchemaVersion`.
- [x] **VAULT-006**: When `/sq-init` runs, the system SHALL create the PARA skeleton, seed `.squirrel/` for audit logs and the switches ledger, and write one sample intent and project page from `templates/`.
  - `commands/sq-init.md` updated: step 3 adds `.squirrel/audit-logs/` and `switches.jsonl`; step 4b writes a sample intent + project page from `templates/intent.md`.
- [x] **VAULT-007**: The system SHALL NOT permit vault writes from segments other than `capture`, `session`, and `sync`; `brief`, `attention`, and `integrations` SHALL be read-only consumers of the vault.
  - Grep of `skills/brief/`, `skills/where-am-i/`, `skills/parakeet/` found no write operations. VAULT-007 anti-pattern note added to all three SKILL.md files.
- [x] **VAULT-008**: The system SHALL operate without third-party Python dependencies; all parsing and aggregation SHALL use Python stdlib only.
  - All `lib/*.py` imports are stdlib + intra-lib siblings only. Covered by `tests/test_vault_specs.py::TestVault008StdlibOnly`.
