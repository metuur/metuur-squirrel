# brief Specs

**LLD**: docs/llds/brief.md
**Arrow**: docs/arrows/brief.md
**Prefix**: `BRIEF-*`

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

- [x] **BRIEF-001**: When `/sq-brief PROYECTO` is invoked, the system SHALL emit a Markdown brief with six sections in this stable order: `now`, `done`, `next`, `decisions`, `steps`, `context`.
- [x] **BRIEF-002**: When `/sq-where-am-i` is invoked, the system SHALL produce a per-project WIP summary including last activity timestamp and next action, AND SHALL recommend exactly one project as the next focus with a stated rationale.
- [x] **BRIEF-003**: When `/sq-status` is invoked, the system SHALL source its data from `lib/status_aggregator.py` JSON output rather than re-parsing vault files in the LLM. (*Current gap: command is LLM-only; see research note 2026-05-24.*)
- [x] **BRIEF-004**: The system SHALL NOT mutate any vault file during a brief operation; brief operations are strictly read-only.
- [x] **BRIEF-005**: When the rendered brief would exceed the per-command token budget (per README), the system SHALL truncate sections with an explicit `[truncated: N items]` marker rather than silently dropping content.
- [x] **BRIEF-006**: When `status_aggregator.py` exits with a non-zero code, the system SHALL surface the error message to the user and exit without crashing the `/sq-status` command. *(Unit 1 — R-1.2)*
