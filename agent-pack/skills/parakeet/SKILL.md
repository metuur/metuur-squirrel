---
name: squirrel-parakeet
description: Deadline reminder with tone calibrated to urgency level. Use when the user runs /sq-parakeet, at the start of any session (embedded in session-start), when the user asks "qué tengo pendiente", "what's due", "any deadlines?", "cuándo es lo de X", or after sq-status returns items with critical/urgent deadlines. Also triggers automatically when any loaded project has a deadline within 24 hours. Accepts an optional `vault_name` argument; when omitted, operates on the default vault (R-7.1, R-7.3).
metadata:
  category: proactive-reminders
  pairs-with: [squirrel-session-start, squirrel-where-am-i, squirrel-brief]
  engine: deadline_scanner.py
---

# squirrel:parakeet

## Purpose

ADHD brains don't feel time passing — deadlines arrive as surprises. Parakeet is the friendly
but persistent voice that keeps deadlines visible without shame, escalating tone only when
urgency truly warrants it.

The key insight from research: most ADHD deadline failures aren't from not caring but from
**time blindness** (Barkley 2015). A well-timed, well-toned reminder can bridge that gap.
A nagging one creates anxiety and avoidance.

## Urgency levels and tones

| Level | When | Tone | Frequency |
|-------|------|------|-----------|
| `distant` | > 30 days | Background awareness | Monthly |
| `eventual` | 8–30 days | Casual info drop | Weekly |
| `upcoming` | 4–7 days | Gentle heads-up | Every 2–3 days |
| `soon` | 2–3 days | "Hey, this is coming" | Daily |
| `urgent` | Today (≥4 h) or tomorrow | Clear and direct | Every session |
| `critical` | Today (<4 h left) or past deadline | Serious / non-judgmental | Immediately / every session |

**Note**: overdue items (`is_overdue=true`) are classified as `critical`. Detect them via `item.is_overdue == true` and apply the non-judgmental overdue tone instead of the "< 4 hours" tone.

## Workflow

### Step 1: Run deadline scanner

Resolve the vault via `config_loader` so the optional `vault_name` argument
routes to the right vault (default if omitted — R-7.3):

```bash
VAULT_PATH=$(python3 -c "
import sys, pathlib
for c in [pathlib.Path('~/.claude/plugins/squirrel/lib').expanduser()] + list(pathlib.Path.home().glob('others/*/squirrel/lib')) + list(pathlib.Path.home().glob('others/*/*/squirrel/lib')):
    if c.exists(): sys.path.insert(0, str(c)); break
from config_loader import get_vault, ConfigError
try:
    name = '$vault_name' if '$vault_name' else None
    print(get_vault(name=name).path)
except ConfigError as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)
" 2>&1)
[ $? -ne 0 ] && echo "⚠️  $VAULT_PATH" >&2 && exit 0   # parakeet never blocks a session

SCRIPT=$(find "${HOME}/.claude/plugins/squirrel/lib" "${HOME}/others" \
    -name 'deadline_scanner.py' -path '*/squirrel/*' 2>/dev/null | head -1)

DEADLINES_JSON=$(python3 "$SCRIPT" --vault "$VAULT_PATH" --pretty 2>&1)
```

If the script fails or vault_path is missing, skip silently — parakeet should never block a session.

### Step 2: Evaluate — is there anything worth mentioning?

Apply the frequency filter:
- `distant`: skip unless standalone `/sq-parakeet` call
- `eventual`: only mention if standalone `/sq-parakeet` call (not embedded in other skills)
- `upcoming`: mention in session-start if not shown in last 2 days
- `soon`, `urgent`, `critical`: always mention (includes overdue items in `critical`)

If the result is empty at all levels: respond with "✅ No deadlines in the next 30 days." and stop.

### Step 3: Compose message by level

Generate a separate block for each non-empty level, most urgent first.

---

#### `critical` — Two sub-tones based on `is_overdue`

**For overdue items** (`item.is_overdue == true`) — Non-judgmental:
```
📋 Critical — overdue (X items):

  • [INTENT-TAG] — [title] — was due [date] ([days_overdue] days ago)
    Project: [PROJECT]
    Next action: [next_action if available]

These slipped past. That happens. What matters now:
→ Is this still relevant? [yes/no/update deadline]
→ If yes: block 30 min today to advance it or get clarity.
```
Never say "you missed", "you forgot", "late". Use passive voice or redirect to action.

