---
description: Closes the current session, generates a structured shutdown note, and saves it in the active intent. Applies the Hemingway trick (suggest stopping at a "going good" point).
allowed-tools: [Read, Write, Edit, Bash, Glob]
---

# /sq-end

Closes the current session.

Invokes the `squirrel:session-end` skill to:
1. Read state.json and identify the active intent
2. Reconstruct what happened in the session (from the conversation + git)
3. Generate a shutdown note with: status, next physical action, active hypothesis, blockers, decisions made
4. Ask for confirmation before applying
5. Update Definition of Done checkboxes if applicable
6. Suggest a commit with a semantic tag
7. Apply Hemingway (suggest stopping at a "going good" point or leaving a TODO on the next line)

Optional arguments:
- `--quick`: quick shutdown (2 lines, no full structure)
- `--commit`: in addition to the shutdown note, commit automatically
- `--vault NAME` — operate on a specific vault (default if omitted)
