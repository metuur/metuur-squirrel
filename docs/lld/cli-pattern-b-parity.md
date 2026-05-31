# CLI Pattern-B Parity — Low-Level Design

## Architecture

```
agent-pack/commands/sq-focus.md          ─── python3 lib/focus_cli.py get|set|clear|history
agent-pack/commands/sq-reminders.md      ─── python3 lib/reminder_scanner.py --vault ...
                                          ─── python3 lib/reminder_writer.py snooze ...
agent-pack/skills/session-start/SKILL.md ─── python3 lib/focus_cli.py checkin
agent-pack/skills/session-end/SKILL.md   ─── python3 lib/focus_cli.py checkout

apps/cli/lib/focus_cli.py  (NEW)
  └── imports: focus_picker, db, config_loader
  └── subcommands: get, set, clear, checkin, checkout, history

apps/cli/lib/reminder_writer.py  (EXTENDED)
  └── adds: argparse CLI entry point with subcommand: snooze

apps/cli/lib/new_project_writer.py  (EXTENDED)
  └── create_project() gains optional `first_intent_filename` param
  └── CLI gains --first-intent-filename flag
```

All scripts share the same vault resolution via `config_loader`.
All DB operations use `db.get_conn()` + `db.init_schema()` — same SQLite file as the web server (WAL mode allows concurrent access).

---

## Module: `focus_cli.py` (new)

Thin orchestrator — no business logic beyond what `focus_picker.py` and `db.py` already provide.

### Subcommands

| Subcommand | Args | Calls | Output |
|---|---|---|---|
| `get` | `--vault PATH` | `focus_picker.get_manual_focus()` | JSON `{today, today_pm, week}` |
| `set` | `--vault PATH --slot today\|today_pm\|week --project SLUG --intent SLUG` | `focus_picker.set_manual_focus()` | `{"ok": true}` or error JSON |
| `clear` | `--vault PATH --slot today\|today_pm\|week` | `focus_picker.clear_manual_focus()` | `{"ok": true}` |
| `checkin` | `--vault PATH --project SLUG --intent SLUG --slot today\|today_pm\|week` | `db.get_conn()` INSERT work_sessions | `{"session_id": N}` |
| `checkout` | `--vault PATH` | `db.get_conn()` UPDATE work_sessions | `{"session_id": N, "duration_minutes": N, "time_invested_minutes": N}` |
| `history` | `--vault PATH [--date YYYY-MM-DD] [--from YYYY-MM-DD --to YYYY-MM-DD]` | `db.get_conn()` SELECT | JSON array of picks + sessions |

Exit codes: `0` success, `1` usage/not-found error. Always emits JSON to stdout so callers can parse with `python3 -c`.

### Checkout detail

Mirrors server.py `api_focus_checkout`:
1. Find latest open session for this vault (checkout_at IS NULL).
2. Set checkout_at = now (UTC ISO).
3. Compute `duration_minutes`.
4. Rewrite `time_invested_minutes` frontmatter on the intent file (same as `_update_time_invested`).

---

## Module: `reminder_writer.py` (extend)

Add a `__main__` block with subcommand `snooze`:

```
python3 lib/reminder_writer.py snooze --note-id ID --until YYYY-MM-DD --vault PATH
```

Resolves the note path via `_find_note(vault, id)` (same logic as server.py), then calls `snooze_reminder(path, until)`.

---

## Module: `new_project_writer.py` (extend)

- `create_project()` gains `first_intent_filename: Optional[str] = None`.
- If `first_intent_filename` is given and non-empty, the intent `.md` file is written as `{first_intent_filename}.md`; otherwise falls back to `{first_intent_tag}.md` (backward compat).
- CLI gains `--first-intent-filename` flag alongside `--first-intent-tag`.
- Validation: `first_intent_filename` must match `^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$`.

---

## Commands updated

### `sq-focus.md`

Replace all `curl` branches with `python3 lib/focus_cli.py` calls. Preserve existing argument surface exactly:

| Old form | New internal call |
|---|---|
| GET (bare) | `focus_cli.py get --vault $VAULT` |
| `today TAG/SLUG` | `focus_cli.py set --vault $VAULT --slot today --project TAG --intent SLUG` |
| `pm TAG/SLUG` | `focus_cli.py set --vault $VAULT --slot today_pm --project TAG --intent SLUG` |
| `week TAG/SLUG` | `focus_cli.py set --vault $VAULT --slot week --project TAG --intent SLUG` |
| `today --clear` | `focus_cli.py clear --vault $VAULT --slot today` |
| `pm --clear` | `focus_cli.py clear --vault $VAULT --slot today_pm` |
| `week --clear` | `focus_cli.py clear --vault $VAULT --slot week` |
| `history [DATE]` | `focus_cli.py history --vault $VAULT [--date DATE]` |

New syntax additions (additive):
- `/sq-focus pm TAG/SLUG` — sets `today_pm` slot
- `/sq-focus pm --clear` — clears `today_pm` slot
- `/sq-focus history [YYYY-MM-DD]` — shows picks + sessions (defaults to today)

GET display gains a third line: `Today PM: {project} / {intent}` (or `(none)`).

### `session-start/SKILL.md`

After Step 5 (state.json written), add **Step 5.5 — Record checkin**:

```bash
python3 lib/focus_cli.py checkin \
    --vault "$VAULT" \
    --project "<PROJECT-TAG>" \
    --intent "<INTENT-TAG>" \
    --slot today
```

Non-fatal: if the script exits non-zero, log a one-line warning and continue.

### `session-end/SKILL.md`

After Step 12 (state.json updated), add **Step 12.5 — Record checkout**:

```bash
python3 lib/focus_cli.py checkout --vault "$VAULT"
```

Parse the JSON output. Append to the Step 13 confirmation:
```
⏱ Sesión: {duration_minutes} min   |   Total invertido: {time_invested_minutes} min
```

Non-fatal: if no open session found, skip silently.

### `sq-reminders.md` (new command)

```
/sq-reminders                          → list
/sq-reminders snooze ID YYYY-MM-DD    → snooze
```

**List:** calls `python3 lib/reminder_scanner.py --vault $VAULT`, renders approaching + active buckets.

**Snooze:** calls `python3 lib/reminder_writer.py snooze --note-id ID --until DATE --vault $VAULT`.

---

## Key Decisions

- **No HTTP in skills** — eliminates the fragile "is the server running?" check from all agent-pack code.
- **`focus_cli.py` as a new file, not modifying `focus_picker.py`** — `focus_picker.py` is a library; adding argparse to it conflates responsibilities. A thin orchestrator is cleaner and matches the `status_aggregator` / `switch_tracker` pattern.
- **`today_pm` exposed as `/sq-focus pm`** (not `today pm`) — simpler to type and parse; consistent with slot naming.
- **Checkin/checkout non-fatal in skills** — session workflow must not break if the DB is temporarily locked or a first-session state lacks an open session.
- **`first_intent_filename` defaults to tag** — zero breaking change for all existing CLI and API callers.

## Out of Scope

- Recalculate time, notification center, reminder dismiss (see Non-Goals in HLD).
- Any changes to the Web UI or server.py (those are already shipped).
- Interactive fuzzy-picker for reminder snooze (non-interactive `ID DATE` form only).
