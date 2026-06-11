---
name: squirrel-session-end
description: Write a structured shutdown note to the active intent in the Markdown vault, so the next session can resume quickly. Use when the user says "I'm done", "let's save progress", "shutdown", "let's close this", runs /sq-end, or at hook Stop. Also applies the Hemingway trick — encourages stopping mid-task at a known continuation point. Accepts an optional `vault_name` argument; when omitted, writes to the default vault (R-7.1, R-7.3).
---

# squirrel:session-end

## Purpose
Prevent context loss between sessions. Every time the user closes a coding session, capture the cognitive state in a structured shutdown note. This is the SINGLE MOST IMPORTANT skill — without it, the system fails.

## When to invoke
- Explicit: `/sq-end`, "I'm done", "shutdown", "let's close", "let's save"
- Hook `Stop` (when the agent session ends naturally)
- If the user has been working for >90 min and shows signs of fatigue/disengagement, OFFER (don't force) to do a session-end

## Workflow

### Step 1: Identify the active intent
Read `~/.squirrel/state.json` to get `last_active_project` and `active_intent`.

If state is missing or stale, ask the user which intent we were working on. Show the top 3 most recent intents as quick-pick options.

### Step 2: Reconstruct what happened in this session
You (the agent) have the conversation history. Mine it for:
- What code was written / read / changed (look at Edit and Write tool calls)
- What commands were run (Bash calls)
- What problems were debugged
- What decisions were made
- What questions came up

### Step 3: Run git sniff
If it's a code project:
```bash
git diff HEAD --stat
git log --oneline @{1.hour.ago}..HEAD
git status -sb
```
This gives the objective record of code changes during the session.

<!-- @spec SESSION-002 -->
### Step 4: Draft the shutdown note
Compose this structure (TIMESTAMP is the current local time):

```markdown
### <YYYY-MM-DD HH:MM>
- **Status**: <what's the current state of the work — done/half-done/stuck/etc.>
               <be specific: file:line if relevant, function name, what works, what doesn't>

- **Next physical action**: <THE most important field. Concrete verb + object.>
                            <Example: "open auth.controller.ts line 47 and add await>
                                       <before the state verification">
                            <NOT abstract: NOT "continue work on auth" — be physical>

- **Active hypothesis**: <what theory am I currently testing? what do I believe is true>
                         <that I'm trying to validate? If none, write "none explicit">

- **Blocked by**: <nothing | waiting for X | need decision from Y | technical blocker Z>

- **Decisions made today**: <list of decisions made during the session, with brief rationale>
                             <If a decision is significant, suggest also creating a separate>
                             <decision note via squirrel:decision skill>

- **Open loops (pending review)**: <questions raised but not answered, things to revisit>

- **Hemingway**: <where am I stopping? Is it a "going good" point or a stuck point?>
                 <If stuck: suggest backing up to a known-good state for tomorrow's start>
```

<!-- @spec SESSION-003 -->
### Step 5: Hemingway offer (SESSION-003)
Before finalising the note, ask unconditionally:
> "Do you want to leave a task intentionally incomplete to make it easier to restart?
>  The Hemingway trick: stopping at a 'going good' point makes it easier to start tomorrow.
>  Is there something you want to leave half-done on purpose? (yes — describe which one / no)"

If the user says yes, capture the deliberately-incomplete item and include it in the `Hemingway` field of the shutdown note with the label `[intentional]`. If no, proceed normally.

### Step 6: Show draft and ask for confirmation
Present the draft. Ask: "Apply to intent <INTENT-TAG>? (yes / adjust / cancel)"

If the user wants to adjust, accept their corrections inline.

### Step 7: Apply to the intent file
Open `<vault>/01-Active-Projects/<PROJECT>/<INTENT-TAG>.md`.

Find or create the `## 🔄 Shutdown notes (most recent first)` section.

Insert the new shutdown note AT THE TOP of that section (so the most recent is first).

If the section doesn't exist, create it.

<!-- @spec SESSION-005 -->
**Append-only**: Never delete or overwrite existing shutdown notes in this section. Each note is a permanent audit trail entry.

### Step 8: Update Project Page if needed
If during the session new components/intents were discovered, suggest adding them to the Project Page. Don't auto-add — propose.

### Step 9: Update Definition of Done
Look at the intent's `Definition of Done` checkboxes. If any criteria were completed during this session, propose checking them off:

```
I see that during the session:
✓ You implemented CSRF state validation → mark "state validation" as done?
✓ You added a unit test → mark "unit test" as done?
```

### Step 10: Suggest commit
If code was modified, suggest a commit message using the tag pattern:
```
Commit suggestion:
  wip(auth): implement CSRF state — <INTENT-TAG>

Apply it with git commit?
```

### Step 11: Hemingway check
Look at git status. If there are uncommitted changes:
- If the changes are at a natural pause (function complete, test passing) → suggest commit + push
- If the changes are mid-flow → suggest committing as WIP with descriptive message, OR offer to leave a TODO comment at the cursor line for tomorrow

### Step 12: Update state
Write to `~/.squirrel/state.json`:
```json
{
  "last_active_project": "<PROJECT-TAG>",
  "last_session_ended_at": "<ISO>",
  "active_intent": "<INTENT-TAG>",
  "last_shutdown_summary": "<one-line summary>"
}
```

### Step 12.5: Record checkout

The skill must resolve the vault path. Use the config_loader pattern (same as session-start Step 2) to set `$VAULT`, or reuse it if already set in this skill's execution context.

```bash
CHECKOUT_RESULT=$(python3 lib/focus_cli.py checkout --vault "$VAULT" 2>/dev/null)
CHECKOUT_RC=$?
```

Parse the result:
- If `CHECKOUT_RC=0`: extract `duration_minutes` and `time_invested_minutes` from the JSON; include in Step 13 output (see below)
- If JSON contains `"error": "no_open_session"`: skip silently — no user-facing message
- Any other non-zero exit: show `⚠️ checkout failed — session time not recorded` and continue normally

### Step 13: Confirm
Brief output:
```
✅ Shutdown note saved to <INTENT-TAG>
   Next: <next physical action>

Anything else before closing?
```

Include the `⏱` line only when Step 12.5 produced a valid checkout result:
```
✅ Shutdown note saved to <INTENT-TAG>
   Next: <next physical action>
   ⏱ Session: {duration_minutes} min   |   Total invested: {time_invested_minutes} min

Anything else before closing?
```

## Special cases

### Session was very short (<15 min)
Skip the elaborate shutdown. Write a 2-line note:
```
### <timestamp>
- Short session. <one-line summary>. No significant changes to state.
```

### Session crossed multiple intents
Generate shutdown notes for EACH intent touched. The user might have been multitasking — capture all.

### Session was research-only (no code)
- Skip git sniff
- Focus on what was learned, what conclusions, what links collected
- Suggest creating a research note via `squirrel:capture` for the findings

### Significant blockers discovered
If the session ended because of a blocker (waiting for someone, missing info), set the intent's frontmatter `status: blocked` and add a `blocked_by` field with details.

## Anti-patterns
- ❌ Don't write generic shutdown notes ("worked on the project, made some progress")
- ❌ Don't skip the "Next physical action" field — it's the WHOLE POINT
- ❌ Don't overwrite prior shutdown notes — always append; prior notes are an audit trail
- ❌ Don't force a shutdown if the user is mid-flow and wants to continue
- ❌ Don't capture every micro-detail — the shutdown note is for ONE sentence per field

## Output style
- Concise, factual
- The shutdown note itself is the deliverable; minimal commentary around it
- If asking for confirmation, make it easy (yes / no / adjust)

## References

- Hemingway, E.: stop mid-sentence — cognitive re-entry is cheaper than starting cold (source of Hemingway technique)
- Allen, D. (2001): GTD "next physical action" — the concrete next step is the unit of cognitive handoff
- Forte, T. (2022): PARA — project notes as "thinking residue" that survives context switches
