---
description: Breaks a large intent into manageable chunks (≤60 min each) with domain-specific names and done conditions.
allowed-tools: [Bash, Read, Write]
---

# /sq-chunk-intent

Takes an intent from the vault (or a free-form description) and breaks it into manageable phases + chunks.

Optional arguments: `[INTENT-TAG]`, `--vault NAME` (default if omitted)

Invokes the `squirrel-chunk-intent` skill (see `skills/chunk-intent/SKILL.md`).

The skill:
1. Reads the intent from the vault (if a TAG is passed)
2. Asks for or confirms the total time estimate
3. Runs `estimate_buffer.py` to apply the focus multiplier
4. Runs `chunk_helper.py` to compute the phase structure
5. Fills in domain-specific names (the LLM's job)
6. Presents the plan with a "Done when" for each chunk
7. Offers to write the chunks as checkboxes in the intent
8. Offers to hand off to the `task-initiation` skill for the first chunk
