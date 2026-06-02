---
description: Generates a structured 6-section brief (now/done/next/decisions/steps/context) ready to copy into email, Slack, or stand-up.
allowed-tools: [Read, Glob, Grep]
---

# /sq-brief

Generates a brief for the `$ARGUMENTS` project (or the active project).

Invokes the `squirrel:brief` skill, which produces the 6 sections:
1. 🎯 What I'm doing (NOW)
2. ✅ What I've already done (DONE)
3. 🎬 What's left (NEXT)
4. 🧠 Decisions made (DECISIONS)
5. 🚦 Next steps (STEPS)
6. 🌐 Important context (CONTEXT)

Optional arguments:
- `--short`: Slack/stand-up version (3 lines)
- `--email <stakeholder>`: email format + opens a mailto: draft
- `--all`: brief of all WIP projects (for weekly review)
- `--vault NAME`: operate on a specific vault (default if omitted)
