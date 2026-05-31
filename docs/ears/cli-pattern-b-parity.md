# CLI Pattern-B Parity — EARS Specifications

## Unit 1: Pattern B enforcement (sq-focus migration)

| ID | EARS statement |
|---|---|
| R-1.1 | THE SYSTEM SHALL resolve the active vault using `config_loader` in all CLI focus operations, never via HTTP cookie. |
| R-1.2 | WHEN `/sq-focus` is invoked, THE SYSTEM SHALL call `python3 lib/focus_cli.py get --vault $VAULT` and display three lines: `Today:`, `Today PM:`, `This week:` (each `(none)` when the slot is unset). |
| R-1.3 | WHEN `/sq-focus today TAG/SLUG` is invoked, THE SYSTEM SHALL call `focus_cli.py set --vault $VAULT --slot today --project TAG --intent SLUG`. |
| R-1.4 | WHEN `/sq-focus pm TAG/SLUG` is invoked, THE SYSTEM SHALL call `focus_cli.py set --vault $VAULT --slot today_pm --project TAG --intent SLUG`. |
| R-1.5 | WHEN `/sq-focus week TAG/SLUG` is invoked, THE SYSTEM SHALL call `focus_cli.py set --vault $VAULT --slot week --project TAG --intent SLUG`. |
| R-1.6 | WHEN `/sq-focus today --clear` is invoked, THE SYSTEM SHALL call `focus_cli.py clear --vault $VAULT --slot today`. |
| R-1.7 | WHEN `/sq-focus pm --clear` is invoked, THE SYSTEM SHALL call `focus_cli.py clear --vault $VAULT --slot today_pm`. |
| R-1.8 | WHEN `/sq-focus week --clear` is invoked, THE SYSTEM SHALL call `focus_cli.py clear --vault $VAULT --slot week`. |
| R-1.9 | IF `focus_cli.py` exits non-zero, THE SYSTEM SHALL print the stderr output and exit with code 1. |
| R-1.10 | THE SYSTEM SHALL NOT contain any `curl` call in `sq-focus.md` after this change. |

## Unit 2: focus_cli.py — get / set / clear

| ID | EARS statement |
|---|---|
| R-2.1 | THE SYSTEM SHALL implement `focus_cli.py` as a standalone Python 3.9+ script in `apps/cli/lib/`. |
| R-2.2 | WHEN `focus_cli.py get` is called, THE SYSTEM SHALL call `focus_picker.get_manual_focus(vault)` and print JSON `{"today": …, "today_pm": …, "week": …}` to stdout. |
| R-2.3 | WHEN `focus_cli.py set --slot S --project P --intent I` is called, THE SYSTEM SHALL call `focus_picker.set_manual_focus(vault, S, P, I)`. |
| R-2.4 | WHEN `focus_picker.set_manual_focus` raises `IntentNotFound`, THE SYSTEM SHALL print `{"error": "intent_not_found", "slug": "P/I"}` to stdout and exit 1. |
| R-2.5 | WHEN `focus_cli.py clear --slot S` is called, THE SYSTEM SHALL call `focus_picker.clear_manual_focus(vault, S)`. |
| R-2.6 | THE SYSTEM SHALL exit 0 on success and 1 on any error, always emitting JSON to stdout. |

## Unit 3: focus_cli.py — checkin / checkout

| ID | EARS statement |
|---|---|
| R-3.1 | WHEN `focus_cli.py checkin --project P --intent I --slot S` is called, THE SYSTEM SHALL insert a row into `work_sessions` (via `db.get_conn()`) with `checkin_at = now(UTC)` and print `{"session_id": N}`. |
| R-3.2 | WHEN `focus_cli.py checkout` is called, THE SYSTEM SHALL find the latest open session for the vault (checkout_at IS NULL), set `checkout_at = now(UTC)`, compute `duration_minutes`, rewrite `time_invested_minutes` frontmatter on the intent file, and print `{"session_id": N, "duration_minutes": N, "time_invested_minutes": N}`. |
| R-3.3 | IF no open session exists when `checkout` is called, THE SYSTEM SHALL print `{"error": "no_open_session"}` and exit 1. |
| R-3.4 | WHEN `focus_cli.py checkin` is called and a session is already open for the vault, THE SYSTEM SHALL auto-close it before opening a new one (same behaviour as server.py startup cleanup). |

## Unit 4: focus_cli.py — history

