# Mind Journal & 4-Hour Mood Check-In — Low-Level Design

## Architecture

A new single-purpose module **`apps/cli/lib/mind_journal.py`**, mirroring the structure of `new_project_writer.py` (seeding) and `reminder_writer.py` (frontmatter + body writes). `server.py` calls into it; the desktop tray consumes new HTTP endpoints.

```
server start ─► ensure_mind_journal(vault, state)         (mind_journal.py)
                  │  reads vault state JSON flag
                  │  seeds SCRATCH-PAD/MIND-JOURNAL.md if flag absent
                  └► sets mind_journal_seeded: true in state JSON

GET  /api/journal        ─► find_journal() + compute_due()  ► {task, entries, due, next_due, interval_hours, waking}
POST /api/journal/entry  ─► append_entry()                  ► writes body entry + reminder_last_logged
PATCH /api/journal/config─► write_journal_config()          ► updates interval / waking window frontmatter
GET  /api/home (extend)  ─► compute_due()                   ► journal: {due, next_due}

tray poll ─► GET /api/home ─► if journal.due and within waking window ─► native banner + tray item
```

### The journal task file

Seeded at `<vault>/01-Active-Projects/SCRATCH-PAD/MIND-JOURNAL.md`. Written directly (like `ensure_scratch_pad`), bypassing intent-tag validation. Discovered by the `journal: true` frontmatter marker, **not** by filename, so a manual rename does not orphan it.

```markdown
---
id: MIND-JOURNAL
type: C
status: wip
created: 2026-06-03
journal: true
project: SCRATCH-PAD
reminder_interval_hours: 4
reminder_last_logged: 2026-06-03T10:00:00-06:00
waking_start: "08:00"
waking_end: "22:00"
tags: [task, journal]
---

# Mind Journal

A journal for your mind. Every few hours, jot what you're thinking, what you're
doing, and how you feel. Delete this task anytime if you don't want it.

## Entries

### 2026-06-03 10:00 · 😊 happy
**Mind:** clear, excited about the release
**Doing:** writing the journal spec
```

New entries are appended under `## Entries`, newest at the bottom (chronological, matching how a journal reads top-to-bottom). `reminder_last_logged` in frontmatter is the recurrence anchor.

### Due computation (`compute_due`)

```
now            = local now
last           = reminder_last_logged  (fallback: created, then now)
interval       = reminder_interval_hours (default 4)
next_boundary  = last + interval hours
within_window  = waking_start <= now.time() <= waking_end
due            = (now >= next_boundary) AND within_window
next_due       = next_boundary clamped forward to the next waking_start if next_boundary
                 lands outside the waking window
```

A boundary crossed during quiet hours does not fire; `next_due` is reported as the upcoming `waking_start` so the tray and UI show a truthful "next check-in" time.

### Seeding & deletion ("mandatory but deletable")

- `ensure_mind_journal` seeds **only if** the vault state JSON flag `mind_journal_seeded` is absent/false.
- After a successful seed, it sets `mind_journal_seeded: true` in the vault state JSON (same store as `last_focus_prompt`, per the AM/PM focus spec).
- Because the flag persists, deleting the task file does not trigger re-seeding on the next start — the journal is mandatory once, then fully under user control.
- The journal task carries **no** `protected` field; existing delete flows treat it like any task (no 403).

## Constraints

- Python backend; vault is markdown + YAML frontmatter. Reuse `intent_parser` (`parse_frontmatter`, `write_frontmatter`, `_DELETE`) and the atomic `tmp → os.replace` write pattern from `reminder_writer.py`.
- All times are local/timezone-aware ISO timestamps, consistent with `created` (`datetime.now().astimezone()`).
- Waking window is stored as `"HH:MM"` strings; comparison is on local wall-clock time of day only (no date component).
- Mood is a closed enum: `happy | neutral | sad`. Reject anything else.
- Seeding must be non-fatal: any failure logs and the server still starts (matches `ensure_scratch_pad`'s `except: pass` posture, but prefer logging over silent swallow).
- The recurring check-in must never be emitted by `reminder_scanner.scan_vault_reminders` — that scanner keys off `reminder_date`, which the journal task does not set.

## Key Decisions

- **Dedicated module, not a generic recurring engine.** The interval lives on the journal task's frontmatter and is configurable, satisfying "configurable, default 4h" without building reminder-recurrence infrastructure the rest of the app doesn't need (Simplicity First).
- **Discovery by `journal: true` marker, not filename.** Survives rename; one query path. The seed writes `MIND-JOURNAL.md` but nothing depends on that name post-seed.
- **State flag for once-only seeding.** Reusing the existing vault state JSON (home of `last_focus_prompt`) avoids a new persistence mechanism and gives the exact "seed once, respect deletion" semantics.
- **Append-only entries inside the task body.** Chosen over separate capture notes (locked decision): one chronological journal that reads top-to-bottom, no item-list clutter in Scratch Pad.
- **`reminder_last_logged` is the recurrence clock**, advanced on every entry submit. No background scheduler — "due" is computed at request time, like the existing reminder/deadline scanners.
- **Quiet hours via per-journal waking window**, defaulting 08:00–22:00, configurable. A boundary in quiet hours defers to the next `waking_start` rather than firing late at night.

## Out of Scope

- Editing or deleting individual past entries via API.
- Mood analytics, streaks, or visualizations.
- Applying the recurring mechanism to any task other than the Mind Journal.
- Snooze/dismiss semantics for the recurring check-in (it simply re-arms on the next entry or boundary).
