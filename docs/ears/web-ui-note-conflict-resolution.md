# Web UI Note Conflict Resolution — EARS Specifications

> _Backfilled from the as-built `_save_with_mtime` + `ConflictDialog.tsx`._

## Unit 1: Conflict detection on save

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN a note save request omits the file body, THE SYSTEM SHALL reject it with `400` without writing. |
| R-1.2 | WHEN a note save request omits the last-read modification time, THE SYSTEM SHALL reject it with `400` and a reload-and-retry message without writing. |
| R-1.3 | WHEN a note save request carries a non-numeric modification time, THE SYSTEM SHALL reject it with `400` without writing. |
| R-1.4 | WHEN the save target is outside the active vault root, THE SYSTEM SHALL reject it with `403`. |
| R-1.5 | WHEN the save target no longer exists on disk, THE SYSTEM SHALL respond `404`. |
| R-1.6 | WHEN the on-disk modification time differs from the client's last-read time by more than 0.001s, THE SYSTEM SHALL respond `409` with the current on-disk body, the current modification time, and a conflict message, and SHALL NOT overwrite the file. |
| R-1.7 | WHEN the on-disk modification time matches the client's last-read time, THE SYSTEM SHALL write the new body atomically (write-temp, fsync, rename). |

## Unit 2: Atomicity

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL perform the modification-time comparison and the subsequent write within a single critical section so that two concurrent saves starting from the same modification time cannot both succeed. |
| R-2.2 | WHEN two saves race, THE SYSTEM SHALL allow at most one to write and SHALL detect the other as a conflict. |

## Unit 3: Conflict dialog

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN a save returns `409`, THE SYSTEM SHALL present a conflict dialog stating that someone else edited the file and asking which version to keep. |
| R-3.2 | THE SYSTEM SHALL offer three actions: Cancel (abandon the save), Keep mine (override and re-save the user's body), and Show their version (load the current on-disk body for review). |
| R-3.3 | THE SYSTEM SHALL disable the "Show their version" action when no conflict payload is available. |
| R-3.4 | THE SYSTEM SHALL NOT overwrite the on-disk file until the user explicitly chooses Keep mine. |
