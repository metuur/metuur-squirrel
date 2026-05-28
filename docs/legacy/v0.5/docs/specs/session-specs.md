# session Specs

**LLD**: docs/llds/session.md
**Arrow**: docs/arrows/session.md
**Prefix**: `SESSION-*`

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

- [x] **SESSION-001**: When a session starts (via the `SessionStart` hook or `/sq-start PROYECTO`), the system SHALL locate the most recent shutdown note for the active project and present a 5–7 line loading summary covering: what is being worked on, what was last done, what is next, key decisions, and the next physical action.
- [x] **SESSION-002**: When a session ends (via the `Stop` hook or `/sq-end`), the system SHALL produce a shutdown note containing the required fields — `estado`, `next_physical_action`, `hipótesis_activa`, `bloqueado_por`, `decisiones_hoy` — and SHALL append it to the active intent file.
- [x] **SESSION-003**: When `/sq-end` is invoked, the system SHALL offer the user the option to leave one item deliberately incomplete (Hemingway trick) to ease re-entry.
- [x] **SESSION-004**: When `/sq-start` cannot unambiguously resolve a single active project, the system SHALL ask the user to select one before producing any loading summary.
- [x] **SESSION-005**: The system SHALL NOT overwrite or remove prior shutdown notes when writing a new one; shutdown notes are append-only within the intent file.
- [x] **SESSION-006**: When `/sq-start PROYECTO` is invoked twice within the same calendar day without intervening session activity, the system SHALL produce an identical loading summary (re-entry idempotency).
- [x] **SESSION-007**: When the user runs `/sq-recover`, the system SHALL read `vault/.squirrel/session-manifest.jsonl` as the primary source, falling back to `~/.claude/projects/*.jsonl` for sessions within the last 72 h. *(Unit 4 — R-4.1)*
- [x] **SESSION-008**: When recovering a session, the system SHALL exclude any session whose source environment is not listed in `allowed_inbound_environments`. *(Unit 4 — R-4.2)*
- [x] **SESSION-009**: When generating a session summary via `/sq-recover`, the system SHALL shell out to `claude -p` and cache the result at `vault/.squirrel/llm-cache/{hash}.md`, keyed by JSONL content hash. *(Unit 4 — R-4.3)*
- [x] **SESSION-010**: Where `compliance_mode` is enabled, the system SHALL redact corporate-environment data before passing session content to `claude -p`. *(Unit 4 — R-4.4)*
- [x] **SESSION-011**: When a `PostToolUse:Edit` hook fires during a session, the system SHALL append a structured manifest entry to `vault/.squirrel/session-manifest.jsonl`. *(Unit 4 — R-4.5)*
- [x] **SESSION-012**: When `/sq-recover` completes, the system SHALL present exactly these disposition options: append-to-shutdown / inbox / project / raw / discard. *(Unit 4 — R-4.6)*
