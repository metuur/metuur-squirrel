# capture Specs

**LLD**: docs/llds/capture.md
**Arrow**: docs/arrows/capture.md
**Prefix**: `CAPTURE-*`

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

- [x] **CAPTURE-001**: When the user invokes `/sq-capture` or expresses an intent to save a note (e.g. "anotá esto", "guarda esto"), the system SHALL create a Markdown file in the vault with a single valid semantic tag, the user's content verbatim, and an ISO-8601 `creado` timestamp.
- [x] **CAPTURE-002**: When the user expresses an architectural decision (matched by `UserPromptSubmit` patterns such as "voy a usar X", "decidí Y", "elegí Z porque"), the system SHALL propose an ADR-ligero note containing context, alternatives, decision, and consequences, and SHALL request confirmation before writing.
- [x] **CAPTURE-003**: The system SHALL NOT write any capture note to the vault without a tag that validates against the schema owned by `vault` (`VAULT-003`).
- [x] **CAPTURE-004**: When two captures with identical content target the same project within a configurable dedup window (default 60s), the system SHALL update the existing note rather than create a duplicate.
- [x] **CAPTURE-005**: The system SHALL preserve the user's original wording in the note body and SHALL NOT summarize or rephrase captured content at capture time.
