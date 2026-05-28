# sync Specs

**LLD**: docs/llds/sync.md
**Arrow**: docs/arrows/sync.md
**Prefix**: `SYNC-*`

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

- [x] **SYNC-001**: When `/sq-sync-out --scope=<scope>` is invoked, the system SHALL emit a `SQUIRREL-PACKAGE` block containing the header (from, to, generated_at, scope, intent), a SHA-256 hash over the canonicalized payload, and one note section per included artifact.
- [x] **SYNC-002**: Every emitted package SHALL declare its scope explicitly; the system SHALL NOT support implicit "everything I touched" packages.
- [x] **SYNC-003**: When a pasted block beginning with `<!-- SQUIRREL-PACKAGE` is detected, the system SHALL verify the declared SHA-256 against the canonicalized payload before any vault mutation. On mismatch, the system SHALL refuse to apply and SHALL surface the discrepancy.
- [x] **SYNC-004**: Before applying any verified package, the system SHALL present a unified diff of intended vault changes and SHALL require explicit user confirmation.
- [x] **SYNC-005**: When a package is successfully applied, the system SHALL write exactly one audit record at `.squirrel/applied/YYYY-MM-DD-<hash>.json` containing the package hash, source, scope, applied operations, and timestamp.
- [x] **SYNC-006**: Applying the same package twice SHALL produce identical vault state (idempotency); a second apply SHALL be a no-op with respect to file contents.
- [x] **SYNC-007**: The system SHALL NOT initiate any network request to transport packages between environments; the only handoffs SHALL be OS-level (clipboard, `mailto:` draft) initiated by the user.
- [x] **SYNC-008**: When a single note within a package fails to apply, the system SHALL leave the vault unchanged for that note (atomic per-note apply) and SHALL report the failure to the user.
