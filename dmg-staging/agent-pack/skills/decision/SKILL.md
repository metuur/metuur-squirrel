---
name: squirrel-decision
description: Capture an architectural or design decision as a lightweight ADR (Architecture Decision Record) in the Markdown vault. Use when the user says "decidí X", "vamos a usar Y", "elegí Z porque", "let's go with X over Y", "concluimos que", or detects decisional language during a design discussion. Decisions are first-class citizens with their own tag and structure separate from regular intents. Accepts an optional `vault_name` argument; when omitted, writes to the default vault (R-7.1, R-7.3).
---

# squirrel:decision

## Purpose
Decisions get lost in chat logs. Capture them explicitly with their context, alternatives considered, and consequences — so future-self and stakeholders can understand WHY a path was taken.

## When to invoke

### Explicit triggers
- `/sq-decision`
- "decidí X"
- "vamos a usar X en lugar de Y"
- "elegí X porque..."
- "let's go with X"
- "concluimos que..."

### Implicit triggers (be proactive — OFFER to capture)
- Conversation pattern: "estoy entre A o B" → discussion → "voy con A"
- User declares a tool/library/pattern choice
- User says "no vamos a hacer X porque..."
- Trade-off is articulated ("A es más rápido pero B es más simple")

When triggered implicitly, ASK first:
> "Detecté una decisión: <decision summary>. ¿La capturo como ADR?
>  Tag sugerido: <PROJECT>-DECISION-<NNN>."

## Workflow

### Step 1: Determine the project context
- Read `state.json` for active project
- Or ask user

### Step 2: Generate the tag
Pattern: `<PROJECT-PREFIX>-DECISION-<NNN>`

Find next NNN by listing existing decision notes:
```bash
ls "<vault>/01-Proyectos-Activos/<PROJECT>/" | grep -E "^${PROJECT_PREFIX}-DECISION-[0-9]+\.md$"
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
proyecto: <PROJECT>
tipo: decision
estado: accepted
creado: <YYYY-MM-DD>
revisado: <YYYY-MM-DD>
tags: [decision, proyecto/<PROJECT>, area/<AREA>]
stakeholders: [<list>]
---

# <DECISION-TAG> — <One-line title>

## 📌 Estado
<proposed | accepted | superseded by <TAG> | deprecated>

## 🎯 Decisión
<The actual choice in 1-2 sentences. Be definitive.>

## 🌐 Contexto
<Why are we deciding this? What's the situation? What constraints?>
<Include relevant background: project stage, deadlines, team composition, etc.>

## 🤔 Alternativas consideradas

### Opción A: <name>
- ✅ Pros: ...
- ❌ Cons: ...
- ⚖️ Veredicto: <why considered, why rejected (if rejected)>

### Opción B: <name>
- ✅ Pros: ...
- ❌ Cons: ...
- ⚖️ Veredicto: ...

### Opción C: <name> ← ELEGIDA
- ✅ Pros: ...
- ❌ Cons: ...
- ⚖️ Veredicto: ...

## 📊 Consecuencias

### Positivas
- <consequence>
- <consequence>

### Negativas / costos
- <consequence>
- <consequence>

### Compromisos a futuro
- <what this locks us into>
- <what this makes harder>

## 🔗 Relacionados
- Parent project: [[<PROJECT>]]
- Intents afectados: [[<INTENT-TAG>]], [[<INTENT-TAG>]]
- Decisión relacionada: [[<DECISION-TAG>]] (si aplica)

## 📚 Referencias
- <link, paper, blog post that informed this>
- <internal doc>

## 🗒️ Notas de discusión
<Raw notes from the conversation that led to this. Useful for future context.>
```

### Step 5: Show draft for confirmation
Present the draft. Allow the user to:
- Confirm as-is
- Edit any field inline
- Cancel

### Step 6: Write to vault
Path: `<vault>/01-Proyectos-Activos/<PROJECT>/<DECISION-TAG>.md`

### Step 7: Link from Project Page
Add to the Project Page under a `## 🧠 Decisiones` section (create if missing):

```markdown
## 🧠 Decisiones

- [[<DECISION-TAG>]] <Title> (<status>, <date>)
- ...
```

### Step 8: Notify stakeholders (suggest)
If the decision has stakeholders, offer:
> "Esta decisión afecta a <stakeholder>. ¿Querés que genere un email/Slack draft para notificarles?"

If yes, generate using the brief skill in "communication mode".

## Special cases

### Decision supersedes a previous one
- Mark previous decision as `estado: superseded`
- Update its frontmatter with `superseded_by: <NEW-TAG>`
- Add a `superseded_by` note in the previous ADR's title

### Decision is uncertain ("we'll try this")
- Use `estado: proposed`
- Add a "revisit by" date in frontmatter: `revisar_en: <YYYY-MM-DD>`
- Create a calendar reminder (suggest)

### Tactical vs strategic decision
- Tactical (e.g., "use this library for utils") → light ADR, skip some sections
- Strategic (e.g., "monorepo vs polyrepo") → full ADR, get more context

If unsure, ASK: "¿Esta es una decisión táctica o estratégica?"

### Personal-life decision (not code)
- Same skill works for personal projects
- Examples: "decidimos hacer las visas con el abogado X", "vamos a viajar en septiembre"
- Use the same structure — context, alternatives, consequences

## Anti-patterns
- ❌ Don't capture trivial choices (variable names, file locations) as ADRs
- ❌ Don't fabricate alternatives that weren't actually considered
- ❌ Don't end with "estado: proposed" indefinitely — push for resolution
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
