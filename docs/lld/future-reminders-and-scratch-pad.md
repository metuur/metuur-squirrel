# Future Reminders & Scratch Pad — Low-Level Design

## Architecture

### New frontmatter fields

Three new optional fields added to the YAML header of intent and capture files:

```yaml
reminder_date: YYYY-MM-DD          # when to surface the item
reminder_snoozed_until: YYYY-MM-DD # set on snooze; clears when date passes
reminder_dismissed: YYYY-MM-DD     # set on dismiss; permanently suppresses
```

All three are parsed by `intent_parser.py` (already reads arbitrary frontmatter keys). No schema migration needed — files without these fields are silently unaffected.

The reminder date is also rendered as a visible callout block in the markdown body when set, immediately below the title heading:

```markdown
> 📅 **Reminder:** 2026-08-01
```

This is written at creation/edit time and updated in-place when snooze changes the date, or removed when dismissed.

### Relative date resolution

Relative inputs are resolved to absolute ISO dates at the API boundary (in `server.py`) before writing to disk:
- `"in 1 month"` → `today + relativedelta(months=1)`
- `"in 3 months"` → `today + relativedelta(months=3)`
- `"in 6 months"` → `today + relativedelta(months=6)`
- `"in 1 year"` → `today + relativedelta(years=1)`
- `"YYYY-MM-DD"` → passed through verbatim

Uses Python's `dateutil.relativedelta` (already available) or `datetime` arithmetic.

### New lib module: `reminder_scanner.py`

Mirrors `deadline_scanner.py` in structure. Scans `01-Active-Projects` and `03-Areas` for files with `reminder_date` set.

Classification logic:

| Condition | State |
|-----------|-------|
| `reminder_dismissed` is set | `dismissed` — excluded from all output |
| `reminder_snoozed_until` is set and in the future | `snoozed` — excluded until that date |
| `reminder_date` in the past or today, no suppression | `reminder_active` |
| `reminder_date` within 7 calendar days, no suppression | `reminder_approaching` |

Returns two lists: `reminder_approaching[]` and `reminder_active[]`. Each entry carries: `id`, `title`, `path`, `reminder_date`, `project`.

### API changes (`server.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/reminders` | GET | Returns `{ approaching: [...], active: [...] }` |
| `/api/reminder/<id>/dismiss` | PATCH | Writes `reminder_dismissed: today` to frontmatter + removes body callout |
| `/api/reminder/<id>/snooze` | PATCH | Writes `reminder_snoozed_until: <date>` to frontmatter + updates body callout |
| `/api/home` | GET (extend) | Adds `reminders: { approaching_count, active_count }` to existing response |
| `/api/intents` (create) | POST (extend) | Accepts optional `reminder_date` (absolute or relative string) |
| `/api/captures` (create) | POST (extend) | Accepts optional `reminder_date` |

The PATCH endpoints do atomic frontmatter rewrite: read file → parse YAML block → update key → reassemble → `os.replace()` (same pattern used by intent writer, line 707–709 of `server.py`).

### Tauri tray changes (`tray_alerts.rs`)

New struct `ReminderAlert` (parallel to `Alert`). The existing `start_polling()` loop at line 216 is extended to:
1. Also call `GET /api/reminders` after each `/api/home` poll.
2. Pass `reminder_approaching[]` and `reminder_active[]` to a new `tray::update_reminders()` call.
3. For `reminder_active` items: fire OS notifications on the same `NOTIF_INTERVAL`/`ITEM_COOLDOWN`/`MAX_DIALOGS_PER_DAY` guards already in place.
4. For `reminder_approaching` items: shown in tray only, no OS notification.

Tray menu gets two new sections (below the existing "PRESSING NOW"):
- **"On your radar"** — `reminder_approaching` items (shown up to 7 days before)
- **"Reminder due"** — `reminder_active` items (shown until dismissed/snoozed)

Desktop web UI gets a new `RemindersWidget` component (mirrors `DeadlinesWidget`) with dismiss and snooze controls.

### Scratch Pad initialization

New function `ensure_scratch_pad(vault_path)` in `new_project_writer.py`:

```python
def ensure_scratch_pad(vault_path: Path) -> None:
    project_dir = vault_path / "01-Active-Projects" / "SCRATCH-PAD"
    if project_dir.exists():
        return
    create_project(
        tag="SCRATCH-PAD",
        type="C",
        description="Default project for quick ideas, reminders, and captures.",
        force=True,
    )
```

Called once at server startup (`server.py` init block), before the first HTTP request is served.

The Scratch Pad project page gets one additional frontmatter field:

```yaml
protected: true
```

### Delete guard

New check in the project delete handler (`server.py`): read project page frontmatter; if `protected: true`, return HTTP 403 with body `{"error": "PROJECT_PROTECTED"}`. No other project currently has `protected: true`.

---

## Constraints

- File system is the only storage layer — no database.
- Atomic writes via temp file + `os.replace()` (existing pattern).
- All date parsing must handle both `YYYY-MM-DD` strings and `datetime.date` objects from `python-frontmatter` (which sometimes returns native types).
- `dateutil` is available in the backend Python environment (verify in `pyproject.toml`; add if absent).
- The `reminder_scanner` must skip files with `status: done/completed/archived` (same as `deadline_scanner`).

---

## Key Decisions

**Reminder state in frontmatter, not a sidecar file.** A sidecar JSON would require a separate read/write cycle and could desync from the file. Frontmatter keeps reminder state co-located with the item and visible in raw editors.

**Body callout rendered at write time, not at display time.** Rendering in the API/UI would require injecting HTML into markdown output on every request. Writing once to the file keeps the render path unchanged.

**Separate scanner, not extending `deadline_scanner`.** Mixing reminder and deadline classification in one function would couple two independent concepts and break the existing EARS spec (ATTN-001). A new `reminder_scanner.py` is a clean addition.

**`ensure_scratch_pad` called at server startup, not on first capture.** D7 specifies "first time the user opens the app." Server startup is the closest reliable hook for this in the current architecture.

**`type: C`** for the Scratch Pad (experimental). A/B/C are the only valid types; C ("experimental") is the least semantically loaded choice for a utility container.

---

## Out of Scope

- Reminder support on project page files (`<TAG>.md` itself).
- Any notification channel other than OS native notifications.
- Changing the `99-Resources/Inbox/` routing for unfiled captures.
- UI for bulk-editing reminder dates across multiple items.
- Reminder recurrence (e.g., "remind me every month").
