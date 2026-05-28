# LLD: attention

ADHD-specific attention support: deadline classification (parakeet), context-switch tracking and focus scoring, ADHD-aware time-estimate buffering, and decomposition of large tasks into ADHD-friendly chunks. All computation is deterministic and script-backed; the LLM only consumes JSON and frames recommendations.

---

## Segment Boundary

- **Prefix**: `ATTN-*`
- **EARS specs**: [docs/specs/attention-specs.md](../specs/attention-specs.md)
- **Arrow doc**: [docs/arrows/attention.md](../arrows/attention.md)
- **HLD parent section**: [docs/high-level-design.md#segments](../high-level-design.md#segments)

### What this segment owns

- Parakeet-style deadline scanning and 6-level classification (`lib/deadline_scanner.py`)
- Context-switch ledger (`vault/.squirrel/switches.jsonl`) and focus-score computation (`lib/switch_tracker.py`)
- ADHD time-estimate buffer (×2-3 multiplier, `lib/estimate_buffer.py`)
- Task chunking into ADHD-friendly sessions (`lib/chunk_helper.py`)
- Skills `parakeet`, `hyperfocus-guardian`, `task-initiation`, `chunk-intent` (planned v0.3)

### What this segment does NOT own

- The intent file frontmatter or where deadlines live in the vault (owned by `vault`)
- The act of starting/ending a session (owned by `session`; attention only consumes the resulting switch event)
- Rendering the recommendations in a brief (owned by `brief`)
- Hook wiring that fires the switch event (owned by `integrations`)

## Responsibilities

- **Deterministic classification**: deadline level is computed by the script from `due_date` and today's date — never inferred by the LLM.
- **6-level parakeet scale**: critical / urgent / soon / upcoming / eventual / distant. The scale is fixed at the segment boundary; downstream code may not invent new levels.
- **Append-only switch ledger**: every project-change event appends one line to `switches.jsonl`. The ledger is never rewritten.
- **Buffer transparency**: when the segment returns a buffered estimate, it MUST also surface the raw estimate and the multiplier — never silently inflate.
- **Chunk = one ADHD session**: default chunk size targets a single sit-down session (~25-50 min focus). The script exposes the threshold as a parameter.
- **Stateless skills, stateful scripts**: skills hold no state across invocations; the scripts and the JSONL ledger are the source of truth.

## Key Flows

### Flow: Deadline scan

```
1. Triggered by session start, /sq-status, or explicit /sq-deadlines (planned)
2. attention skill calls lib/deadline_scanner.py --vault PATH --json
3. Receives classified items grouped by level
4. Surfaces critical + urgent to the user; defers the rest
```

→ EARS specs: `ATTN-001`, `ATTN-007`

### Flow: Context switch recorded

```
1. /sq-start PROYECTO-B invoked while PROYECTO-A is the active session
2. Skill calls lib/switch_tracker.py --record --from A --to B
3. Script appends a JSON line to vault/.squirrel/switches.jsonl
4. Skill optionally returns updated focus_score for the day
```

→ EARS specs: `ATTN-002`, `ATTN-005`

### Flow: ADHD-aware estimate

```
1. User says "creo que me lleva 2 horas"
2. Skill calls lib/estimate_buffer.py --estimate "2 hours" --json
3. Returns { raw: "2h", multiplier: 2.5, buffered: "5h", rationale: ... }
4. Skill presents both values, recommends the buffered one
```

→ EARS specs: `ATTN-003`

### Flow: Task chunking

```
1. User has a task >2h estimated
2. Skill calls lib/chunk_helper.py --hours N --json
3. Receives ordered chunks with one "physical next action" each
4. Skill writes the chunk plan into the intent file
```

→ EARS specs: `ATTN-004`, `ATTN-006`

## Constraints

- Scripts must remain Python-stdlib-only (no third-party deps); installation footprint is part of the product contract.
- All computation must be reproducible — same input vault state and same `today` must produce same JSON output.
- The switches ledger is bounded only by disk; downstream summaries must cope with files of arbitrary length.

## Open Questions

- [x] Should the multiplier be per-user-configurable, per-task-type, or learned? **Decision: per-user-configurable in `config.toml`** (`estimate_multiplier = 2.5`). Not per-task-type (too complex for v1) and not learned (requires data collection infrastructure). Users can tune it after observing their own estimate accuracy.
- [x] Should parakeet thresholds be configurable or fixed? **Decision: fixed in v1.** The thresholds are part of the opinionated ADHD model — letting users tweak them undermines the "it just works" guarantee. Document the rationale in `lib/deadline_scanner.py`. Revisit in a future version if field feedback shows the defaults don't fit.
- [x] Does `hyperfocus-guardian` belong in `attention` or as its own segment? **Decision: keep in `attention`.** It reads `switches.jsonl` (owned here) and triggers on time-in-session — both attention concerns. A new segment for one skill adds overhead with no architectural benefit at this scale.
