---
name: squirrel-brief
description: Produce a structured 6-section brief of the current state of a project for stakeholders or for the user to review. Use when the user asks "give me the brief", "what am I doing", "summarize the project", "status update", "I need a summary for the lead", "what's the status of X", or before any communication round. Outputs Markdown ready to copy-paste into email, Slack, or stand-up. The 6 sections are NOW, DONE, NEXT, DECISIONS, STEPS, CONTEXT. Accepts an optional `vault_name` argument; when omitted, operates on the default vault (R-7.1, R-7.3).
---

# squirrel:brief

## Purpose
Generate a clear, structured status of a project that the user can:
- Read themselves to remember where they are
- Send to a stakeholder (lead, PM, client)
- Use as a session-start summary
- Include in a sync-out package

## When to invoke
- Explicit: `/sq-brief [PROJECT-TAG]`, "give me a brief", "give me the summary"
- Before user communicates with stakeholders (detect "I'm going to send an update to X")
- Weekly review prep
- When user is overwhelmed and needs to re-anchor

## Workflow

### Step 1: Determine scope
Resolution:
1. Explicit project tag in argument
2. `active_intent.project` from state
3. Ask: "Brief of which project?" with WIP list

### Step 2: Load project data (script-driven)

Resolve the vault via `config_loader` so the optional `vault_name` argument
routes to the right vault (default if omitted — R-7.3). Then shell out once
to get all the data needed — no manual file reading:

```bash
VAULT=$(python3 -c "
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
[ $? -ne 0 ] && echo "❌ $VAULT" >&2 && exit 1
python3 lib/status_aggregator.py --vault "$VAULT" --project <PROJECT-TAG> --detailed
```

If the script exits non-zero, surface the error and stop.

### Step 3: Derive state from JSON
The JSON already aggregates everything. Read directly from it:

- **Total/done/in-progress/pending/blocked intents**: from `intents.total`, `intents.done`, etc.
- **Most recent activity**: `last_activity` + `days_since_activity`
- **Active intent + next action**: `active_intent` + `next_physical_action`
- **Done intents list**: `intent_list[]` where `status` is `done` or `completed`
- **In-progress list**: `intent_list[]` where `status` is `in-progress` / `wip`
- **Decisions**: from each intent's `decisions` field (non-empty entries)
- **Context**: `context_dump` + `open_questions`
- **Stakeholders / deadline / type**: top-level project fields

### Step 4: Produce the 6-section brief

Use this EXACT structure (the user explicitly asked for these 6 sections):

```markdown
# 📊 Brief: <PROJECT-TAG>

**Type**: <A|B|C>  •  **Deadline**: <date>  •  **Progress**: <X%>
**Last activity**: <date> (<N days ago>)
**Stakeholders**: <list>

---

## 🎯 1. What I'm doing (NOW)

<2-3 lines max. The current active intent + the immediate next action.>
<Be specific: not "working on auth" but "implementing CSRF state validation in auth.controller.ts">

**Active intent**: `<INTENT-TAG>`
**Next physical action**: <from latest shutdown note>

---

## ✅ 2. What I've done (DONE)

<List of completed intents and major milestones, most recent first. Up to 7 items.>

- [x] `<INTENT-TAG>` <one-line description> (completed <date>)
- [x] `<INTENT-TAG>` <one-line description>
- ...

<If there are more, add "...and N more">

---

## 🎬 3. What's left (NEXT)

<List of pending and in-progress intents, grouped by status.>

### In progress
- 🔵 `<INTENT-TAG>` <description> — <next action>

### Upcoming
- ⏳ `<INTENT-TAG>` <description>
- ⏳ `<INTENT-TAG>` <description>

### Backlog (post-deadline)
- 📋 `<INTENT-TAG>` <description>

---

## 🧠 4. Decisions made (DECISIONS)

<Pull from each intent's `decisions` field in the JSON. Most relevant 3-5, most recent first.>

- **<Date>**: <Decision in one line>. Rationale: <one-line rationale>.
- **<Date>**: <Decision>. Rationale: <rationale>.

---

## 🚦 5. Next steps (STEPS)

<The 3-5 concrete things that will happen next in chronological order.>

1. <Concrete action with intent tag>
2. <Concrete action>
3. <Concrete action>

**Realistic ETA**: <date>

---

## 🌐 6. Important context (CONTEXT)

<Critical context for anyone (including future-self) to understand the state.>
<Pull from `context_dump` and `open_questions` JSON fields.>

### Open questions
- ❓ <question>
- ❓ <question>

### Blockers
- 🚧 <blocker> — waiting on <person/event>

### Pending decisions
- ⚖️ <decision needed> — <when>

### Details that matter
<2-3 lines of critical context from the project notes>

---

*Brief generated: <ISO timestamp>*
*Generated by: squirrel:brief*
```

### Step 5: Adapt to context
The brief above is the DEFAULT format. Adapt based on who it's for:

#### For a Slack stand-up (very short)
Compress to:
```
**<PROJECT-TAG>** [<date>]
- Yesterday: <done>
- Today: <now>
- Blockers: <blockers or "none">
```

#### For email to lead (medium)
Keep sections 1-3 + 6. Skip detailed decisions list. Add salutation.

#### For weekly review (full)
Full 6 sections.

#### For sync-out package
Full 6 sections + package header.

ASK the user: "Full brief or short version (email/slack)?"

### Step 6: Offer to send
After generating:
```
Would you like me to:
  a) Open it as an email draft for <stakeholder>
  b) Copy it to the clipboard
  c) Generate a sync-out package (if you're taking it to another environment)
```

## Special cases

### Project has no intents yet
- Brief is very thin
- Suggest creating initial intents via `/sq-capture`
- Don't fake content

### Project has intents but no shutdown notes
- Means the user hasn't been using session-end
- Soft nudge: "I see there are no shutdown notes. If you want a richer brief, consider running /sq-end when closing future sessions."

### Brief across multiple projects (e.g., for weekly review)
- If user asks `/sq-brief --all` or "brief of all my projects"
- Generate ONE brief per WIP project, sequential
- Add a top-level summary table

## Token budget

Brief output MUST stay within 800 tokens. When output would exceed this limit:
- Truncate each section to its 3 most recent/important items.
- Append `[truncated: N items]` immediately after the last shown item in that section (where N is the number of omitted items).
- Apply truncation per-section, not globally — never silently drop whole sections.

## Anti-patterns
- ❌ Don't invent decisions or steps that aren't in the notes
- ❌ Don't include intents from projects other than the scoped one
- ❌ Don't write more than ~400 words total (hard cap: 800 tokens)
- ❌ Don't end without offering next action (send / copy / sync-out)
- ❌ Don't write to the vault during brief operations — brief is strictly read-only
- ❌ Don't silently drop items — use `[truncated: N items]` marker when sections exceed 3 items under the token budget
