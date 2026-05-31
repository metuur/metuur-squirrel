---
name: squirrel-capture
description: Capture and persist context, notes, ideas, or research findings to the local Markdown vault with semantic tags. Use this skill whenever the user says "capture this", "save this", "anotá", "guarda", or whenever a piece of information emerges that should outlive the current conversation (research findings, requirements, constraints, decisions, side observations, links). Always assigns a semantic tag (PROJECT-SUBAREA-COMPONENT-NNN) and writes to the vault root configured in ~/.squirrel/config.toml. Accepts an optional `vault_name` argument; when omitted, writes to the default vault (R-7.1, R-7.3).
---

# squirrel:capture

## Purpose
Persist transient context from the agent session into the local Markdown vault so it survives session boundaries, model context windows, and machine restarts. This is the primary "external memory" entry point for the user.

## When to invoke
- Explicit triggers: "capture this", "save this", "anotá", "guarda esto", "agregalo al vault"
- Implicit triggers (be proactive):
  - User shares a research finding that informs a project
  - User mentions a constraint or requirement ("we can't use X because Y")
  - User states a fact about the codebase worth remembering ("the auth module lives in /old-auth, don't touch it")
  - User finishes a debugging session with a non-obvious root cause
  - User mentions a link or resource that should be archived

If the trigger is implicit, ASK before capturing: "¿Querés que guarde esto como nota en el vault? Tag sugerido: X."

## Workflow

### Step 1: Read configuration
Read `~/.squirrel/config.toml` to get:
- `vault_path` — root directory of the Markdown vault
- `active_projects` — list of WIP project tags (used for tag suggestion)
- `default_capture_folder` — where to put untagged captures (default: `99-Resources/Captures/`)

If the config file does not exist, ask the user to run `/sq-init` first.

### Step 2: Determine and validate the tag

The tag is a SEMANTIC ID of the form `PROJECT-SUBAREA-COMPONENT-NNN`:
- Uppercase, hyphens (not underscores or spaces)
- Exactly 3 named segments + 3-digit zero-padded number
- Examples: `TRABAJO-PROYECTO-AUTH-001`, `VISA-FAMILIA-DOCS-002`, `SIDEPROJECT-FOYER-RESEARCH-001`

Tag resolution order:
1. If the user provided a tag explicitly → use it (validate below)
2. If the current session is bound to a project (via `/sq-start`) → use that project as prefix
3. Otherwise → propose a tag based on conversation context and ASK before using it

To pick the next NNN, run:
```bash
ls "$VAULT_PATH" | grep -i "^${PROJECT_PREFIX}-${SUBAREA}-" | wc -l
```
Then increment.

<!-- @spec CAPTURE-003 -->
**Tag validation (CAPTURE-003 — mandatory before any write):**

Locate `tag_parser.py` using the candidate-path pattern:
```bash
TAG_PARSER=""
for p in lib/tag_parser.py ../lib/tag_parser.py ~/.squirrel/lib/tag_parser.py; do
  [ -f "$p" ] && TAG_PARSER="$p" && break
done
```

Then validate:
```bash
python3 "$TAG_PARSER" validate "$TAG"
```

- Exit 0 → tag is valid, proceed to Step 3.
- Exit 1 → tag is invalid. Show the `tag_parser.py` error message and the suggestion (if any) to the user. Ask the user to confirm a corrected tag. Do NOT write the note until the tag passes validation.

A note with zero valid tags or multiple tags in the `id` field MUST NOT be written.

<!-- @spec CAPTURE-004 -->
### Step 2b: Check for duplicate content (CAPTURE-004)

Before composing a note, check whether an identical capture already exists for the same project within the dedup window:

```bash
DEDUP_WINDOW=${dedup_window_seconds:-60}   # configurable in config.toml, default 60
find "$VAULT_PATH" -name "*.md" -newer "$( date -v -${DEDUP_WINDOW}S +%Y%m%d%H%M%S 2>/dev/null || date -d "-${DEDUP_WINDOW} seconds" +%Y%m%d%H%M%S )" \
  | xargs grep -l "$(echo "$CONTENT" | head -c 80)" 2>/dev/null
```

- If a match is found → do NOT create a new file. Instead, append a `## Update <ISO-8601>` section to the existing note with the new content, then confirm to the user which file was updated.
- If no match → continue to Step 3.

### Step 3: Detect note type
Based on the content, choose ONE type:

