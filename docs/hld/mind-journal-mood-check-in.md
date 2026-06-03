# Mind Journal & 4-Hour Mood Check-In — High-Level Design

## Overview

A **Mind Journal** is a single, auto-seeded task living inside the Scratch Pad project. It exists to give the user a low-friction place to externalize what their mind is doing throughout the day. A **recurring check-in reminder** (default every 4 hours, configurable, only during waking hours) brings the journal back to attention and prompts two questions — *"What is your mind thinking right now?"* and *"What are you doing right now?"* — together with a mood (happy / neutral / sad). Each answer is appended as a timestamped, mood-tagged entry inside the journal task, building a running log of mood and activity over the day.

The journal task is **mandatory** in the sense that the system seeds it automatically the first time a vault has none — the user never has to create it. But unlike the Scratch Pad project itself (which is `protected: true` and cannot be deleted), the journal task **can be deleted** like any other task. Once deleted, it is not silently resurrected.

---

## Stakeholders & Impact

**Primary user (sole user).** This is an ADHD-focused tool. Today the vault tracks projects, intents, deadlines, and one-shot future reminders, but there is no rhythm for capturing transient mental state — what the user is thinking, what they are doing, and how they feel while doing it. That state is exactly what slips away. After this ships, the user gets a gentle, repeating nudge (during waking hours only) that takes seconds to answer, and over time accumulates a readable mood-and-activity log they can scroll through to spot patterns.

**Existing reminder system.** The one-shot `reminder_date` mechanism (dismiss / snooze, "On your radar" / "Reminder due") is untouched. The recurring journal check-in is a separate, parallel mechanism and must not appear in the one-shot reminder buckets.

**Desktop tray & notifications.** A new "Mind Journal" check-in surfaces in the tray and as a native notification banner when due, riding the existing notification cadence guards — but suppressed entirely outside the configured waking window.

---

## Goals

- The system seeds exactly one Mind Journal task in the Scratch Pad project the first time a vault lacks one, with no user action.
- The journal task is deletable through normal task flows; once deleted it is **not** automatically recreated.
- A recurring check-in becomes "due" every `reminder_interval_hours` (default 4) after the last logged entry, but only while the current local time is inside the configured waking window.
- The interval and the waking window are configurable.
- When the user answers the two prompts and picks a mood, the answer is appended as a timestamped, mood-tagged entry inside the journal task body, and the recurrence clock resets.
- Mood is recorded on a three-point scale: happy, neutral, sad.
- A due check-in surfaces in the desktop tray and fires a native notification on the same cadence guards as pressing items — never during quiet hours.

## Non-Goals

- Making the journal task protected/undeletable — it must remain deletable.
- A generic recurring-reminder engine for arbitrary tasks; this recurrence applies only to the Mind Journal.
- Charts, analytics, or mood trend visualizations (the appended log is the only output for now).
- Changing or extending the existing one-shot `reminder_date` / dismiss / snooze behavior.
- Multiple journals per vault, or journals outside the Scratch Pad project.
- Notification channels beyond the existing OS tray/native banner system.
- Backfilling or editing past entries through the API (entries are append-only).

## Success Criteria

1. On first server start against a vault with no journal, a Mind Journal task appears inside the Scratch Pad project.
2. Deleting the journal task and restarting the server does **not** recreate it.
3. With interval = 4h and the last entry logged at 10:00, the check-in reads "not due" at 13:00 and "due" at 14:00 (assuming 14:00 is within the waking window).
4. If a 4-hour boundary falls at 03:00 (outside the waking window), no notification fires; the check-in surfaces at the start of the next waking window instead.
5. Submitting an entry with mood "happy", mind text, and doing text appends a timestamped entry to the journal body and resets "due" to false.
6. The existing one-shot reminder buckets ("On your radar" / "Reminder due") never contain the Mind Journal task.
