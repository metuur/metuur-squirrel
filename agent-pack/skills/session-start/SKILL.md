---
name: squirrel-session-start
description: Load context from the local Markdown vault to start a coding session on a specific project. Use this skill when the user runs /sq-start, says "vamos a trabajar en X", "retomemos Y", "abrí el proyecto Z", "what was I doing", or at the beginning of any session when a project tag can be inferred. Reads the most recent shutdown notes, current intents, and produces a structured "loading note" so the user re-enters the project quickly without re-reading 20 files. Accepts an optional `vault_name` argument; when omitted, operates on the default vault (R-7.1, R-7.3).
---

# squirrel:session-start

## Purpose
Solve the ADHD context-switching problem. When the user returns to a project (after hours, days, or weeks), this skill rebuilds the cognitive context FAST by reading the vault's structured notes.

## When to invoke
- Explicit: `/sq-start [PROJECT-TAG]`, "let's work on X", "retomemos Y"
- At hook `SessionStart` if the previous session was bound to a project
- When the user opens a file path that matches a known project's working directory
- When the user says "what was I doing", "¿en qué estaba?", "where did I leave off"

## Workflow

<!-- @spec SESSION-004 -->
### Step 1: Identify the project
Resolution order:
1. Explicit argument: `/sq-start TRABAJO-PROYECTO-A` → use that
2. Recent activity: read `~/.squirrel/state.json` for `last_active_project`
3. Working directory inference: if cwd matches a path declared in any Project Page → use that
4. Ask the user: list WIP projects from config and ask which one

**SESSION-004 guard**: If resolution reaches step 4 (no unambiguous project found), stop immediately. Present the WIP project list and ask the user to pick one. Do NOT produce any loading summary until exactly one project is confirmed. Example prompt:
```
No pude determinar el proyecto activo. ¿Cuál querés retomar?
1. PROYECTO-A
2. PROYECTO-B
3. PROYECTO-C
Respondé con el número o el tag exacto.
```

### Step 1.5: Record context switch (ATTN-002)
Before loading context, record the switch so the ledger stays accurate.

```bash
PREV_PROJECT=$(python3 -c "
import json, pathlib, sys
state = pathlib.Path('~/.squirrel/state.json').expanduser()
if state.exists():
    d = json.loads(state.read_text())
    prev = d.get('last_active_project')
    if prev:
        print(prev)
")
```

If `PREV_PROJECT` is non-empty **and** differs from `<PROJECT-TAG>`:
```bash
python3 lib/switch_tracker.py record \
    --vault "$VAULT" \
    --from "$PREV_PROJECT" \
    --to <PROJECT-TAG> \
    --reason voluntary
```

If this is the first session (no `last_active_project`):
```bash
python3 lib/switch_tracker.py record \
    --vault "$VAULT" \
    --to <PROJECT-TAG> \
    --reason session-start
```

The script appends one JSON line to `vault/.squirrel/switches.jsonl`. On success, capture the returned JSON — it will be used in Step 4 to show the day's focus score.

### Step 2: Load project context (script-driven)

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

If the script exits non-zero, surface the error and stop. Do not proceed without the JSON.

The JSON contains:
- `objective` — 1-line project goal
- `context_dump` — critical context text
- `open_questions` — project-level open questions
- `active_intent` — ID of the most recently active intent
- `next_physical_action` — from the latest shutdown note
- `last_activity` / `days_since_activity`
- `intent_list[]` — each with `id`, `title`, `estado`, `shutdown_notes[]`, `dod_done`, `dod_pending`, `open_questions`, `decisions`
- `alerts[]` — critical/urgent alerts

From `intent_list`, find the entry whose `id` matches `active_intent`. That is your active intent. Pull from it:
- `shutdown_notes[0]` → `state`, `next_action`, `hypothesis`, `open_loops`
- `dod_done` / `dod_pending` — what's done vs. still pending
- `open_questions` — intent-level open questions

### Step 3: Run a quick git sniff (if it's a code project)
If the Project Page declares a `repo_path` or the cwd is a git repo:
```bash
git log --oneline -5
git diff HEAD~1 --stat
git status -sb
git stash list
```
Look for stashes named with the project tag.