**For imminent items** (`hours_left` present, no `is_overdue`) — Serious and clear:
```
🔴 Critical — due in < 4 hours:

  • [INTENT-TAG] — [title] — today by [time]
    → [next_action]

This is happening today. Is this on your radar?
If not: 15 min NOW to define "good enough done" and start.
```

#### `urgent` — Direct

```
🟠 Urgent — due today:

  • [INTENT-TAG] — [title] — deadline: [date]
    Project: [PROJECT]
    Last action: [next_action or "not specified"]

This one is today. Is it started?
```

#### `soon` — Friendly nudge

```
🟡 Coming up (1–3 days):

  • [INTENT-TAG] — [title] — [date] ([N] days left)

Heads up: worth 10 min today to make sure you know the next physical action.
```

#### `upcoming` — Casual

```
🔵 On the radar (3–7 days):

  • [INTENT-TAG] — deadline [date]
  • [INTENT-TAG] — deadline [date]

Nothing urgent, just keeping these visible.
```

#### `eventual` — Information only

Only show when invoked directly as `/sq-parakeet`. In embedded contexts (session-start, status), skip this level.

```
🟢 Further out (8–30 days):
  • [INTENT-TAG] — [date]
```

#### `distant` — Background awareness

Only show when invoked directly as `/sq-parakeet`. One-line, no narrative.

```
⚪ Distant (> 30 days):
  • [INTENT-TAG] — [date]
```

### Step 4: Suggest one action (if critical or urgent items exist)

After the deadline blocks, add a single concrete recommendation:

```
→ Suggested next: start [MOST-CRITICAL-TAG] — [1-sentence reason why this one]
```

Don't offer 5 options. One clear call to action.

### Step 5: Embedded mode behavior

When parakeet runs embedded inside another skill (session-start, where-am-i, status):

1. **Only show urgent/critical** — skip upcoming, eventual, and distant
2. **Compact format** — one line per item, no narrative
3. **Don't interrupt flow** — insert as a brief section, not as the main content
4. **Max 5 items total** — truncate with "(+N more, run /sq-parakeet for full list)"

Compact format:
```
⏰ Deadlines:
  🔴 [TAG] — [title] — TODAY
  🟠 [TAG] — [title] — tomorrow
```

## Special behaviors

### "I know, I know" pattern
If the user dismisses a deadline ("sí, ya sé", "I'll deal with it later"):
- Acknowledge: "Noted. I'll mention it again next session if it's still open."
- Don't argue or repeat immediately
- Log the dismissal mentally (don't literally write to a file)

### Multiple deadlines same day
If 3+ deadlines on the same day: group them and ask the user to triage:
```
🟠 Three things due today:
  • [TAG1], [TAG2], [TAG3]

You probably can't do all three. Which one actually matters most today?
```

### Deadline just passed (< 12 hours overdue)
Treat as urgent/critical, not as fully overdue. Tone: "This just tipped over — is it recoverable today?"

## Output constraints

- Max 8 deadline items total before truncation
- Never mention the same deadline twice in the same session (track in conversation context)
- If ADHD-specific framing doesn't fit culturally for the user, default to neutral factual tone
- Always end overdue/critical blocks with one concrete action option

## Anti-patterns

- ❌ Don't use "you missed", "you forgot", "late", "behind"
- ❌ Don't show ALL deadlines on every status check (eventual/distant noise creates habituation)
- ❌ Don't list deadlines without a suggested next action for critical/urgent
- ❌ Don't invoke parakeet standalone more than once per session (monotony kills effectiveness)
- ❌ Don't shame around overdue items (in `critical`) — they happened, now what?
- ❌ **VAULT-007**: Do NOT write, edit, or create any file inside the vault. This skill is a read-only consumer. All vault writes belong to `capture`, `session`, or `sync` segments only.

## References

- Barkley, R.A. (2015): time blindness as core ADHD deficit, not motivation failure
- Hallowell & Ratey (2021): deadline proximity as primary ADHD motivational trigger
- Mark et al. (2008): reminder fatigue when alerts fire too frequently
