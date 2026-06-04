# ADR 0001 — WIP cap counts every open project (including stale and Scratch Pad)

- **Status:** Accepted (records current behaviour; deeper question deferred)
- **Date:** 2026-06-04
- **Deciders:** Javier (with uncle-senior + uncle-lead review)

## Context

`status_aggregator.py` computes the WIP count as a pure folder count:

```python
wip_count = len(projects_by_loc["wip"])   # every folder under 01-Proyectos-Activos
```

There is **no active-vs-stale filtering** on this path. A `wip_max` (currently 3,
hard-coded) drives a "WIP excede el máximo" warning when `wip_count > wip_max`.

This surfaced while fixing a stale test: `test_status_aggregator_cli` asserted
`wip.count == 2`, but the fixture vault had gained a third project folder
(`SCRATCH-PAD`), and the minimal fixture also contains a project literally named
`SIDEPROJECT-STALE`. That naming raised a real question: **should a stale project
count toward the active WIP cap?**

## Decision

**Keep the current behaviour: the WIP cap counts every open folder under
`01-Proyectos-Activos/`, including the Scratch Pad and stale projects.**

Rationale:

- The cap is a **load** signal ("how many things are open"), not a **progress**
  signal. A project stalled at 90% still occupies cognitive WIP — for an ADHD
  tool, counting it is arguably the point.
- `docs/lld/future-reminders-and-scratch-pad.md` already states: "The Scratch Pad
  counts toward the WIP cap like any other project." The same reasoning extends
  to a stale project until it is explicitly moved to a Parking-Lot location.
- Staleness already has a home: `_recommend_focus` uses it to drive the
  recommendation, so excluding stale projects from the *count* would remove the
  pressure signal without adding value.
- No EARS/LLD requirement for stale-exclusion exists. We will not invent one.

## Open question (deferred — not blocking)

Should the WIP cap ever distinguish **"open"** from **"actively progressing"** —
e.g. a `last_active`/`stale` dimension that feeds the cap separately from the raw
folder count?

Resolving signal: an explicit requirement in `docs/ears/` or `docs/lld/`. If that
requirement is written, update the cap logic at `status_aggregator.py:366` and its
tests together. Until then, current behaviour stands.

## Consequences

- The WIP count is honest about total open load; users see pressure from stale
  work, which is intended.
- Tests no longer pin a hand-maintained magic number:
  - `test_status_aggregator_cli` (end-to-end smoke) is **drift-proof** — it derives
    the expected count from the fixture directory and asserts contract invariants
    (`count == len(projects)`, `max == 3`, `at_capacity`, warning-iff-over-cap).
  - `TestWipCount` pins the **exact** intended inventory
    (`{TEST-PROJECT, SIDEPROJECT-STALE, SCRATCH-PAD}`) with a docstring, so fixture
    changes force an intentional update instead of a reflexive number bump.
- `wip_max` is still hard-coded (`= 3`); making it configurable is out of scope for
  this decision.
