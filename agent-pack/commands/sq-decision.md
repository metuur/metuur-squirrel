---
description: Captures an architectural/design decision as a lightweight ADR in the vault.
allowed-tools: [Read, Write, Glob]
---

# /sq-decision

Captures a decision about $ARGUMENTS (or about the recent conversation).

Optional arguments:
- `--vault NAME` — operate on a specific vault (default if omitted)

Invokes the `squirrel:decision` skill, which:
1. Assigns the tag `<PROJECT>-DECISION-<NNN>`
2. Extracts from the conversation: context, decision, alternatives considered, consequences
3. Asks for confirmation of the fields
4. Creates the file `<PROJECT>-DECISION-<NNN>.md` in ADR format
5. Links it from the Project Page
6. Offers to notify relevant stakeholders
