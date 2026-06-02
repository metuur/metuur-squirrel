---
name: squirrel-task-initiation
description: Break through task-start paralysis. Use when the user says "no puedo arrancar", "can't start", "I'm stuck", "no sé por dónde empezar", "estoy bloqueado", "I keep avoiding this", "everytime I try to start I...", "I don't know where to begin", "this feels overwhelming", "just can't make myself do it", or has been stalling on the same intent across multiple sessions without progress. Accepts an optional `vault_name` argument; when omitted, reads from the default vault (R-7.1, R-7.3).
metadata:
  category: executive-function-support
  pairs-with: [squirrel-chunk-intent, squirrel-hyperfocus-guardian, squirrel-session-start]
  triggers: [stalling-detection, explicit-invoke]
---

# squirrel:task-initiation

## Purpose

Task initiation is one of the most debilitating executive function deficits. The **Wall
of Awful** (Mahan 2017) — the accumulated emotional weight around a task — can make starting
feel physically impossible even when the user knows exactly what to do.

This skill does NOT lecture about why starting is hard. It removes friction from the first
30 seconds.

## When to invoke

**Explicit:**
- `/task-initiation [INTENT-TAG]`
- User says any variant of "stuck", "can't start", "avoiding", "paralyzed"

**Implicit (detect and offer):**
- User mentions the same intent 2+ sessions in a row without any progress logged
- User says "I should work on X but..." (the "but" signals avoidance)
- In session-start: the recommended intent has 0 progress after 2+ sessions open

**Do NOT invoke** if the user is already in flow, just asking a technical question, or
explicitly says they want to keep working.

## Step 1: Identify the task

If the user mentioned a specific intent tag, use that. Otherwise:

```bash
cat ~/.squirrel/state.json 2>/dev/null
```

Read `active_intent` or `last_active_project`. If neither is set, ask:
"¿Cuál es el task que no podés arrancar? (dame el tag o descríbelo)"

## Step 2: Read the intent (if it exists in the vault)

Open the intent file and extract:
- Title
- Definition of Done (what "done" looks like)
- Last shutdown note (what was the last known state)
- Size estimate (if any)

If the intent doesn't exist in the vault, skip this step and work from what the user described.

## Step 3: Diagnose the blocker type

Present these options quickly (don't make the user analyze themselves):

```
Antes de arrancar: ¿cuál describe mejor lo que está pasando?

  A) No sé exactamente qué hacer primero
  B) Sé qué hacer pero no puedo hacer click/abrir el archivo
  C) La tarea parece enorme y no sé si voy a terminarla
  D) Tengo miedo de que salga mal / de que me juzguen
  E) Otro (descríbelo)
```

Route to the appropriate protocol based on the answer. If they don't answer or say "all of
them", apply Protocol 1 (smallest action) — it works for all cases.

## Protocol 1: Smallest Possible Action (for A, B, all-of-the-above)

The goal: get the body moving. Override the executive function barrier with a micro-commitment.

```
OK. No "work on X". Instead:

→ Open [specific file / URL / tool] right now.
   Just open it. That's the entire task.

You're not starting the project. You're just opening a file.

[After they confirm] What do you see? Tell me one line.
```

File/tool to open should be **maximally specific**:
- ❌ "open the project" 
- ✅ "open auth.controller.ts"
- ❌ "start working on the API"
- ✅ "open Postman and look at the /auth/login endpoint"

The specificity is what makes the action feel manageable. Generate it from:
1. Last shutdown note's "next physical action" (most specific)
2. First task checkbox in the intent
3. If nothing found: ask "¿qué archivo o herramienta usarías si supieras exactamente qué hacer?"

## Protocol 2: 2-Minute Start (for B — body won't cooperate)

For when they know what to do but can't make themselves do it:

```
⏱️ 2-Minute Start

Here's the deal: you only have to do this for 2 minutes. Literally.
Set a timer for 2 minutes. When it goes off, you're allowed to stop.

Your 2-minute task:
→ [ONE SPECIFIC ACTION — open file / run command / write first line]

Timer set?
```

Research basis: task initiation is the hardest moment. Once started, momentum often 
carries the session forward. The 2-minute commitment removes the "but I have to do the whole 
thing" cognitive load.

## Protocol 3: Decompose (for C — overwhelm)

If the task feels too large:

```
OK. "Work on [INTENT]" is too big. Let's make it smaller.

What's ONE thing — 15-30 min max — that would make [INTENT] 1% better?
Not finish it. Not solve it. Just 1% forward.

(If you can't think of one, run /sq-chunk [INTENT-TAG] and I'll break it down for you.)
```

If they struggle to identify the 1% action, immediately offer to run the chunk-intent skill:
"¿Quiero que lo descomponga ahora?"

## Protocol 4: Emotional Defusion (for D — fear/shame)

The Wall of Awful is real. Don't minimize it. Acknowledge and redirect:

```
Makes sense. This one has some weight to it.

Here's the thing: the emotional barrier is separate from the task itself.
The task is [X]. The feeling is [the wall].
You can feel the wall AND still open the file.

→ What would you do if you KNEW it was going to go well?
   (Describe that first action.)
```

This is the **If/Then Reframe**: "If I knew I couldn't fail, I would..." surfaces the actual
next action without the emotional load attached.

After they answer, immediately say: "Do that. Right now."

## Step 4: Presence during initiation

Stay present for the first 30 seconds after the suggested action:

```
OK — tell me when you've [opened the file / run the command / written the first line].
I'll be here.
```

Do NOT launch into explaining the full task. Do NOT offer options. Wait for confirmation.

When they confirm: "¿Qué ves?" / "What do you see?" — this anchors them in the actual task
and transitions from initiation to working mode.

## Step 5: Transition to working mode

Once they're started (confirmed at least one micro-action):

```
You're in. 

Current task: [one sentence from shutdown note or their own description]
Suggested focus block: 25 min

After 25 min I'll check in. Go.
```

Set the context so the user can refer back to it, but don't interrupt them once they're moving.

## Stall detection (proactive)

During session-start, check if the recommended intent has been "in-progress" for >3 sessions
with 0 shutdown notes added. If so, after the normal session brief, add:

```
⚠️ [INTENT-TAG] ha estado "en progreso" por [N] sesiones sin avance registrado.
¿Querés que apliquemos el protocolo de inicio? (responde "sí" o "salteamos")
```

Only offer once per session. Don't push.

## Output style

- Short sentences. No paragraph walls.
- Never say "just" (minimizes the struggle) or "it's easy" or "you just need to..."
- The word "now" is important — specificity of time reduces ambiguity
- End every protocol step with a concrete, immediate action

## Anti-patterns

- ❌ Don't explain why starting is hard (they know, it doesn't help)
- ❌ Don't offer 3 protocols at once — choose the most likely and offer alternatives after
- ❌ Don't say "you can do it!" — hollow motivation, zero traction
- ❌ Don't launch into the full task plan before the first micro-action
- ❌ Don't invoke if the user is already working — interrupting flow is worse than the wall
- ❌ Don't shame around the stall pattern ("you've been avoiding this for weeks")

## References

- Mahan, B. (2017): Wall of Awful — accumulated emotional weight blocking task entry
- Barkley, R.A. (2015): task initiation as distinct executive function deficit from motivation
- Deci & Ryan (1985): autonomy support vs control — why "just do it" commands fail
