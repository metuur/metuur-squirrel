---
name: squirrel-decision
description: Capture an architectural or design decision as a lightweight ADR (Architecture Decision Record) in the Markdown vault. Use when the user says "I decided X", "let's use Y", "I chose Z because", "let's go with X over Y", "we concluded that", or detects decisional language during a design discussion. Decisions are first-class citizens with their own tag and structure separate from regular intents. Accepts an optional `vault_name` argument; when omitted, writes to the default vault (R-7.1, R-7.3).
---

# squirrel:decision

## Purpose
Decisions get lost in chat logs. Capture them explicitly with their context, alternatives considered, and consequences — so future-self and stakeholders can understand WHY a path was taken.

## When to invoke

### Explicit triggers
- `/sq-decision`
- "I decided X"
- "let's use X instead of Y"
- "I chose X because..."
- "let's go with X"
- "we concluded that..."

### Implicit triggers (be proactive — OFFER to capture)
- Conversation pattern: "I'm between A or B" → discussion → "I'll go with A"
- User declares a tool/library/pattern choice
- User says "we're not going to do X because..."
- Trade-off is articulated ("A is faster but B is simpler")

When triggered implicitly, ASK first:
> "I detected a decision: <decision summary>. Should I capture it as an ADR?
>  Suggested tag: <PROJECT>-DECISION-<NNN>."

## Workflow

### Step 1: Determine the project context
- Read `state.json` for active project
- Or ask user

### Step 2: Generate the tag
Pattern: `<PROJECT-PREFIX>-DECISION-<NNN>`

Find next NNN by listing existing decision notes:
```bash
ls "<vault>/01-Active-Projects/<PROJECT>/" | grep -E "^${PROJECT_PREFIX}-DECISION-[0-9]+\.md$"
```

### Step 3: Extract decision components
Mine the conversation for these elements. ASK if any are missing:

| Field | What to capture |
|---|---|
| **Title** | One-line summary: "Use Redis for session storage" |
| **Status** | proposed / accepted / superseded / deprecated |
| **Context** | What's the problem? What constraints? What forced this decision? |
| **Decision** | What was chosen. Be explicit. |
| **Alternatives considered** | What else was on the table, and why rejected |
| **Consequences** | Both positive AND negative. What does this commit us to? |
| **Stakeholders** | Who was involved or needs to know |

<!-- @spec CAPTURE-002 -->
### Step 4: Draft the ADR

Template (based on Michael Nygard's ADR format, simplified):

```markdown
---
id: <DECISION-TAG>
project: <PROJECT>
type: decision
status: accepted
created: <YYYY-MM-DD>
reviewed: <YYYY-MM-DD>
tags: [decision, project/<PROJECT>, area/<AREA>]
stakeholders: [<list>]
---

# <DECISION-TAG> — <One-line title>

## 📌 Status
<proposed | accepted | superseded by <TAG> | deprecated>

## 🎯 Decision
<The actual choice in 1-2 sentences. Be definitive.>

## 🌐 Context
<Why are we deciding this? What's the situation? What constraints?>
<Include relevant background: project stage, deadlines, team composition, etc.>

## 🤔 Alternatives considered

### Option A: <name>
- ✅ Pros: ...
- ❌ Cons: ...
- ⚖️ Verdict: <why considered, why rejected (if rejected)>

### Option B: <name>
- ✅ Pros: ...
- ❌ Cons: ...
- ⚖️ Verdict: ...

### Option C: <name> ← CHOSEN
- ✅ Pros: ...
- ❌ Cons: ...
- ⚖️ Verdict: ...

## 📊 Consequences

### Positive
- <consequence>
- <consequence>

### Negative / costs
- <consequence>
- <consequence>

### Future commitments
- <what this locks us into>
- <what this makes harder>

## 🔗 Related
- Parent project: [[<PROJECT>]]
- Affected intents: [[<INTENT-TAG>]], [[<INTENT-TAG>]]
- Related decision: [[<DECISION-TAG>]] (if applicable)

## 📚 References
- <link, paper, blog post that informed this>
- <internal doc>

## 🗒️ Discussion notes
<Raw notes from the conversation that led to this. Useful for future context.>
```

### Step 5: Show draft for confirmation
Present the draft. Allow the user to:
- Confirm as-is
- Edit any field inline
- Cancel

### Step 6: Write to vault
Path: `<vault>/01-Active-Projects/<PROJECT>/<DECISION-TAG>.md`

### Step 7: Link from Project Page
Add to the Project Page under a `## 🧠 Decisions` section (create if missing):

```markdown
## 🧠 Decisions

- [[<DECISION-TAG>]] <Title> (<status>, <date>)
- ...
```

### Step 8: Notify stakeholders (suggest)
If the decision has stakeholders, offer:
> "This decision affects <stakeholder>. Would you like me to generate an email/Slack draft to notify them?"

If yes, generate using the brief skill in "communication mode".

## Special cases

### Decision supersedes a previous one
- Mark previous decision as `status: superseded`
- Update its frontmatter with `superseded_by: <NEW-TAG>`
- Add a `superseded_by` note in the previous ADR's title

### Decision is uncertain ("we'll try this")
- Use `status: proposed`
- Add a "revisit by" date in frontmatter: `revisit_by: <YYYY-MM-DD>`
- Create a calendar reminder (suggest)

### Tactical vs strategic decision
- Tactical (e.g., "use this library for utils") → light ADR, skip some sections
- Strategic (e.g., "monorepo vs polyrepo") → full ADR, get more context

If unsure, ASK: "Is this a tactical or strategic decision?"

### Personal-life decision (not code)
- Same skill works for personal projects
- Examples: "we decided to handle the visas with lawyer X", "we're going to travel in September"
- Use the same structure — context, alternatives, consequences

## Anti-patterns
- ❌ Don't capture trivial choices (variable names, file locations) as ADRs
- ❌ Don't fabricate alternatives that weren't actually considered
- ❌ Don't end with "status: proposed" indefinitely — push for resolution
- ❌ Don't put decisions outside the project folder — they're project-scoped
- ❌ Don't write more than ~500 words for a decision — it's a record, not an essay

## Output style
- Crisp and structured
- The ADR is the deliverable; surrounding chat is minimal
- Confirm before writing; suggest after writing

## References

- Nygard, M. (2011): Architecture Decision Records — lightweight immutable decision log pattern
- Klein, G. (1998): Naturalistic Decision Making — decisions made under time pressure need abbreviated rationale capture, not full analysis
- Tufte, E. (2001): decision context decays rapidly — record the constraint, not just the choice
