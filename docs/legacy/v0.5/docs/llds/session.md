# LLD: session

Session-lifecycle behavior: how the plugin marks the start and end of a coding session, loads prior context on entry, and writes a structured shutdown note on exit so the next session can resume cheaply.

---

## Segment Boundary

- **Prefix**: `SESSION-*`
- **EARS specs**: [docs/specs/session-specs.md](../specs/session-specs.md)
- **Arrow doc**: [docs/arrows/session.md](../arrows/session.md)
- **HLD parent section**: [docs/high-level-design.md#segments](../high-level-design.md#segments)

### What this segment owns

- Session-start loading note (`/sq-start`, `session-start` skill)
- Session-end shutdown note (`/sq-end`, `session-end` skill)
- Detecting inactivity / Stop-hook fire and prompting for shutdown
- The "Hemingway trick" — deliberately leaving one item incomplete for easier re-entry
- Linking shutdown notes back into the active intent file

### What this segment does NOT own

- The act of capturing free-form notes mid-session (owned by `capture`)
- Producing the user-facing brief content (owned by `brief`)
- Tracking the *fact* of a context switch between projects (owned by `attention`)
- Wiring the SessionStart/Stop hooks themselves into a specific host (owned by `integrations`)

## Responsibilities

- **Structured shutdown notes**: every shutdown note contains state, next physical action, active hypothesis, blockers, decisions taken today. No free-form-only shutdowns.
- **One active project per session**: session-start resolves a single active project; if ambiguous, asks the user before loading.
- **Loading notes are summaries, not dumps**: present 5-7 lines max — what / last-done / next / decisions / next action. Do not paste the whole intent.
- **Shutdown is append-only**: shutdown notes append to the intent file; they do not overwrite earlier session history.
- **Re-entry safety**: a loading note for project X must be reproducible — running `/sq-start X` twice yields the same summary.

## Key Flows

### Flow: Session start

```
1. SessionStart hook fires (or /sq-start PROYECTO invoked)
2. session-start skill locates most recent shutdown note for the project
3. Reads project page from vault
4. Produces 5-line summary: now / last / next / decisions / next-action
5. Asks: "Confirmás que retomamos esto?"
```

→ EARS specs: `SESSION-001`, `SESSION-004`

### Flow: Session end

```
1. Stop hook fires (or /sq-end invoked, or inactivity detected)
2. session-end skill identifies the active intent
3. Drafts a shutdown note with the 5 required fields
4. Asks user to confirm/adjust the draft
5. Appends shutdown note to intent; suggests commit with semantic tag
6. Optionally prompts the Hemingway trick (leave one thing on purpose)
```

→ EARS specs: `SESSION-002`, `SESSION-003`, `SESSION-005`

## Constraints

- Loading note must produce in the token budget declared for `/sq-start` (~500 tokens, see README).
- Must operate without a running daemon — only via hook events and explicit slash commands.
- Must work even when no prior shutdown note exists (first-ever session on the project).

## Open Questions

- [x] How long of an inactivity gap should trigger an auto-shutdown prompt? **Decision: 15 min default, configurable** (`inactivity_timeout_min = 15` in `config.toml`). 5 min produces too many false positives during normal pauses; 15 min matches the "noticed I drifted" window typical of ADHD work patterns. The Stop hook already handles deliberate exits; this covers the "forgot to `/sq-end`" case.
- [x] Should session-start auto-load the project's open files into the agent's context? **Decision: summary only.** Auto-loading files spikes token usage on every session start and the open-file set may not be relevant (files may have been left open for unrelated reasons). Users who need file context can trigger it explicitly with `/sq-context`.
