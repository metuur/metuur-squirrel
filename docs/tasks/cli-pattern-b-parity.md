# CLI Pattern-B Parity — Tasks

## Unit 2: focus_cli.py — get / set / clear

- [x] 2.1 Create `apps/cli/lib/focus_cli.py` with `get`, `set`, `clear` subcommands (est: ~30m)
  - acceptance: R-2.1, R-2.2, R-2.3, R-2.4, R-2.5, R-2.6 — standalone Python 3.9+ script; `get` calls `focus_picker.get_manual_focus` and prints JSON; `set` calls `set_manual_focus`; `clear` calls `clear_manual_focus`; `IntentNotFound` → exit 1 with JSON error; always exit 0/1 with JSON stdout
  - verify: `python3 apps/cli/lib/focus_cli.py get --vault $VAULT` prints 3-key JSON; `set` and `clear` return `{"ok": true}`

## Unit 3: focus_cli.py — checkin / checkout

- [x] 3.1 Add `checkin` and `checkout` subcommands to `focus_cli.py` (deps: 2.1, est: ~25m)
  - acceptance: R-3.1, R-3.2, R-3.3, R-3.4 — `checkin` inserts into `work_sessions`; `checkout` closes open session, computes duration, rewrites `time_invested_minutes` frontmatter; auto-closes stale open session before new checkin; `no_open_session` → exit 1
  - verify: `checkin` → `{"session_id": N}`; `checkout` → `{"session_id": N, "duration_minutes": N, "time_invested_minutes": N}`; second `checkin` without `checkout` auto-closes first

## Unit 4: focus_cli.py — history

- [x] 4.1 Add `history` subcommand to `focus_cli.py` (deps: 2.1, est: ~15m)
  - acceptance: R-4.1, R-4.2 — queries `focus_picks` and `work_sessions` for given date; defaults to today when `--date` omitted
  - verify: `python3 apps/cli/lib/focus_cli.py history --vault $VAULT` prints JSON with `picks` and `sessions` arrays

## Unit 1: Pattern B enforcement (sq-focus migration)

- [x] 1.1 Rewrite `agent-pack/commands/sq-focus.md` to use `focus_cli.py` (deps: 2.1, 3.1, 4.1, est: ~20m)
  - acceptance: R-1.1 through R-1.10 — all curl calls replaced; vault resolved via `config_loader`; GET shows 3 lines including `Today PM:`; `pm` slot sets `today_pm`; `history` subcommand renders table; no `curl` in file after change
  - verify: `/sq-focus` with backend offline still returns focus data; `grep curl agent-pack/commands/sq-focus.md` returns nothing

## Unit 5: session-start — checkin

- [x] 5.1 Add Step 5.5 to `agent-pack/skills/session-start/SKILL.md` (deps: 3.1, est: ~10m)
  - acceptance: R-5.1, R-5.2, R-5.3 — after state.json write, calls `focus_cli.py checkin`; failure logs warning and continues; loading note display is never blocked
  - verify: Step 5.5 block present in SKILL.md; error path documented as non-fatal

## Unit 6: session-end — checkout

- [x] 6.1 Add Step 12.5 to `agent-pack/skills/session-end/SKILL.md` (deps: 3.1, est: ~10m)
  - acceptance: R-6.1, R-6.2, R-6.3, R-6.4 — after state.json write, calls `focus_cli.py checkout`; success appends duration line to Step 13 output; `no_open_session` → silent skip; other errors → one-line warning
  - verify: Step 12.5 block present; Step 13 template includes `⏱` line; error paths documented

## Unit 8: sq-reminders — snooze

- [x] 8.1 Add `__main__` entry point with `snooze` subcommand to `apps/cli/lib/reminder_writer.py` (est: ~20m)
  - acceptance: R-8.2, R-8.3, R-8.4, R-8.5 — `python3 reminder_writer.py snooze --note-id ID --until DATE --vault PATH`; resolves note via rglob; calls `snooze_reminder`; prints JSON; not-found → exit 1; invalid date → exit 1
  - verify: `python3 reminder_writer.py snooze --note-id FAKE --until 2099-01-01 --vault $VAULT` prints `{"error": "not_found", ...}`

## Unit 7: sq-reminders — list

- [x] 7.1 Create `agent-pack/commands/sq-reminders.md` with list and snooze commands (deps: 8.1, est: ~15m)
  - acceptance: R-7.1, R-7.2, R-7.3, R-7.4, R-8.1 — `/sq-reminders` calls `reminder_scanner.py` and renders Approaching + Active sections; empty → "No reminders right now."; vault error → exit 1; `/sq-reminders snooze ID DATE` calls `reminder_writer.py snooze`
  - verify: file exists at `agent-pack/commands/sq-reminders.md`; list and snooze branches both documented with vault resolution

## Unit 9: new_project_writer — filename independence

- [x] 9.1 Add `first_intent_filename` param to `new_project_writer.py` (est: ~20m)
  - acceptance: R-9.1, R-9.2, R-9.3, R-9.4, R-9.5 — `create_project()` accepts `first_intent_filename=None`; writes `{filename}.md` when set, else `{tag}.md`; validates against `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`; raises `INVALID_INTENT_FILENAME`; `--first-intent-filename` flag added to CLI
  - verify: `python3 new_project_writer.py --tag TEST --tipo C --first-intent-tag TEST-SETUP-001 --first-intent-filename MY-CUSTOM-FILE` creates `MY-CUSTOM-FILE.md`; omitting flag falls back to tag name

- [x] 9.2 Update `agent-pack/commands/sq-new-project.md` to expose `--first-intent-filename` (deps: 9.1, est: ~10m)
  - acceptance: R-9.5 — command docs show `--first-intent-filename` as optional flag alongside `--first-intent-tag`; skill derives filename from title using UPPERCASE-DASH logic when not provided
  - verify: flag documented in usage and examples sections
