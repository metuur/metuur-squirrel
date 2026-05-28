# LLD: brief

Brief behavior: how the plugin produces user-facing summaries of working state — per-project briefs, "where am I" diagnostics, and global status reports — by consuming structured JSON from the `vault` and `attention` segments rather than re-parsing files in the LLM.

---

## Segment Boundary

- **Prefix**: `BRIEF-*`
- **EARS specs**: [docs/specs/brief-specs.md](../specs/brief-specs.md)
- **Arrow doc**: [docs/arrows/brief.md](../arrows/brief.md)
- **HLD parent section**: [docs/high-level-design.md#segments](../high-level-design.md#segments)

### What this segment owns

- `/sq-brief PROYECTO` — 6-section project brief (now / done / next / decisions / steps / context)
- `/sq-where-am-i` — multi-project WIP diagnostic with a single focus recommendation
- `/sq-status` — global vault status (WIP, parking, areas)
- Formatting JSON from script outputs into human-readable Markdown
- Recommending a single next focus when multiple projects are WIP

### What this segment does NOT own

- Parsing intent files or computing percentages (owned by `vault` via `status_aggregator.py` / `intent_parser.py`)
- Deadline classification or focus scoring (owned by `attention`)
- Writing anything to the vault — brief is read-only

## Responsibilities

- **Scripts-first**: every brief command MUST source its data from a `lib/` script that emits JSON. The LLM only formats and judges. Re-parsing vault files in the LLM is an anti-pattern.
- **Stable section order**: the 6 brief sections always appear in the same order.
- **One focus, not many**: `where-am-i` always lands on a single recommended next action, even when multiple projects compete.
- **Diagnostic, not prescriptive**: briefs describe state and suggest, but never auto-act (no auto-commits, no auto-edits).
- **Honor token budget**: brief operations are token-budgeted per README; if input JSON exceeds budget, the brief truncates with a clear marker rather than dropping data silently.

## Key Flows

### Flow: Per-project brief

```
1. User invokes /sq-brief PROYECTO
2. brief skill calls lib/status_aggregator.py --project PROYECTO --json
3. Skill renders 6 sections from JSON
4. Output is plain Markdown, ready to copy into Slack/email
```

→ EARS specs: `BRIEF-001`

### Flow: Where-am-i diagnostic

```
1. User invokes /sq-where-am-i (or returns after >24h idle)
2. brief skill calls lib/status_aggregator.py --all --json
3. Skill summarizes per-project WIP, last-activity, next-action
4. Skill picks ONE recommended focus and explains the reason
```

→ EARS specs: `BRIEF-002`

### Flow: Global status

```
1. User invokes /sq-status
2. brief skill calls lib/status_aggregator.py --all --json
3. Skill emits WIP / parking / areas overview
```

→ EARS specs: `BRIEF-003` (currently an active gap — see specs)

## Constraints

- Total tokens for `/sq-where-am-i` and `/sq-status` must stay under ~500 (see README budget table).
- Briefs must remain useful when the vault is sparse (first-time use, single project).
- Output must be plain Markdown — no agent-specific formatting that breaks copy/paste.

## Open Questions

- [x] Should `/sq-status` surface attention-segment signals? **Decision: yes, one-line banner only.** If any `critical` or `urgent` deadlines exist, prepend a single banner line to the output. The full attention report stays behind `/sq-where-am-i` and explicit deadline commands. Don't mix the inventory view with the attention view.
- [x] What's the right truncation policy with many WIP projects? **Decision: top N by deadline pressure, then recency.** Deadline pressure is the most actionable signal for ADHD users; recency alone doesn't indicate urgency. Default N = 5, configurable in `config.toml` (`status_max_projects = 5`). Show a count of hidden projects ("+ 3 more in parking").
