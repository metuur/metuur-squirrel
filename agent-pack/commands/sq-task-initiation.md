---
description: Task-initiation protocol against executive paralysis. Detects the type of block and applies the right protocol (Smallest Action, 2-Minute Start, Decompose, Emotional Defusion).
allowed-tools: [Bash, Read]
---

# /sq-task-initiation

Breaks start-up paralysis. Use when the user can't get a task going.

Optional arguments: `[INTENT-TAG]`, `--vault NAME` (default if omitted)

Invokes the `squirrel-task-initiation` skill (see `skills/squirrel-task-initiation/SKILL.md`).

The skill:
1. Identifies the blocked intent (from the TAG, from state, or by asking)
2. Reads the last shutdown note to extract the "next physical action"
3. Diagnoses the type of block (A=don't know what to do / B=can't click in / C=overwhelmed / D=fear)
4. Applies the appropriate protocol:
   - **Protocol 1 (Smallest Action)**: open a specific file, nothing more
   - **Protocol 2 (2-Minute Start)**: just 2 minutes, then you can stop
   - **Protocol 3 (Decompose)**: the task is too big → offers `/sq-chunk-intent`
   - **Protocol 4 (Emotional Defusion)**: "what would you do if you knew it would turn out fine?"
5. Stays present until the first micro-action is confirmed
6. Hands off gently to working mode

Automatic triggers (from `session-start`): an intent that's been "in-progress" for >3 sessions with no new shutdown note.
