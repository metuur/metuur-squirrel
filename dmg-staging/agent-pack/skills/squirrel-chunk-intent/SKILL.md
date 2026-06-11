---
name: squirrel-chunk-intent
description: Decompose a large or overwhelming intent into focus-friendly chunks with time estimates. Use when the user says "this intent is too large", "I don't know how to attack this", "this is too much", "how do I start X", "break down X for me", "chunk this task", runs /sq-chunk [INTENT-TAG], or when task-initiation Protocol 3 redirects here. Also offers automatically when an intent's estimate exceeds 3 hours.
metadata:
  category: task-decomposition
  pairs-with: [squirrel-task-initiation, squirrel-estimate, squirrel-session-start]
  engine: chunk_helper.py
---

# squirrel:chunk-intent

## Purpose

A single large intent labeled "implement auth" or "refactor database layer" is invisible to the
The brain — too abstract to start. This skill converts it into a concrete sequence of chunks,
each ≤60 min, with domain-specific names the user recognizes.

The **script** (chunk_helper.py) calculates the time distribution and phase structure.
The **LLM** (you) fills in the domain-specific meaning — the script can't know that
"Core Implementation" means "wire the JWT middleware to the existing router".

## Workflow

### Step 1: Identify the intent

**Explicit**: `/sq-chunk TRABAJO-PROJ-AUTH-001`
**Implicit**: user describes the task — extract a working title

If a tag is provided, read the intent from the vault:
```bash
# Find the intent file
find "$VAULT_PATH/01-Proyectos-Activos" -name "*.md" | xargs grep -l "^id: $TAG" 2>/dev/null | head -1
```

Extract:
- `title` — what it is
- `definition_of_done` — what "finished" looks like
- Any existing task checkboxes — these become chunk names
- `prioridad` — affects how aggressive the time estimate is

### Step 2: Get or confirm the time estimate

If the intent has an `estimate` in frontmatter, use it.
If not, ask: "How long do you estimate this will take in total? (minutes or hours)"

Run the estimate buffer to apply the focus multiplier:

```bash
python3 "$SCRIPT_DIR/estimate_buffer.py" --estimate "$USER_ESTIMATE" --pretty
```

Show the user the adjusted estimate:
```
Your estimate: [RAW]
With focus buffer (×[MULTIPLIER]): [ADJUSTED]
Reason: [EXPLANATION]

Shall we use [ADJUSTED] for the chunk plan?
```

Wait for confirmation or let them override.

### Step 3: Run chunk_helper

```bash
python3 "$SCRIPT_DIR/chunk_helper.py" --minutes $TOTAL_MINUTES --pretty
```

The script returns phases with default names (Research, Setup, Core, Polish, Testing).
These are structural placeholders.

### Step 4: Map phases to domain-specific names

This is the LLM's job. Using the intent title, DoD, and any existing task checkboxes:

Replace generic names with names that match the actual work. Examples:

| Generic | Domain-specific (auth example) |
|---------|-------------------------------|
| Research & Planning | Read existing JWT implementation + understand current session flow |
| Setup & Scaffolding | Add jsonwebtoken dep + create auth middleware skeleton |
| Core Implementation | Wire middleware to /api routes + implement token validation |
| Polish & Edge Cases | Handle expired tokens, refresh logic, error messages |
| Testing & Documentation | Write 3 tests for auth flow + update API docs |

**Rules for naming chunks:**
- Name must start with a verb (Read, Write, Add, Fix, Implement, Test, Review)
- Max 8 words
- Must be recognizable from the intent's DoD or task list
- No "etc." or vague endings

### Step 5: Present the chunk plan

```markdown
## 📦 Chunk plan: [INTENT-TITLE]

Total: [ADJUSTED_TIME] ([RAW_TIME] × [MULTIPLIER] focus buffer)
Chunks: [N] chunks across [M] session(s)

### Session 1 — [TOTAL_MIN] min
  🔬 [Domain-specific Research name] — [MIN] min
     "Done when: [one sentence — what you'll have at the end of this chunk]"
  🛠 [Domain-specific Setup name] — [MIN] min
     "Done when: ..."

### Session 2 — [TOTAL_MIN] min
  ⚙️ [Domain-specific Core name] — [MIN] min
     "Done when: ..."
  ✨ [Domain-specific Polish name] — [MIN] min
     "Done when: ..."

### Session 3 — [TOTAL_MIN] min  (if needed)
  🧪 [Domain-specific Test name] — [MIN] min
     "Done when: ..."

**Estimated: [N] days at ~2 sessions/day**
```

The "Done when" line is critical — it converts abstract work into a concrete finish
line for each chunk. Without it, the chunk is just a time box without an exit condition.

### Step 6: Update the intent (with user confirmation)

Ask: "Shall I update intent [TAG] with these tasks? (I'll add them as checkboxes)"

If yes, append the chunk list as checkboxes to the intent file:

```bash
# Append to the intent file's task section
python3 -c "
import pathlib
intent_path = '$INTENT_PATH'
content = pathlib.Path(intent_path).read_text()
chunks_md = '''
## 🧩 Chunks (generated)
- [ ] [chunk1 name] — [min] min
- [ ] [chunk2 name] — [min] min
...
'''
# Insert before the first section that's not ## Tareas concretas
# or append at end
pathlib.Path(intent_path).write_text(content + chunks_md)
"
```

If no: "OK. Use the plan above as reference. You can copy-paste the checkboxes when you're ready."

### Step 7: Offer the first chunk as a start

End with a handoff to task-initiation for the first chunk:

```
Ready to start?

→ First chunk: [FIRST_CHUNK_NAME] — [MIN] min
   Done when: [done condition]

Shall we begin? (reply "yes" and I'll help you get started)
```

If they say yes, invoke task-initiation Protocol 1 with the first chunk as the specific task.

## Large intent handling (>8 hours)

If the total adjusted estimate exceeds 8 hours:

1. First apply chunking normally
2. Then note: "This intent is large. Consider creating sub-intents for each session:
   - [SESSION_1_NAME] — separate intent
   - [SESSION_2_NAME] — separate intent"
3. Offer to create the sub-intents from the template

Don't force the split — some users prefer one large intent. Just surface the option.

## Minimal mode (no vault)

If there's no intent file (user just describes the task verbally):
1. Ask: title + total estimate
2. Skip Steps 1 and 6 (no file to read/write)
3. Proceed with Steps 2–5 and 7

## Anti-patterns

- ❌ Don't use generic phase names in the output — always domain-specific
- ❌ Don't skip the "Done when" line — it's the whole point
- ❌ Don't present more than 3 sessions at once — paralysis by volume
- ❌ Don't ask the user to estimate 5 different sub-tasks — one total estimate, script handles distribution
- ❌ Don't chunk a task that's already ≤30 min — overhead exceeds value
- ❌ Don't auto-write to the intent file without confirmation

## References

- Barkley (2015): time blindness means tasks need explicit sub-goals, not just time boxes
- Leroy (2009): incomplete tasks fragment attention — done conditions reduce residue
- Ashinoff & Abu-Akel (2021): task chunking as hyperfocus entry point
