# Web UI Note Conflict Resolution — Low-Level Design

> _Backfilled from the as-built `_save_with_mtime` + `ConflictDialog.tsx`._

## Architecture

Optimistic concurrency keyed on file mtime. The client round-trips the mtime it
last read; the backend compares it against the live on-disk mtime inside a lock,
and on mismatch replies `409` with the current body instead of writing.

```
[note editor]  body + mtime (last-read)
   └ save → POST (note save)
        backend: _save_with_mtime(target, vault_root, payload)
          with _NOTE_SAVE_LOCK:                     # one critical section
            current = target.stat().st_mtime
            if |client_mtime - current| > 0.001:
               → 409 { current_body, current_mtime, message }   (no write)
            else atomic_write_text(target, body)
   └ on 409 → ConflictDialog(open, payload={current_body, current_mtime})
        Cancel            → onCancel
        Keep mine         → onForceMine  (re-save, overriding)
        Show their version→ onTakeTheirs (load current_body for review)
```

## Backend contract (`_save_with_mtime`, `apps/backend/server.py`)

- Rejects a target outside the vault root → `403`.
- Requires `body` → else `400` ("Missing the note body.").
- Requires `mtime` → else `400` ("Missing the file timestamp. Reload and try
  again.").
- Acquires `_NOTE_SAVE_LOCK` (module-level) so the stat-compare and the write are
  one critical section — without it, two threaded in-flight saves could both pass
  the check and the slower one would silently overwrite the faster.
- Inside the lock:
  - `current_mtime = target.stat().st_mtime`; missing file → `404`.
  - If `abs(float(client_mtime) - current_mtime) > 0.001` → respond `409` with
    `{ current_body, current_mtime, message }` (the current on-disk text), then
    short-circuit via `_ResponseSent` so no write happens.
  - A non-numeric client mtime → `400` ("The file timestamp looks wrong…").
  - Otherwise `atomic_write_text(target, body)` (write-temp, fsync, rename).
- The `0.001`s tolerance absorbs float/filesystem mtime precision jitter.

## Frontend contract (`ConflictDialog.tsx`)

Props: `{ open, payload: { current_body, current_mtime } | null, onTakeTheirs,
onForceMine, onCancel }`. Renders a small `Modal`:

- Title "Someone else just edited this", subtitle "Pick which version to keep",
  warning icon.
- Body: a warning callout explaining a newer version is already on disk.
- Footer actions:
  - **Cancel** → `onCancel`.
  - **Keep mine** → `onForceMine` (the editor re-saves, overriding the conflict —
    typically by re-reading the now-current mtime and saving the user's body).
  - **Show their version** → `onTakeTheirs`, disabled when `payload` is null (loads
    `current_body` for the user to review before overwriting).

## Constraints

- The check and write MUST be atomic (single lock) — correctness of the whole
  feature depends on it.
- The backend returns the full current body on conflict so the UI can show "their
  version" without a second request.
- Conflict resolution is whole-version (keep mine / take theirs), never an
  automatic merge.

## Key Decisions

- **mtime optimistic concurrency over locking files** — cheap, stateless, works
  across every writer (none of which coordinate), and only intervenes on an actual
  divergence.
- **Server-side lock around check+write** — defends against the backend's own
  threaded concurrency, which a per-client mtime check alone cannot.
- **Return the current body in the 409** — lets the dialog offer "show their
  version" immediately, no extra round-trip.

## Out of Scope

- Three-way/line merge, real-time collaboration/presence, version history, and
  conflict handling for non-note resources.