| ID | EARS statement |
|---|---|
| R-4.1 | WHEN `focus_cli.py history --date YYYY-MM-DD` is called, THE SYSTEM SHALL query `focus_picks` and `work_sessions` for that date and print JSON `{"picks": […], "sessions": […]}`. |
| R-4.2 | IF `--date` is omitted, THE SYSTEM SHALL default to today's local date. |
| R-4.3 | WHEN `/sq-focus history [DATE]` is invoked, THE SYSTEM SHALL call `focus_cli.py history` and render picks and sessions as a human-readable table. |

## Unit 5: session-start — checkin

| ID | EARS statement |
|---|---|
| R-5.1 | WHEN `session-start` completes Step 5 (state.json written), THE SYSTEM SHALL call `python3 lib/focus_cli.py checkin --vault $VAULT --project $PROJECT --intent $INTENT --slot today`. |
| R-5.2 | IF `focus_cli.py checkin` exits non-zero, THE SYSTEM SHALL log a one-line warning and continue the session-start workflow without interruption. |
| R-5.3 | THE SYSTEM SHALL NOT block or abort the loading note display due to a checkin failure. |

## Unit 6: session-end — checkout

| ID | EARS statement |
|---|---|
| R-6.1 | WHEN `session-end` completes Step 12 (state.json updated), THE SYSTEM SHALL call `python3 lib/focus_cli.py checkout --vault $VAULT`. |
| R-6.2 | WHEN checkout succeeds, THE SYSTEM SHALL append `⏱ Sesión: {duration_minutes} min | Total invertido: {time_invested_minutes} min` to the Step 13 confirmation output. |
| R-6.3 | IF `focus_cli.py checkout` returns `no_open_session`, THE SYSTEM SHALL skip silently (no user-visible message). |
| R-6.4 | IF `focus_cli.py checkout` exits non-zero for any other reason, THE SYSTEM SHALL show a one-line warning and complete the shutdown note normally. |

## Unit 7: sq-reminders — list

| ID | EARS statement |
|---|---|
| R-7.1 | THE SYSTEM SHALL provide a `/sq-reminders` command in `agent-pack/commands/`. |
| R-7.2 | WHEN `/sq-reminders` is invoked without arguments, THE SYSTEM SHALL call `python3 lib/reminder_scanner.py --vault $VAULT` and render two sections: **Approaching** and **Active**, each as a numbered list with id, title, and date. |
| R-7.3 | IF both sections are empty, THE SYSTEM SHALL print `No reminders right now.` |
| R-7.4 | WHERE the vault cannot be resolved, THE SYSTEM SHALL print an error and exit 1. |

## Unit 8: sq-reminders — snooze

| ID | EARS statement |
|---|---|
| R-8.1 | WHEN `/sq-reminders snooze ID YYYY-MM-DD` is invoked, THE SYSTEM SHALL call `python3 lib/reminder_writer.py snooze --note-id ID --until DATE --vault $VAULT`. |
| R-8.2 | THE SYSTEM SHALL add a `--main` entry point to `reminder_writer.py` that accepts subcommand `snooze` with `--note-id`, `--until`, and `--vault` arguments. |
| R-8.3 | WHEN `reminder_writer.py snooze` is called, THE SYSTEM SHALL resolve the note path via vault rglob, call `snooze_reminder(path, until)`, and print `{"snoozed": true, "id": ID, "until": DATE}`. |
| R-8.4 | IF the note ID is not found, THE SYSTEM SHALL print `{"error": "not_found", "id": ID}` and exit 1. |
| R-8.5 | IF `YYYY-MM-DD` fails ISO date validation, THE SYSTEM SHALL print `{"error": "invalid_date"}` and exit 1. |

## Unit 9: new_project_writer — filename independence

| ID | EARS statement |
|---|---|
| R-9.1 | THE SYSTEM SHALL add `first_intent_filename: Optional[str] = None` to `create_project()` in `new_project_writer.py`. |
| R-9.2 | WHEN `first_intent_filename` is provided and non-empty, THE SYSTEM SHALL write the intent file as `{first_intent_filename}.md` instead of `{first_intent_tag}.md`. |
| R-9.3 | IF `first_intent_filename` is None or empty, THE SYSTEM SHALL fall back to `{first_intent_tag}.md` (backward-compatible default). |
| R-9.4 | WHEN `first_intent_filename` is provided, THE SYSTEM SHALL validate it against `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$` and raise `NewProjectError(code="INVALID_INTENT_FILENAME")` on failure. |
| R-9.5 | THE SYSTEM SHALL add `--first-intent-filename` to the `new_project_writer.py` CLI and to `sq-new-project.md`. |