<!-- @spec SESSION-001 -->
### Step 4: Generate the loading note
Produce a structured brief, MAX 200 words, 5–7 lines of actual content, with these sections (in this order):

```markdown
## 🔵 Sesión: <PROJECT-TAG>
Última actividad: <date> (<X días/horas atrás>)

### 🎯 Estás haciendo
<from latest intent + shutdown note, 1-2 sentences>

### ✅ Lo último que hiciste
<from latest shutdown note + recent commits, 2-3 bullets>

### 🎬 Próximo paso físico
<the "next physical action" from latest shutdown note>

### 💡 Decisiones clave
<key decisions from latest shutdown note's `decisiones_hoy` field, 1-3 bullets; "Ninguna" if empty>

### 🚧 Bloqueos / preguntas abiertas
<from latest intent's open questions + blockers, if any>

### 🔧 Sugerencia de apertura
1. <very concrete first action — open file X line Y / run command Z>
2. <second concrete action>
3. <third — usually a 25-min pomodoro target>

---
¿Empezamos por 1?
```

### Step 5: Update state
Write to `~/.squirrel/state.json`:
```json
{
  "last_active_project": "<PROJECT-TAG>",
  "session_started_at": "<ISO timestamp>",
  "active_intent": "<INTENT-TAG>"
}
```

This state is used by `session-end` and by future `where-am-i` calls.

### Step 6: Offer one shortcut
After producing the brief, offer a single concrete action the user can confirm with "sí":
- "¿Abro auth.controller.ts línea 47?"
- "¿Corro el último test que dejaste fallando?"
- "¿Muestro el diff completo?"

## Special modes

<!-- @spec SESSION-006 -->
### Same-day re-entry (SESSION-006 idempotency)
Before generating a new loading note, check `~/.squirrel/state.json` for `session_started_at`:
- Extract the date portion (YYYY-MM-DD) and compare to today's date
- If the dates match AND `last_active_project` equals the requested project AND no new shutdown note exists since `session_started_at`:
  - **Re-use the same loading note**: re-read the same shutdown note the previous call used (same `active_intent`, same `shutdown_notes[0]`) and produce an identical summary
  - Do NOT generate a fresh/different summary
  - Optionally note: "_(sesión ya iniciada hoy — mostrando el mismo contexto de entrada)_"
- This makes `/sq-start PROYECTO` idempotent: calling it twice on the same day with the same state returns the same output

### Multi-day gap (>3 days since last activity)
- Add a "📅 Han pasado X días desde la última sesión" header
- Be MORE explicit about reloading context (mention 2-3 lines extra from context_dump)
- Suggest redrawing the architecture in the user's physical notebook

### First session ever for a project
- If the JSON has `shutdown_notes: []` on all intents and `active_intent: null`, this is a first session
- Frame the brief as "primer setup" using `objective` + `intent_list` from the JSON
- Suggest creating the first intent

### Project in PARKING-LOT
- Refuse politely: "Este proyecto está en Parking Lot. Para reactivarlo necesitás:
  (1) mover a `01-Proyectos-Activos/`, (2) confirmar que WIP < 3, (3) explicitar deadline."

### Foyer Family special case (Finishing Tax)
If the project is `SIDEPROJECT-FOYER-FAMILY` and its frontmatter has `prioridad: finishing-tax`, add to the brief:
```
⚠️ FINISHING TAX: Este proyecto está al 90% y llevás <N> semanas sin lanzarlo.
   Compromiso: no empezás otro side project hasta cerrar este.
   Si querés ver la idea nueva que dejaste esperando: ver [[02-Parking-Lot/SIDEPROJECT-NUEVA-IDEA]]
```

## Output style
- Crisp, action-oriented, NO motivational fluff
- Use the user's preferred language (Spanish by default for this user)
- If you have to make inferences (which intent is active), state them briefly
- ALWAYS end with one concrete proposed first action

## Anti-patterns
- ❌ Don't dump the whole Project Page on the user
- ❌ Don't make the brief longer than 200 words
- ❌ Don't ask the user to choose between 5 things — propose 1 and let them adjust
- ❌ Don't start without reading the actual files (no hallucinating intent states)
