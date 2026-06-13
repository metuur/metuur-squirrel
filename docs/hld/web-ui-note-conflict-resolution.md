# Web UI Note Conflict Resolution — High-Level Design

> _Backfilled from the as-built `apps/backend/app/src/components/ConflictDialog.tsx`
> and the `_save_with_mtime` save path in `apps/backend/server.py`._

## Overview

A Squirrel vault is edited from many surfaces at once — the Web UI, the desktop
popup, the CLI, the coding agent, and Obsidian. Two of them can hold the same note
open; without a guard, the slower save silently clobbers the faster one and the
user loses edits with no warning.

This change adds **optimistic-concurrency conflict detection** on note saves: the
client sends the file modification time it last read; the backend rejects the save
with `409` if the file on disk changed since then, returning the current on-disk
body so the Web UI can present a **conflict dialog** asking the user to keep theirs
or pull in the newer version before overwriting.

## Stakeholders & Impact

- **User editing from two places:** instead of a silent overwrite, gets a clear
  "Someone else just edited this" dialog and decides which version wins.
- **Backend save path:** gains a single critical section around the
  check-then-write so concurrent in-flight saves can't both pass the check.
- **Every note editor in the Web UI:** consumes the `409` conflict payload and
  shows the dialog.

## Goals

- Detect when a note changed on disk since the client loaded it, and refuse to
  overwrite silently.
- Make the check-and-write atomic so two concurrent saves cannot both win.
- Present the user a clear choice: cancel, force-keep-mine, or view-theirs before
  overwriting.
- Never lose an edit without the user explicitly choosing to discard it.

## Non-Goals

- No automatic three-way merge — the user picks a whole version, the app does not
  merge line-by-line.
- No real-time collaborative editing or presence.
- No conflict handling for non-note resources (projects' structured writes,
  Post-its) in this feature.
- No version history/undo beyond showing the current on-disk body.

## Success Criteria

1. Saving a note whose on-disk mtime differs from the client's last-read mtime
   returns `409` with the current on-disk body and mtime — the save does not
   overwrite.
2. Two concurrent saves that both started from the same mtime cannot both succeed;
   the second is detected as a conflict.
3. On a `409`, the Web UI shows a dialog offering Cancel, Keep mine, and Show their
   version.
4. A save with no mtime, or a malformed mtime, is rejected with a `400` and a
   reload-and-retry message rather than overwriting.
5. A normal save (matching mtime) writes atomically and succeeds.
