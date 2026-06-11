---
description: Starts a work session on a project, loading all the context from the vault. Usage: /sq-start [PROJECT-TAG]
allowed-tools: [Read, Write, Bash, Glob, Grep]
---

# /sq-start

Starts a session on the `$ARGUMENTS` project (or asks if none is specified).

Optional arguments:
- `--vault NAME` — operate on a specific vault (default if omitted)

Invokes the `squirrel-session-start` skill to:
1. Identify the active project
2. Read the Project Page and the intents
3. Generate a loading note of at most 200 words with: what I'm doing, the last thing I did, next physical action, blockers, critical context, a concrete opening suggestion

The skill updates `~/.squirrel/state.json` with the active project and intent.

After the loading note, offer ONE concrete action to get started (open file X line Y, run test Z, etc.).
