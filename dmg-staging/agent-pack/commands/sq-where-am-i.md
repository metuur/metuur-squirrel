---
description: "Where was I?" — Shows the current state of all WIP projects and suggests where to pick up.
allowed-tools: [Read, Glob, Grep]
---

# /sq-where-am-i

Quick diagnostic: where were you?

Optional arguments:
- `--vault NAME` — operate on a specific vault (default if omitted)

Invokes the `squirrel:brief` skill with `--all` to:
1. List all WIP projects
2. For each one: estimated progress, last intent, next action
3. Detect warning signals:
   - Projects with no activity for >3 days
   - Foyer Family (or any project with `priority: finishing-tax`) with no progress
   - Blocked intents
4. Suggest 1 concrete action for TODAY based on deadlines and blockers

Ideal for starting the day or after several days without touching the vault.
