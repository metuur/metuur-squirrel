# LLD: sync

Air-gap sync behavior: how the plugin packages selected vault content into a self-contained, hash-verified Markdown block (`sync-out`), and how it validates, diffs, and applies such a block on the receiving side (`sync-in`) — all with the human as the explicit transport.

---

## Segment Boundary

- **Prefix**: `SYNC-*`
- **EARS specs**: [docs/specs/sync-specs.md](../specs/sync-specs.md)
- **Arrow doc**: [docs/arrows/sync.md](../arrows/sync.md)
- **HLD parent section**: [docs/high-level-design.md#segments](../high-level-design.md#segments)

### What this segment owns

- The `SQUIRREL-PACKAGE` protocol (header, scope, hash, payload, operations)
- `/sq-sync-out` — package generation, hash computation, clipboard/email handoff
- `/sq-sync-in` — package detection, hash verification, diff, confirm, apply
- Audit log of applied packages (`.squirrel/applied/`)
- Idempotent apply semantics (re-applying the same package is a no-op)

### What this segment does NOT own

- Encryption of packages (out-of-scope per HLD; user's GPG is opt-in)
- The actual transport (email / clipboard / messaging — the human carries it)
- Vault tag schema or frontmatter format (owned by `vault`)
- Cross-environment configuration (owned by `integrations` — e.g. which agent host is on which side)

## Responsibilities

- **Hash before payload**: SHA-256 over the canonicalized payload is part of the package header; `sync-in` MUST verify before applying.
- **Explicit scope**: every `sync-out` declares its scope (`PROYECTO-TAG:area/*`) in the header. No implicit "everything I touched today" packages.
- **Diff-then-confirm**: `sync-in` MUST present a unified diff and require an explicit user confirmation before any vault write.
- **Idempotency**: applying the same package twice MUST produce identical vault state and one audit record per *distinct* apply (not per attempt).
- **Audit is append-only**: `.squirrel/applied/YYYY-MM-DD-<hash>.json` is written once per successful apply and never deleted by the plugin.
- **No network**: the segment MUST NOT initiate any network request. Mail/HTTP/etc. are the user's choice via OS-level handoff (`mailto:` is acceptable; in-band sending is not).

## Key Flows

### Flow: Sync out

```
1. User invokes /sq-sync-out --scope=PROYECTO:research
2. sync-out skill calls lib/package_protocol.py to:
   - Collect matching notes from vault
   - Canonicalize payload
   - Compute SHA-256
   - Emit SQUIRREL-PACKAGE block
3. Skill shows the block in chat and asks: clipboard / email draft / show only?
```

→ EARS specs: `SYNC-001`, `SYNC-002`

### Flow: Sync in

```
1. User pastes a block starting with <!-- SQUIRREL-PACKAGE
2. sync-in skill (or UserPromptSubmit hook) detects the marker
3. lib/package_protocol.py parses + verifies hash
4. On mismatch: refuse, explain, exit
5. On match: compute diff vs current vault, present to user
6. User confirms; lib applies each note with the declared operation (create/update/merge/append)
7. Skill writes audit record to .squirrel/applied/
```

→ EARS specs: `SYNC-003`, `SYNC-004`, `SYNC-005`, `SYNC-006`

## Constraints

- A package MUST round-trip losslessly: `sync-out` then `sync-in` on the same vault is a no-op.
- Hash mismatch MUST fail closed (no partial apply).
- Apply MUST be atomic per note — partial-write of a single note is not allowed.

## Open Questions

- [x] Should the protocol carry a schema version? **Decision: yes.** Add `protocol_version: 1` to the SQUIRREL-PACKAGE header immediately. Migration story: a `sync-in` receiving an unknown version surfaces a clear "upgrade required" error and refuses to apply — no silent corruption.
- [x] How should `sync-in` handle conflicts when the same note has been edited on both sides? **Decision: fail closed.** Present a conflict report showing both versions side-by-side and require an explicit user choice: keep-local / keep-remote / abort. No auto-merge. Data loss is unacceptable for an ADHD context tool.
- [x] Should the audit record include a snapshot of the prior file state? **Decision: package hash + operations only.** Snapshots double storage and create maintenance burden. Prior state is recoverable from git history or the intent file's own append-only session history.
