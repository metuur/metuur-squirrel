# Manual Focus Pick (Today & Week) — High-Level Design

## Overview

Today, the focus shown in `FocusWidget` is 100% automatic: `_recommend_focus()` (`apps/cli/lib/status_aggregator.py:340–386`) runs a 3-rule heuristic (critical → urgent → most-recent activity) at every `GET /api/home` call. The user has no way to say "I know there's an overdue thing, but *today* I'm working on something else." This is the wrong default for a focus-targeted tool: forcing the user back onto the heuristic's overdue choice when they have already decided otherwise is exactly the kind of friction that triggers task avoidance.

This change adds a **manual focus pick** for two independent slots — *today* and *this week* — without weakening the heuristic. The overdue/critical signal continues to win the primary focus card; the user's pick is rendered alongside it with a clear visual indicator. The pick is stored as YAML frontmatter on the chosen intent file (visible in Obsidian) and auto-expires daily/weekly so the user re-commits each day/week — a deliberate focus-friendly forcing function, not a UX bug.

The architectural commitment: **the vault is the source of truth, the heuristic is unchanged, and the pick is additive surface area**. No existing endpoint changes its semantics. No existing field in `/api/home.focus` changes shape. CLI, REST, and desktop UI all converge on the same YAML-on-intent-file storage.

## Stakeholders & Impact

| Stakeholder | Today's pain | After this ships |
|---|---|---|
| Primary user (Javier) | Overdue project always hijacks the focus card. No way to declare "today I'm working on X" without first clearing the overdue flag. | A small `Pick focus` button on `FocusWidget` and a `/sq-focus` CLI let the user pin a project+intent for today or this week. The overdue card still appears (so nothing is hidden), but the chosen focus appears alongside it with a 📌 indicator. |
| Obsidian-only sessions | No visibility into "what is Squirrel currently treating as my focus" when the desktop app isn't open. | The pick is a plain `focus_today: 2026-05-28` / `focus_week: 2026-W22` line in the intent file's frontmatter — readable, searchable, and editable directly in Obsidian. |
| macOS reminders daemon | Three-button alert (`Dismiss` / `Snooze` / `Open`) where `Open` only launches the browser. The user has no way to commit to the alerted project from the notification itself. | The `Open` button is replaced by **`Focus now`**: clicking it pins the alerted project's active intent as today's focus AND opens the web UI. The daemon keeps its existing alert cadence, snooze behaviour, and per-day cap unchanged. The manual pick does **not** suppress overdue reminders. |
| Future LLM agents reading the vault | No machine-readable signal for "what is the human currently focused on." | `focus_today` / `focus_week` frontmatter keys become a stable, parseable signal across the vault. |

Out-of-scope consumers (browser SPA's Projects page, Capture flow's `ProjectSelector`, deadline scanner) are listed only to confirm they are not affected by this change.

## Goals

When this ships, the following are observable and true:

1. **The user can pick a (project, intent) pair as the focus for today.** Surfaces: `FocusWidget` button → modal selector, `PUT /api/focus/today`, `/sq-focus today TAG/INTENT-SLUG`.
2. **The user can pick a separate (project, intent) pair as the focus for this week.** Surfaces: same three.
3. **The two picks are independent.** Setting one does not affect the other; they may point to the same intent or to different intents.
4. **The pick is stored in the intent file's YAML frontmatter** — `focus_today: <YYYY-MM-DD>` and/or `focus_week: <ISO-week>` — visible in Obsidian without running Squirrel.
5. **At most one intent in the vault carries `focus_today: <today's-date>` at any time.** Same single-pick invariant for `focus_week`. When the user picks a new focus, the previous flag is removed atomically from the prior intent file.
6. **The pick auto-expires.** `focus_today` is considered set only when the date matches today's local date. `focus_week` is considered set only when the ISO-week token matches the current ISO week. Stale entries are ignored on read and pruned on next write.
7. **The overdue/critical heuristic is untouched.** `_recommend_focus()` keeps returning the heuristic result. `GET /api/home.focus` keeps its exact current shape and semantics.
8. **The picks are surfaced alongside the heuristic focus** via a new `GET /api/home.manual_focus` field (additive; nullable per slot).
9. **`FocusWidget` renders both.** Primary card = heuristic focus (overdue still wins). Below it, two pill-style indicators show "📌 Today: {intent}" and "📌 This week: {intent}" when set, with a `Change` and `Clear` affordance on each.
10. **A single CLI entry point** — `/sq-focus [today|week] [TAG/INTENT-SLUG | --clear]` (and bare `/sq-focus` to show current picks) — covers the keyboard-driven flow.
11. **The macOS reminder daemon's notification gains a `Focus now` button** (replacing `Open`) that sets today's focus to the alerted project's active intent and opens the web UI.
12. **Clearing a pick removes the YAML key from the intent file** (does not leave a stale `focus_today: null`).

