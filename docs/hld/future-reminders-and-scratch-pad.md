# Future Reminders & Scratch Pad — High-Level Design

## Overview

Two related features that extend the vault's temporal awareness. First, a **future reminder** system: users can attach a `reminder_date` to any task, note, or capture, so the system brings the item back to their attention at the right time — completely separate from deadline/overdue tracking. Second, a **Scratch Pad** project: a protected default project that exists in every vault from first launch, providing a safe place for ideas, quick captures, and reminders that don't belong to a specific project yet.

---

## Stakeholders & Impact

**Primary user (sole user).** Today, the only date mechanism is `deadline` — it signals something is *due*. There is no mechanism to say "ignore this for now, remind me in three months." Users must either keep ideas in their head, clutter a project with premature tasks, or rely on an external tool. After this ships, the user can set a future reminder on any item and trust the system to surface it at the right time without any further action.

The Scratch Pad removes the friction of needing a real project before capturing a thought. Today, unfiled captures go to `99-Resources/Inbox/` — a location that `deadline_scanner` doesn't even scan. After this ships, the Scratch Pad is a first-class project, its items are scannable, and reminders attached to Scratch Pad captures work like any other.

---

## Goals

- Any task (intent), note (capture), or project capture can have a `reminder_date` field.
- Relative inputs ("in 3 months", "in 6 months", "in 1 year", "on YYYY-MM-DD") are resolved to an absolute ISO date at save time.
- Starting 7 days before `reminder_date`, the item appears daily in a new "On your radar" section — visually distinct from the overdue/pressing section.
- On and after `reminder_date`, the item moves to a "Reminder due" section and persists there until the user acts on it.
- The user can **dismiss** (permanent) or **snooze** (pick a new date) any active reminder; both actions write back to the file's frontmatter.
- Reminder state (`reminder_date`, `reminder_dismissed`, `reminder_snoozed_until`) lives in the file's YAML frontmatter AND is rendered as a visible callout in the markdown body so it's readable without parsing headers.
- The Scratch Pad project (`SCRATCH-PAD`) is created automatically at first server start if absent.
- The Scratch Pad cannot be deleted through any API or UI flow.
- The Scratch Pad counts toward the WIP cap like any other project.

---

## Non-Goals

- Reminders on the project page file itself (only tasks and captures).
- Multi-user or collaborative reminder delivery.
- Email, SMS, or any notification channel beyond the existing OS notification system.
- Automatically routing unfiled captures to the Scratch Pad (existing `99-Resources/Inbox/` behavior unchanged).
- A "reminder history" or audit log of past dismissals.
- Changing the WIP cap rules or exempting the Scratch Pad from them.

---

## Success Criteria

1. A task or capture with `reminder_date: 2026-08-01` appears in "On your radar" from 2026-07-25, and in "Reminder due" from 2026-08-01 onward.
2. Snoozing updates `reminder_snoozed_until` in the file and removes the item from all reminder views until the new date.
3. Dismissing updates `reminder_dismissed` in the file and permanently removes the item from all reminder views.
4. On first server start with a fresh vault, `SCRATCH-PAD` is created and visible as a project.
5. Attempting to delete `SCRATCH-PAD` via the API returns HTTP 403.
6. All existing deadline/overdue behavior is unchanged.