| Type | When | Folder |
|---|---|---|
| `intent` | A task / requirement to accomplish | `01-Proyectos-Activos/<PROJECT>/` |
| `research` | Findings from investigation | `01-Proyectos-Activos/<PROJECT>/` |
| `decision` | Architectural / design decision (use `squirrel:decision` skill instead) | `01-Proyectos-Activos/<PROJECT>/` |
| `reference` | Snippet, link, doc | `99-Resources/Captures/` |
| `constraint` | Something that constrains the project | `01-Proyectos-Activos/<PROJECT>/` |
| `loose` | Untagged thought to triage later | `99-Resources/Captures/inbox.md` (append) |

<!-- @spec CAPTURE-001 -->
### Step 4: Compose the note
Use the template at `templates/intent.md` (see plugin templates), or for non-intent notes:

```markdown
---
id: <TAG>
proyecto: <PROJECT_PREFIX>
tipo: <type>
estado: <pending|in-progress|done|archived>
creado: <YYYY-MM-DDTHH:MM:SS±HH:MM>
tags: [<type>, proyecto/<PROJECT>, <other-tags>]
---

# <TAG> — <Short title>

## Context
<Why this matters / where it came from in the conversation>

## Content
<The user's original wording, verbatim — do NOT summarize, rephrase, or improve>

## Source
- Session: <timestamp>
- Agent: <claude-code | codex | cursor | ...>
- Triggered by: <quote of user message that caused capture>

## Links
- Parent: [[<PROJECT_ROOT>]]
- Related: ...
```

**`creado` MUST be a full ISO-8601 datetime with timezone offset** (e.g. `2025-05-24T14:32:00-03:00`), never a date-only value.

### Step 5: Write to disk
Use the `Write` tool. Path: `<vault_path>/<folder>/<TAG>.md`.

If the file already exists, do NOT overwrite — instead:
1. Tell the user
2. Offer to: (a) update (append new section), (b) create with `-002` suffix, (c) cancel

### Step 6: Link from Project Page
If the project has a root file `<PROJECT>.md`, append a link entry under the appropriate `## Componentes e Intents` section:

```markdown
- [[<TAG>]] <Short title> — <one-line status>
```

### Step 7: Confirm to user
Output a brief confirmation:
```
✅ Captured as <TAG>
   → <full path>
   → linked from <project-page>
```

## Edge cases

### No project context
If the user is just chatting and captures something untethered: put it in `99-Resources/Captures/inbox.md` with a timestamp and short heading. Tell the user to triage during weekly review.

### Multiple captures in one message
Split into multiple captures with sequential NNN.

<!-- @spec CAPTURE-002 -->
### Captures that look like decisions (CAPTURE-002 — ADR-ligero flow)

When the content matches decision language — "voy a usar X", "decidí Y", "elegí Z porque", "going to use X", "I decided Y" — activate the ADR-ligero flow:

1. **Propose** a structured note draft to the user with these sections:
   ```markdown
   ## Context
   <why the decision was needed>

   ## Alternatives
   <options that were considered>

   ## Decision
   <the chosen option, verbatim>

   ## Consequences
   <expected outcomes, trade-offs, risks>
   ```
2. **Ask for explicit confirmation** before writing: "¿Confirmo y guardo esta decisión como `<TAG>`?" (or equivalent in conversation language). Do NOT write the note until the user confirms.
3. Set `tipo: decision` in frontmatter.
4. Continue with Steps 2–7 above (tag validation, dedup check, write, link).

### Conflicting tags
If the user provides a tag that conflicts with an existing project's namespace but not its conventions, ask for clarification BEFORE writing.

## Output format
- Brief confirmation (3-4 lines), no verbose explanation
- Include the exact tag and path so the user can grep/find later
- If you made any inference (tag, type, folder), state it briefly so the user can correct

<!-- @spec CAPTURE-005 -->
## Anti-patterns
- ❌ Don't ask 5 questions before capturing — propose defaults and let the user override
- ❌ Don't capture every utterance — there's a signal-to-noise judgment
- ❌ Don't use random IDs (UUIDs, timestamps as IDs) — the tag must be semantic and readable
- ❌ Don't overwrite without warning
- ❌ Don't write outside the configured vault path
- ❌ Don't summarize, rephrase, or improve the user's wording at capture time — write the `## Content` section exactly as said (CAPTURE-005)
- ❌ Don't write a note before the tag passes `tag_parser.py validate` — no exceptions (CAPTURE-003)
- ❌ Don't write a decision note without explicit user confirmation — always propose first (CAPTURE-002)

## References

- Allen, D. (2001): GTD "capture everything" — cognitive load of remembering things prevents acting on them
- Baddeley, A. (2000): working memory capacity ~4 chunks — external capture offloads limited phonological loop
- Carroll, R. (2013): Bullet Journal — structured capture prevents the "pile of sticky notes" trap
- Newport, C. (2016): deep work interrupted by untracked ideas loses ~23 min of focus recovery (Gloria Mark, UC Irvine, 2008)