## Non-Goals

Out of scope for this change:

- **Replacing or weakening the 3-rule heuristic.** Overdue still wins the primary focus card.
- **Suppressing overdue alerts when a manual focus is set.** The PRESSING section, deadline daemon, and `priority: finishing-tax` logic all keep their current behaviour.
- **A "focus history" log.** Each pick overwrites the previous one; we do not record the sequence of past picks.
- **Multi-user / vault-merge semantics.** Single-user, single-vault remains the assumption. If two vaults are synced, last-write-wins per file (standard Obsidian sync behaviour).
- **A "month" or "quarter" focus slot.** Only today + week in this change.
- **Pinning at the project level instead of intent level.** The pick is always (project + intent); picking a project without an intent is rejected.
- **Cross-device sync of the picks** beyond what the vault sync already provides — there is no `~/.squirrel/`-side state for this feature.
- **Cleaning up *all* stale `focus_today` / `focus_week` entries across the vault on every read.** Lazy cleanup only: stale values are ignored on read and removed on the next write that touches that file.
- **A "snooze overdue" feature.** Rejected: the whole point is that the pick does NOT touch overdue logic.

## Success Criteria

This is done when:

1. From the desktop popup, clicking `Pick focus` on `FocusWidget` opens a modal showing every active project + its intents; selecting one writes the YAML flag and the widget shows "📌 Today: {intent}" within 1s.
2. Opening the same intent file in Obsidian shows the new `focus_today: <YYYY-MM-DD>` line in the frontmatter — and Obsidian's frontmatter search (`focus_today: 2026-05-28`) finds exactly that one file.
3. Running `/sq-focus week PROJECT-TAG/INTENT-SLUG` writes `focus_week: <ISO-week>` to the intent file, removes any prior week-pick flag from another file, and prints the resulting state.
4. Running `/sq-focus` with no args shows both picks in a 2-line summary (or "(none)" for unset slots).
5. With both picks set and an overdue project present, `GET /api/home`:
   - Returns the overdue project in `focus` (unchanged behaviour).
   - Returns the user's two picks in `manual_focus.today` and `manual_focus.week`.
   - Returns the overdue project in `pressing[]` (unchanged behaviour).
6. After local midnight, `manual_focus.today` is `null` (the date in the YAML no longer matches today) — without any background process running. The YAML line itself remains until the next write.
7. After the ISO week rolls over (Monday 00:00 local), `manual_focus.week` is `null`. Same lazy semantics.
8. Clicking `Clear` on the today pill removes the `focus_today` line from the intent file (the key is deleted, not set to `null`).
9. If two intent files somehow both carry `focus_today: <today>` (e.g. manual Obsidian edit), the API picks the most-recently-modified one and the next write prunes the others.
10. Triggering the reminder daemon manually (`reminder-daemon.sh --force`) shows a dialog with `Dismiss` / `Snooze` / `Focus now`. Clicking `Focus now` writes `focus_today: <today>` to the alerted project's active intent file and opens `http://localhost:3939/projects/<TAG>` — verified by inspecting the intent file's frontmatter afterwards.
11. Running the existing test suite (`make test-cli`) stays green; new tests for the focus-pick path exist and pass.

If all eleven pass, the feature ships.
