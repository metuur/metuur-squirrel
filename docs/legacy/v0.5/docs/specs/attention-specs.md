# attention Specs

**LLD**: docs/llds/attention.md
**Arrow**: docs/arrows/attention.md
**Prefix**: `ATTN-*`

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

- [x] **ATTN-001**: When deadlines are scanned, the system SHALL classify each item into exactly one of six parakeet levels: `critical`, `urgent`, `soon`, `upcoming`, `eventual`, `distant`. Classification SHALL be computed by `lib/deadline_scanner.py` from intent `due_date` and the current date, not inferred by the LLM.
- [x] **ATTN-002**: When the active project changes (via `/sq-start PROYECTO-B` while project A is active), the system SHALL append a single JSON line to `vault/.squirrel/switches.jsonl` containing `from`, `to`, `timestamp`, and optional `reason`.
- [x] **ATTN-003**: When the user supplies a raw time estimate, the system SHALL return both the raw estimate and an ADHD-buffered estimate (multiplier ×2–3 via `lib/estimate_buffer.py`), and SHALL surface the multiplier used.
- [x] **ATTN-004**: When a task's estimated duration exceeds a configurable chunk threshold (default 2 hours), the system SHALL propose a decomposition into ADHD-friendly chunks via `lib/chunk_helper.py`, with one stated "physical next action" per chunk.
- [x] **ATTN-005**: When focus score for a window W is requested, the system SHALL compute it from `switches.jsonl` over W, and the same input data and window SHALL yield the same score (deterministic).
- [x] **ATTN-006**: The system SHALL NOT silently apply the ADHD buffer; if a buffered estimate is reported, the raw value and multiplier SHALL also be reported.
- [x] **ATTN-007**: When `/sq-where-am-i` or `/sq-status` runs, the attention segment SHALL surface only `critical` and `urgent` deadlines by default; lower levels SHALL be suppressed unless explicitly requested.
- [x] **ATTN-008**: The `switches.jsonl` ledger SHALL be append-only; the system SHALL NOT rewrite, reorder, or truncate prior entries.
- [x] **ATTN-009**: When `deadline_scanner.py` returns items at `critical` or `urgent` level, the system SHALL display a macOS notification via `companions/macos-reminders/reminder-daemon.sh` with "Focus now", "Snooze", and "Dismiss" buttons. *(Unit 2 — R-2.1)*
- [x] **ATTN-010**: While the macOS reminder daemon is running, the system SHALL suppress notifications outside the configured workday window; if the per-window dialog cap is reached, the system SHALL suppress further notifications until the next window opens. *(Unit 2 — R-2.2, R-2.3)*
- [x] **ATTN-011**: Where the host OS is not macOS, the system SHALL skip companion installation and log a no-op message rather than failing. *(Unit 2 — R-2.6)*
- [x] **ATTN-012**: When the user invokes `/sq-chunk`, the system SHALL execute `python3 lib/chunk_helper.py` and display the resulting task breakdown as a slash command response. *(Unit 3 — R-3.1)*
- [x] **ATTN-013**: When the user invokes `/sq-estimate`, the system SHALL execute `python3 lib/estimate_buffer.py` and display the buffered estimates (including raw value and multiplier) as a slash command response. *(Unit 3 — R-3.2)*
