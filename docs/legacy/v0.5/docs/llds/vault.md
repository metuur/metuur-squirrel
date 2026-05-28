# LLD: vault

Vault behavior: the on-disk layout, the semantic tag schema, the intent-file frontmatter contract, and the deterministic parsers/aggregators every other segment depends on. The vault is the single source of truth — every other segment reads from it or writes to it through this contract.

---

## Segment Boundary

- **Prefix**: `VAULT-*`
- **EARS specs**: [docs/specs/vault-specs.md](../specs/vault-specs.md)
- **Arrow doc**: [docs/arrows/vault.md](../arrows/vault.md)
- **HLD parent section**: [docs/high-level-design.md#segments](../high-level-design.md#segments)

### What this segment owns

- PARA-style folder layout (`01-Proyectos-Activos/`, `02-Areas/`, `03-Recursos/`, `04-Archivo/`)
- The semantic tag schema `PROYECTO-SUBÁREA-COMPONENTE-NNN` and its validation
- Intent-file frontmatter contract (required fields, types, defaults)
- `lib/intent_parser.py` — frontmatter + section parsing
- `lib/status_aggregator.py` — vault-wide JSON aggregation
- `lib/tag_parser.py` — tag validation and inference helpers
- `vault_io.py` — read/write primitives (planned, currently inlined in skills)

### What this segment does NOT own

- The decision *to capture* a note (owned by `capture`); vault only owns *how* a note is stored.
- The audit log of applied sync packages (owned by `sync`, lives under `.squirrel/applied/`)
- The switches ledger (owned by `attention`, lives under `.squirrel/switches.jsonl`)
- Vault rendering or editing (delegated to the user's chosen editor)

## Responsibilities

- **One canonical layout**: PARA. No alternative layouts supported in v1. Configurable root path only.
- **Tag schema is enforced at write time**: invalid tags MUST be rejected by `tag_parser` before any file is written.
- **Intent frontmatter is a contract**: required fields are `id`, `proyecto`, `estado`, `creado`, `tags`. Optional fields (`due_date`, `chunks`, etc.) are documented in `templates/intent.md`.
- **Parser is the only reader**: other segments MUST go through `intent_parser` / `status_aggregator`. Ad-hoc YAML or regex parsing in skills is forbidden.
- **JSON contracts are stable**: the JSON shape returned by `status_aggregator.py --json` is a versioned contract; breaking changes require a `schema_version` bump.
- **No vault mutation outside declared writers**: only `capture`, `session`, `sync` may write. `brief`, `attention`, `integrations` are read-only with respect to the vault.

## Key Flows

### Flow: Status aggregation

```
1. Caller (brief / where-am-i) requests JSON status
2. lib/status_aggregator.py walks PARA folders
3. lib/intent_parser.py parses each intent (frontmatter + sections)
4. Aggregator computes per-project stats (percent_done, last_activity, blockers)
5. Returns single JSON document
```

→ EARS specs: `VAULT-004`, `VAULT-005`

### Flow: Tag validation at capture time

```
1. capture skill proposes tag T
2. tag_parser validates against schema; if invalid, returns error + suggested correction
3. capture either auto-corrects or asks user
```

→ EARS specs: `VAULT-003`

### Flow: First-time vault initialization

```
1. /sq-init invoked
2. Skill creates PARA folder skeleton at configured root
3. Skill seeds .squirrel/ for audit logs and switches ledger
4. Skill writes a sample intent and project page using templates/
```

→ EARS specs: `VAULT-001`, `VAULT-002`, `VAULT-006`

## Constraints

- Must operate on plain filesystem; no DB, no index, no daemon.
- Parsing must be Python-stdlib-only (no PyYAML; use simple YAML subset documented in templates).
- Status aggregation for a 200-intent vault must complete in well under 1 second on a laptop.

## Open Questions

- [x] Should the tag schema allow more than 3 dash-segments for deeply nested areas, or is the depth cap a feature? **Decision: the cap is a feature.** Max 3 dash-segments enforced; deeper tags are rejected by `tag_parser`. The constraint prevents over-classification and reduces ADHD decision fatigue at capture time.
- [x] When the vault contains malformed frontmatter, should the parser skip-with-warning or fail-loud? **Decision: read operations skip-with-warning** (log to stderr + emit `malformed_count` in JSON output); **write operations fail-loud** if the target file already has malformed frontmatter. Keeps the vault usable on a messy state while protecting writes.
- [x] Should `.squirrel/` move under a user-config-dir instead of inside the vault, so vault sync tools don't surface internal state? **Decision: keep it inside the vault.** Moving it splits the audit trail from the data it audits and breaks the property that copying/cloning the vault carries its history. Solve the sync-tool concern by adding `.squirrel/` to `.gitignore` and excluding it from `sync-out` scope declarations.
