# /sq-deadlines — High-Level Design

## Overview

A read-only slash command that surfaces all vault deadlines grouped by urgency
level. Wraps the existing `deadline_scanner.py` script, which classifies intents
into six urgency buckets (overdue → critical → urgent → soon → upcoming →
future_fyi). The command makes deadline visibility available mid-session without
the noise of a full `/sq-status` output.

## Stakeholders & Impact

- **ADHD developer (primary)**: today must leave Claude or run `/sq-status`
  (full vault dump) to check deadlines. After this ships: one focused command.
- **macOS daemon (secondary)**: already calls `deadline_scanner.py` directly —
  no change.

## Goals

- `/sq-deadlines` renders all vault deadlines grouped by urgency
- `--level critical,urgent` narrows to specific levels
- Empty vault or no deadlines: clean "No deadlines found" message
- Command is read-only — zero vault mutations

## Non-Goals

- Modifying `deadline_scanner.py`
- Writing snooze or dismiss state
- Per-project filtering
- Any LLM involvement (pure script wrapper)

## Success Criteria

Running `/sq-deadlines` in a Claude session shows the same urgency groups as
`python3 lib/deadline_scanner.py --vault <vault> --pretty` with a human-readable
render (not raw JSON). `--level` flag narrows output correctly.
