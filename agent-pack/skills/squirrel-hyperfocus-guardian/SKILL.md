---
name: squirrel-hyperfocus-guardian
description: Detect and interrupt hyperfocus loops. Use when the user has been on the same task >90 min without a break, when they say "I've been going for hours", "I lost track of time", "just one more thing", or when session time exceeds the configured focus limit. Offers a structured break protocol and logs the hyperfocus event. Also runs as a check-in when the user returns after an unusually long coding sprint.
---

# squirrel:hyperfocus-guardian

## Purpose

Hyperfocus is a double-edged sword: productive streaks can become unsustainable tunnel
vision that leads to burnout, missed meals, forgotten commitments, and poor decision-making
late in a session. This skill intervenes gently but firmly to impose a circuit breaker.

## When to invoke

- **Explicit**: user says "I've been at this for 3 hours", "lost track of time", "just one more
  quick thing" (the classic lie), `/hyperfocus-guardian`, "check on me"
- **Automatic** (via session timer check): session has been open >90 min on a single intent
- **Post-sprint**: user returns from a deep work session and mentions fatigue or confusion
- **Escalation**: user has said "just one more" 2+ times in the same session

## Step 1: Assess current state

Read session state:

```bash
cat ~/.squirrel/state.json 2>/dev/null
```

Extract:

- `session_started_at` — when this session began
- `last_active_project` — what they're working on
- `active_intent` — which specific task

Calculate session duration. If the file doesn't exist or session data is missing, ask the user
directly: "How long have you been at this?"

## Step 2: Classify the alert level

| Duration    | Alert level | Response                       |
| ----------- | ----------- | ------------------------------ |
| < 90 min    | None        | Don't intervene                |
| 90–120 min  | Yellow      | Gentle nudge                   |
| 120–180 min | Orange      | Strong suggestion to break     |
| > 180 min   | Red         | Mandatory break protocol       |
| > 240 min   | Critical    | Hard stop, save everything now |

If the user reported "just one more thing" multiple times → escalate one level.

## Step 3: Deliver the intervention

### Yellow (90–120 min)

```
⏱️ You've been at [INTENT] for ~[N] minutes.

That's past the 90-min mark where focus quality typically drops.
Your current progress: [what you've done this session, 1-2 lines]

→ Recommended: 10-min break now, then one more focused block.
→ Or: commit what you have, log a shutdown note, come back fresh.

Continue? Or take the break?
```

### Orange (120–180 min)

```
🟠 [N] hours into this session. Quality check time.

Signs you might be in hyperfocus:
  • The scope has expanded since you started
  • You've been "just finishing" something for 30+ min
  • You haven't eaten/moved/looked away from the screen

Your last concrete output: [last commit or last known progress]

→ Take 15 min. Set a timer.
→ After: run /sq-end to checkpoint, or confirm you want 1 final 25-min Pomodoro.

What do you want to do?
```

### Red (180+ min)

```
🔴 [N] hours. This is the hyperfocus zone.

Long sessions without breaks hurt more than they help:
  • Decision quality drops after 3+ hours
  • Bugs introduced in fatigue cost 3× to fix
  • You're burning tomorrow's energy today

What you've built so far is real. Let's protect it.

**Mandatory checkpoint:**
1. Run /sq-end right now → shutdown note + next action
2. Take 20+ min away from the screen
3. Eat something if you haven't
4. Come back with /sq-start to continue

Shall I run /sq-end for you?
```

### Critical (240+ min)

```
💀 [N] hours without a proper break.

I'm not asking — I'm telling you to stop.

Running shutdown sequence now. You can fight me on this after you've had food and water.
```

Then immediately invoke the session-end skill protocol.

## Step 4: If user wants to continue

If they choose to continue despite Orange/Red alert, negotiate:

1. **Set a Pomodoro contract**: "One 25-min block, then hard stop. Agreed?"
2. **Define the finish line**: "What specifically needs to be done for this to be a win? One sentence."
3. **Log the hyperfocus event** (see Step 5)
4. At the end of that 25-min block, re-invoke this skill automatically.

Do NOT just say "OK" and disappear. Keep the contract visible.

## Step 5: Log the hyperfocus event

Append to `~/.squirrel/state.json` (or a separate hyperfocus log):

```bash
python3 -c "
import json, datetime, pathlib
log = pathlib.Path('~/.squirrel/hyperfocus-log.jsonl').expanduser()
entry = {
    'timestamp': datetime.datetime.now().isoformat(),
    'project': '$PROJECT',
    'intent': '$INTENT',
    'duration_minutes': $DURATION,
    'alert_level': '$LEVEL',
    'outcome': '$OUTCOME'  # continued / break_taken / hard_stop
}
with open(log, 'a') as f:
    f.write(json.dumps(entry) + '\n')
"
```

This log feeds future pattern analysis: which projects trigger hyperfocus, time-of-day patterns,
outcomes.

## Step 6: Post-break reentry

When the user comes back after a hyperfocus break, run a quick re-orientation:

```
🟢 Welcome back. You were working on: [INTENT]

Last concrete output: [from shutdown note]
Your fresh eyes: what's the ONE thing to do next?

(If you're not sure, run /sq-start [PROJECT] to reload full context.)
```

## Special cases

### "Just one more thing" pattern

If the user has said any variant of "just one more", "quick fix", "almost done" 2+ times in
the same session without actually finishing:

```
⚠️ That's the third "just one more." This is a known trap.

The task is probably bigger than it felt at the start. That's OK.
But continuing in this state usually means:
  • More bugs
  • No energy for tomorrow
  • The task still won't be "done"

Better play: log where you are, commit what works, come back tomorrow with a plan.
```

### Weekend/evening sessions

If session_started_at is after 20:00 or on a weekend, lower all thresholds by 30 min
(fatigue accumulates faster in off-hours).

### "Flow state" override

If the user explicitly says "I'm in flow, don't interrupt" → respect it for 30 more minutes,
then check in again. Never disable the guardian entirely for a session.

## Output style

- Direct, not preachy. One intervention, not a lecture.
- Acknowledge the work done — it's real and valuable.
- Offer a concrete out (not "take a break" but "what specifically to do in the break").
- Never shame. Time blindness is neurological, not a character flaw.

## Anti-patterns

- ❌ Don't say "you should take care of yourself" — paternalistic
- ❌ Don't interrupt without acknowledging what they've achieved
- ❌ Don't offer 5 options — offer 1 concrete recommendation
- ❌ Don't disappear after "OK" — hold the contract
- ❌ Don't trigger during the first 89 min of a session
