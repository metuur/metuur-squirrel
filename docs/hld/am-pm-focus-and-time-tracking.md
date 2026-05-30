# AM/PM Focus Slots & Time Tracking — High-Level Design

## Overview

The existing manual focus pick (`focus_today`, `focus_week`) lets the user declare "today I'm working on X." It works for a full-day intent but has no concept of time-of-day or how long the user actually worked. This change adds three things: (1) a second focus slot for PM so the user can split their day between two different intents, (2) a SQLite-backed history log so past picks and work sessions are queryable, and (3) a check-in/check-out mechanism that records actual working time and surfaces it as a derived `time_invested_minutes` field on the intent file.

The architectural commitment: **frontmatter tokens remain the source of truth for current focus state; SQLite is the source of truth for all history and time data.** Nothing in the existing heuristic (`_recommend_focus()`), the overdue/pressing logic, or the `focus_week` slot changes.

## Stakeholders & Impact

| Stakeholder | Today's pain | After this ships |
|---|---|---|
| Primary user (Javier) | One focus for the whole day — no way to plan "morning: deep work on X, afternoon: admin on Y." No record of how long tasks actually took. | AM focus defaults to full day. Optional PM override at midday. Check-in/out stamps real working time. `time_invested_minutes` appears in the intent file for at-a-glance review. |
| Obsidian-only sessions | `focus_today` is visible in frontmatter. `time_invested_minutes` is not recorded anywhere. | Both `focus_today_pm` and `time_invested_minutes` appear as plain frontmatter — readable and searchable in Obsidian without running Squirrel. |
| Retrospective review | No queryable history of what was focused when or for how long. | `GET /api/focus/history` returns picks and sessions by date range, derived from SQLite. |
| Desktop app (Tauri tray) | No morning prompt — user must remember to pick a focus. | On startup, if no `focus_today` exists for today, the tray fires a prompt. One prompt per day maximum. |

## Goals

When this ships, the following are observable and true:

1. **The user can pick separate AM and PM focus intents.** `focus_today` covers full day (AM default). `focus_today_pm` optionally overrides PM. Both are independent.
2. **Setting AM does not clear PM, and vice versa.** The strip-pass for each slot operates only on its own frontmatter key.
3. **Focus picks are recorded in SQLite** (`focus_picks` table) with vault, slot, date, timestamps.
4. **The user can check in and check out against the active focus.** Each action writes to `work_sessions` in SQLite.
5. **On checkout, `time_invested_minutes` is written to the intent file's frontmatter** as a derived cumulative total — not raw timestamps.
6. **SQLite is authoritative for time data.** If `time_invested_minutes` drifts, a `recalculate` command rewrites it from SQLite.
7. **On desktop startup, if no today focus exists, the tray shows a morning prompt.** At most once per day.
8. **`GET /api/focus` returns all three slots** (`today`, `today_pm`, `week`).
9. **`GET /api/focus/history` returns picks and sessions** by date or date range.

## Non-Goals

- Replacing or weakening `_recommend_focus()` — the heuristic is untouched.
- Suppressing overdue/pressing alerts when a manual focus is set.
- Writing raw check-in/check-out timestamps to the intent file — only the derived total.
- A "month" or "quarter" focus slot.
- Multi-user / multi-vault history merge semantics.
- Persisting `time_invested_minutes` across vault resets — SQLite is the source; the frontmatter field is a cache.
- A dedicated time-tracking UI beyond the check-in/out buttons on the focus card.

## Success Criteria

1. Picking a PM focus via `PUT /api/focus/today {slot:"pm"}` writes `focus_today_pm: YYYY-MM-DD-PM` to the chosen intent file without touching the AM intent file.
2. `GET /api/focus` returns `{today: {...}, today_pm: {...}, week: {...}}` with both slots populated independently.
3. Check-in → do work → check-out writes a complete row to `work_sessions` in SQLite and updates `time_invested_minutes` on the intent file.
4. Opening the intent file in Obsidian shows `time_invested_minutes: <n>` in frontmatter.
5. `GET /api/focus/history?date=YYYY-MM-DD` returns the day's picks and sessions with durations.
6. On desktop startup with no today focus, a tray notification appears. After picking, it does not appear again that day.
7. Running `recalculate` updates all `time_invested_minutes` values from SQLite with no manual edits required.
8. Existing `make test-cli` stays green.
