---
description: Captures a note, idea, research finding, or context into the vault with a semantic tag.
allowed-tools: [Read, Write, Glob]
---

# /sq-capture

Capture: $ARGUMENTS

Optional arguments:
- `--vault NAME` — operate on a specific vault (default if omitted)

Invokes the `squirrel-capture` skill, which:
1. Determines the appropriate semantic tag (`PROJECT-SUBAREA-NNN`)
2. Detects the note type (intent / research / constraint / reference)
3. Composes the note with frontmatter
4. Writes it to the corresponding folder in the vault
5. Links it from the Project Page if applicable
