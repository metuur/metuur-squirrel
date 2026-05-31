# CLI Pattern-B Parity — High-Level Design

## Overview

The Squirrel agent-pack currently has two call patterns: **Pattern A** (curl HTTP calls to the running backend) used by `sq-focus`, and **Pattern B** (direct Python lib calls, no server required) used by `session-start` / `session-end`. This feature enforces Pattern B everywhere, migrates `sq-focus` off curl, and closes the five capability gaps where the CLI has no equivalent for Web UI features: PM focus slot, focus history, work-session tracking (checkin/checkout), reminder management (list + snooze), and intent filename independence.

## Stakeholders & Impact

**Primary user:** the developer running CLI skills from Claude Code sessions.

**Current pain:**
- `sq-focus` breaks silently or with a confusing error if the backend is not running.
- `/sq-start` and `/sq-end` do not record work sessions to the DB — time tracking only works via the Web UI.
- No CLI command exists to list or snooze reminders.
- The PM focus slot (`today_pm`) is invisible from the CLI.
- Two intents in the same project cannot share a tag because the tag doubles as the filename in the CLI flow.

**After this ships:**
- All CLI skills call Python libs directly; the backend server is never a dependency for core workflow.
- Work sessions are recorded identically whether the user works from CLI or Web UI.
- The CLI surfaces reminders (list + snooze) so the daemon isn't a silent black box.
- PM focus is a first-class CLI concept.
- Intent filenames and tags are independent everywhere (Web UI + CLI).

**Secondary consumer:** the Web UI — reads the same SQLite DB, so sessions written by the CLI appear immediately in the Web UI's history and time-invested views.

## Goals

- One canonical Python lib per operation; no duplicated logic between HTTP handlers and CLI scripts.
- `sq-focus`, `session-start`, `session-end`, and the new `sq-reminders` all reach parity with the Web UI feature set.
- No regression: existing `sq-focus` argument syntax is preserved (additive changes only).

## Non-Goals

- Recalculate time (`POST /api/focus/recalculate`) — deferred.
- Notification center — deferred.
- Reminder dismiss — deferred.
- Building a full CLI REPL or interactive TUI.

## Success Criteria

- `sq-focus` works identically whether the backend is running or not.
- A `focus_cli.py` script exists that drives all focus + session operations.
- `reminder_scanner.py` and `reminder_writer.py` are callable from the CLI for list/snooze.
- `session-start` writes a checkin row; `session-end` writes a checkout row and surfaces duration.
- `sq-reminders` lists approaching and active reminders and accepts a snooze command.
- `new_project_writer.py` accepts a separate `first_intent_filename` parameter.
