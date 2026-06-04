# Quick Tasks — Focus Stack — High-Level Design

## Overview

A new lightweight task type, the **Quick Task**, gives the user a safe place to park
small interruptions (2–5 minute actions — send an attachment, approve a transaction,
reply to a one-line email) **without** acting on them immediately and breaking focus.
Quick Tasks live in a dedicated, intentionally small **Quick Task Stack**: a FIFO queue
that holds at most **5 active** items. The oldest sits at the top, new ones are added to
the bottom, and the user is nudged to clear them in order. A captured task is surfaced
later as a gentle in-app reminder rather than demanding attention now.

This is **focus management, not task management.** The hard cap of 5 and the constrained
snooze model exist specifically to stop the stack from becoming yet another backlog.

## Stakeholders & Impact

**Primary user (sole user).**

| Current pain | After this ships |
|---|---|
| A 3-minute interruption either gets done now (breaking the current focus block) or is held in the user's head | The user presses one shortcut, types one line, and returns to work — the task is parked |
| Quick captures become full intent tasks that clutter projects and never get cleaned up | Quick Tasks are capped at 5 active and surfaced for fast disposal, not accumulation |
| No "from anywhere" capture — the user must open the window and navigate | A global shortcut, a tray item, and a web button all funnel to one capture box |
| Parked items are silently forgotten | The 30s daemon surfaces the oldest task as a low-key alert + tray badge until it is cleared |

**Secondary consumers.** The existing tray poller (`tray_alerts.rs`) and the in-app
notification center are extended — Quick Tasks reuse their plumbing (SQLite notifications
table, badge, in-app center rows). No new external systems.

## Goals

- A Quick Task can be **captured from anywhere** via a global shortcut (`Ctrl+Cmd+Q`), a
  tray menu item, or a web-UI button — all three open the same minimal one-line capture box.
- Each Quick Task is stored as a markdown file in the protected `SCRATCH-PAD` project
  (`QT-NNN.md`, `quick_task: true`), reusing the existing vault/frontmatter infrastructure.
- The Quick Task Stack behaves as a **FIFO queue**: oldest at top, new appended to bottom,
  completion encouraged in order.
- A **hard limit of 5 active** Quick Tasks is enforced. Attempting to add a 6th is blocked
  until the user completes, deletes, or snoozes one.
- A Quick Task can be **completed**, **deleted**, or **snoozed**. Snoozing temporarily
  removes it from the active 5 (freeing a slot) and auto-returns it to the bottom of the
  stack after a delay.
- Parked tasks are **surfaced gently**: the existing 30s daemon shows the oldest active
  task as a low-key in-app alert + tray badge on a cooldown, and an always-visible widget
  shows the full stack.
- The stack is **kept small on purpose**: snoozing is bounded so snoozed items cannot
  silently grow into an unbounded backlog.

## Non-Goals

- Quick Tasks do **not** participate in focus picking, AM/PM scheduling, deadlines, the
  project WIP cap, priorities, tags, or estimates. They are interruption parking only.
- No editing a Quick Task's text after capture (delete + re-add instead).
- No manual reordering — order is strictly FIFO by capture time.
- No recurring Quick Tasks and no Quick Task history/audit of completed items.
- No new OS-notification behavior — Quick Task alerts ride the existing in-app notification
  center and honor the existing OS-popup setting; nothing new is added there.
- No Windows or Linux support in this iteration (macOS desktop only, matching the
  notification center).
- The `SCRATCH-PAD` protection, WIP-counting, and reminder behavior from the existing
  Scratch Pad feature are unchanged.

## Success Criteria

1. Pressing `Ctrl+Cmd+Q` from any foreground app opens a one-line capture box; typing text
   and pressing Enter creates `QT-NNN.md` in `SCRATCH-PAD` and returns focus to the prior app.
2. With 5 active Quick Tasks, a 6th create attempt is rejected (`QUICK_TASK_LIMIT_REACHED`)
   and the UI tells the user to complete, delete, or snooze one first.
3. `GET /api/quick-tasks` returns active tasks ordered oldest-first; the most recently added
   is last.
4. Completing or deleting a Quick Task frees a slot, allowing a new capture immediately.
5. Snoozing a Quick Task drops it out of the active count; after its delay elapses and a slot
   is free, it reappears at the bottom of the stack.
6. While at least one active Quick Task exists, the tray shows a Quick Tasks badge/section and
   the oldest task is surfaced as an in-app notification on the existing cooldown.
7. A snoozed task that becomes due while the stack is already full is **not** silently dropped
   and does **not** breach the cap — it waits and the user is nudged to free a slot.
