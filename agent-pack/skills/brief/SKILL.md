---
name: squirrel-brief
description: Produce a structured 6-section brief of the current state of a project for stakeholders or for the user to review. Use when the user asks "dame el brief", "qué estoy haciendo", "resumí el proyecto", "status update", "necesito un resumen para el lead", "what's the status of X", or before any communication round. Outputs Markdown ready to copy-paste into email, Slack, or stand-up. The 6 sections are NOW, DONE, NEXT, DECISIONS, STEPS, CONTEXT. Accepts an optional `vault_name` argument; when omitted, operates on the default vault (R-7.1, R-7.3).
---

# squirrel:brief

## Purpose
Generate a clear, structured status of a project that the user can:
- Read themselves to remember where they are
- Send to a stakeholder (lead, PM, client)
- Use as a session-start summary
- Include in a sync-out package

## When to invoke
- Explicit: `/sq-brief [PROJECT-TAG]`, "give me a brief", "dame el resumen"
- Before user communicates with stakeholders (detect "le voy a mandar update a X")
- Weekly review prep
- When user is overwhelmed and needs to re-anchor

## Workflow

### Step 1: Determine scope
Resolution:
1. Explicit project tag in argument
2. `active_intent.project` from state
3. Ask: "¿Brief de qué proyecto?" with WIP list

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
- **Done intents list**: `intent_list[]` where `estado` is `done` or `completado`
- **In-progress list**: `intent_list[]` where `estado` is `in-progress` / `wip`
- **Decisions**: from each intent's `decisions` field (non-empty entries)
- **Context**: `context_dump` + `open_questions`
- **Stakeholders / deadline / tipo**: top-level project fields

### Step 4: Produce the 6-section brief

Use this EXACT structure (the user explicitly asked for these 6 sections):

```markdown
# 📊 Brief: <PROJECT-TAG>

**Tipo**: <A|B|C>  •  **Deadline**: <date>  •  **Avance**: <X%>
**Última actividad**: <date> (<N días atrás>)
**Stakeholders**: <list>

---

## 🎯 1. Lo que estoy haciendo (NOW)

<2-3 lines max. The current active intent + the immediate next action.>
<Be specific: not "working on auth" but "implementing CSRF state validation in auth.controller.ts">

**Intent activo**: `<INTENT-TAG>`
**Next physical action**: <from latest shutdown note>

---

## ✅ 2. Lo que ya hice (DONE)

<List of completed intents and major milestones, most recent first. Up to 7 items.>

- [x] `<INTENT-TAG>` <one-line description> (completado <date>)
- [x] `<INTENT-TAG>` <one-line description>
- ...

<Si hay más, agregar "...y N más">

---

## 🎬 3. Lo que falta (NEXT)

<List of pending and in-progress intents, grouped by status.>

### En progreso
- 🔵 `<INTENT-TAG>` <description> — <next action>

### Próximos
- ⏳ `<INTENT-TAG>` <description>
- ⏳ `<INTENT-TAG>` <description>

### Backlog (post-deadline)
- 📋 `<INTENT-TAG>` <description>

---

## 🧠 4. Decisiones tomadas (DECISIONS)

<Pull from each intent's `decisions` field in the JSON. Most relevant 3-5, most recent first.>

- **<Date>**: <Decision in one line>. Justificación: <one-line rationale>.
- **<Date>**: <Decision>. Justificación: <rationale>.

---

## 🚦 5. Próximos pasos (STEPS)

<The 3-5 concrete things that will happen next in chronological order.>

1. <Concrete action with intent tag>
2. <Concrete action>
3. <Concrete action>

**ETA realista**: <date>

---

## 🌐 6. Contexto importante (CONTEXT)

<Critical context for anyone (including future-self) to understand the state.>
<Pull from `context_dump` and `open_questions` JSON fields.>

### Open questions
- ❓ <question>
- ❓ <question>

### Blockers
- 🚧 <blocker> — waiting on <person/event>

### Decisiones pendientes
- ⚖️ <decision needed> — <when>

### Detalles que importan
<2-3 lines of critical context from the project notes>

---

*Brief generado: <ISO timestamp>*
*Generado por: squirrel:brief*
```

### Step 5: Adapt to context
The brief above is the DEFAULT format. Adapt based on who it's for:

#### For a Slack stand-up (very short)
Compress to:
```
**<PROJECT-TAG>** [<date>]
- Ayer: <done>
- Hoy: <now>
- Bloqueos: <blockers or "none">
```

#### For email to lead (medium)
Keep sections 1-3 + 6. Skip detailed decisions list. Add salutation.

#### For weekly review (full)
Full 6 sections.

#### For sync-out package
Full 6 sections + paquete header.

ASK the user: "¿Brief completo o versión corta (email/slack)?"

### Step 6: Offer to send
After generating:
```
¿Querés que:
  a) Lo abra como draft de email para <stakeholder>
  b) Lo copie al clipboard
  c) Genere paquete sync-out (si vas a llevarlo a otro entorno)
```

## Special cases

### Project has no intents yet
- Brief is very thin
- Suggest creating initial intents via `/sq-capture`
- Don't fake content

### Project has intents but no shutdown notes
- Means the user hasn't been using session-end
- Soft nudge: "Veo que no hay shutdown notes. Si querés un brief más rico, considera correr /sq-end al cerrar sesiones futuras."

### Brief across multiple projects (e.g., for weekly review)
- If user asks `/sq-brief --all` or "brief de todos mis proyectos"
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
