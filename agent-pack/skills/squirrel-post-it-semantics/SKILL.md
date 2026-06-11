---
name: squirrel-post-it-semantics
description: Use when designing, researching, speccing, or implementing Squirrel Post-it / sticky note features. Preserves the product distinction between Post-its, Quick Tasks, and project/task notes: Post-its are ambiguous, low-friction working-memory captures that start independent from tasks and projects, but may later be converted or attached.
---

# Squirrel Post-it Semantics

## Core Distinction

Treat Post-its as a separate capture artifact from both Quick Tasks and project/task notes.

```text
Quick Task
  - Actionable by default
  - Small interruption to complete, snooze, or delete
  - Belongs in the task-management flow

Project / Task Note
  - Contextual by default
  - Attached to a known project or task
  - Carries richer supporting information

Post-it / Sticky Note
  - Ambiguous by default
  - Independent from project/task structure
  - Captures a random thought, idea, reminder, quote, phone number, or fragment
  - May later become a task, project, or project/task note, but does not start there
```

## Product Invariants

- A Post-it must be capturable without choosing a task, project, focus area, or workflow.
- A Post-it should preserve “capture now, decide later” behavior.
- A Post-it is not automatically actionable; avoid task language unless the user converts it.
- A Post-it is not a project/task note until explicitly attached or converted.
- A Post-it may later be linked to a task/project, converted into a task, or turned into project context.
- Capture UX should optimize for seconds, not classification accuracy.

## Existing Squirrel Context

- Quick Tasks already cover small actionable interruptions.
- Existing captures/notes can already attach to projects.
- The desired Post-it behavior covers the gap before the user knows what something is.
- Use this distinction when writing HLD/LLD/EARS docs, API names, UI copy, storage fields, tests, and migration notes.

## Naming Guidance

Prefer:
- `Post-it`
- `Sticky note`
- `Unstructured capture`
- `Capture now, organize later`

Avoid using these as synonyms:
- `task`
- `quick task`
- `project note`
- `task note`
- `intent`

## Validation Checklist

- Does capture work with only content?
- Can it exist forever without a task/project?
- Does UI copy avoid implying it is actionable?
- Is conversion explicit?
- Is attachment explicit?
- Are project/task notes still treated as richer contextual artifacts?
