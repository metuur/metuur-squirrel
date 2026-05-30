# AM/PM Focus Slots & Time Tracking — Low-Level Design

## Architecture

### Layer 1 — State (frontmatter tokens)

Unchanged token mechanism from `manual-focus-pick`. Option B: keep `"today"` as AM, add `"today_pm"` as a new independent slot.

| Slot name | Frontmatter key | Token format | Example |
|-----------|----------------|--------------|---------|
| `today` | `focus_today` | `YYYY-MM-DD` | `2026-05-30` |
| `today_pm` | `focus_today_pm` | `YYYY-MM-DD-PM` | `2026-05-30-PM` |
| `week` | `focus_week` | `GGGG-Www` | `2026-W22` |

New derived field (written on checkout only):

| Frontmatter key | Type | Semantics |
|----------------|------|-----------|
| `time_invested_minutes` | integer | Cumulative total from SQLite `work_sessions`; SQLite wins on conflict |

**Changes in `focus_picker.py`:**
- `_token_now(slot)` — add `"today_pm"` branch: `n.strftime("%Y-%m-%d-PM")`
- `_slot_key(slot)` — add `"today_pm"` → `"focus_today_pm"`
- `set_manual_focus(slot, ...)` — strip-pass only removes `_slot_key(slot)` from other files; AM and PM keys are never co-cleared
- `get_manual_focus()` — return dict with all three slots; `today_pm` returns `None` if not set or expired

### Layer 2 — History (SQLite)

Database path: `Path(state_dir()) / "squirrel.db"` where `state_dir()` comes from `config_loader.py:78`.

**New module: `apps/cli/lib/db.py`**

```python
def get_conn() -> sqlite3.Connection:
    # Opens a new connection per call. Caller is responsible for closing.
    # WAL mode enables concurrent reads from ThreadingMixIn server.

def init_schema(conn):
    # Creates focus_picks and work_sessions if not exist.
    # Called once at server startup.
```

**Schema:**

```sql
CREATE TABLE IF NOT EXISTS focus_picks (
  id            INTEGER PRIMARY KEY,
  vault         TEXT NOT NULL,
  slot          TEXT NOT NULL,
  date          TEXT NOT NULL,
  project_slug  TEXT NOT NULL,
  intent_slug   TEXT NOT NULL,
  picked_at     TEXT NOT NULL,
  cleared_at    TEXT
);

CREATE TABLE IF NOT EXISTS work_sessions (
  id            INTEGER PRIMARY KEY,
  vault         TEXT NOT NULL,
  slot          TEXT NOT NULL,
  date          TEXT NOT NULL,
  project_slug  TEXT NOT NULL,
  intent_slug   TEXT NOT NULL,
  checkin_at    TEXT NOT NULL,
  checkout_at   TEXT
);
```

**Threading:** `ThreadingMixIn` server (`server.py:1233`) — each request handler opens and closes its own connection. No shared global connection. No explicit lock needed; WAL handles concurrent reads; SQLite serializes concurrent writes internally.

### Layer 3 — API (server.py)

**Modified:**
- `PUT /api/focus/today` — accepts `{project_slug, intent_slug, slot: "am"|"pm"}` (default `"am"` for backwards compat); routes to `set_manual_focus("today")` or `set_manual_focus("today_pm")`
- `GET /api/focus` — extends response shape to include `today_pm: ManualPick|null`

**New:**
- `POST /api/focus/checkin` — body `{project_slug, intent_slug, slot}`; INSERTs into `work_sessions`
- `POST /api/focus/checkout` — body `{}` or `{session_id}`; finds open session for vault, sets `checkout_at`, calls `_update_time_invested()`
- `GET /api/focus/history` — query params `date=YYYY-MM-DD` or `from=...&to=...`; returns picks + sessions with computed durations
- `POST /api/focus/recalculate` — rewrites `time_invested_minutes` for all intents from SQLite aggregate

**`_update_time_invested(vault, intent_slug)` helper (server.py or focus_picker.py):**
1. `SELECT SUM(strftime('%s', checkout_at) - strftime('%s', checkin_at)) FROM work_sessions WHERE vault=? AND intent_slug=? AND checkout_at IS NOT NULL`
2. Convert seconds → integer minutes
3. Write `time_invested_minutes: <n>` to the intent file frontmatter via existing frontmatter writer

**Auto-close orphan sessions:**  
On server startup (`server.py` init block), run:
```sql
UPDATE work_sessions
SET checkout_at = date || 'T23:59:59'
WHERE checkout_at IS NULL AND date < date('now', 'localtime')
```
Closes sessions that were left open across midnight. No background process needed.

### Layer 4 — Morning Prompt (Tauri tray)

**File: `apps/desktop/src-tauri/src/tray_alerts.rs`**

On app startup:
1. `GET /api/focus` → check if `today` is `null`
2. If null AND today's date not in a local "prompted today" flag (stored in `~/.squirrel/state/<vault>.json` as `last_focus_prompt: YYYY-MM-DD`):
   - Fire tray notification: "What's your focus today? Tap to pick."
   - Write `last_focus_prompt: <today>` to state JSON
3. Clicking notification opens `http://localhost:3939` (focus picker modal auto-opens if no focus set)

**One prompt per day** — enforced by `last_focus_prompt` date comparison, not a timer.

### Layer 5 — Frontend (apps/backend/app/src/)

**`client.ts`** — new calls:
```typescript
api.setFocus(slot: "am"|"pm"|"week", projectSlug: string, intentSlug: string)
api.clearFocus(slot: "am"|"pm"|"week")
api.checkin(projectSlug: string, intentSlug: string, slot: string)
api.checkout()
api.getFocusHistory(params: { date?: string; from?: string; to?: string })
```

**`HomePage.tsx`** — focus section renders:
- One card when only `today` is set (full-day, no PM override)
- Two cards when both `today` and `today_pm` are set (AM + PM, may differ)
- Check-in / Check-out button on the active card
- `time_invested` formatted as "Xh Ym" when `time_invested_minutes > 0`
- Active session indicator (pulsing dot or similar) while checked in

**`FocusPickerModal.tsx`** — wire to `PUT /api/focus/today` with correct `slot` param. Currently connected to start-prompt flow only.

## Key Decisions

| Decision | Why |
|----------|-----|
| Option B: keep `"today"` as AM, add `"today_pm"` only | Zero migration. Existing tests untouched. `focus_today` meaning unchanged. |
| SQLite at `squirrel.db`, one connection per request | ThreadingMixIn server makes shared connections unsafe without locking. Per-request connections + WAL is the minimal safe pattern. |
| `time_invested_minutes` is a cache, not source of truth | Task files are version-controlled content; writing raw timestamps creates git noise and sync conflicts. One derived integer is acceptable; timestamps are not. |
| Auto-close orphan sessions at server startup, not midnight daemon | Simpler. No background process. The server is already the right point of coordination. |
| Morning prompt via tray, gated by `last_focus_prompt` date | Reuses existing `tray_alerts.rs` infrastructure. State stored in existing vault state JSON — no new file. |

## Out of Scope

- Raw check-in/check-out timestamps written to the task file
- SQLite replacing frontmatter as the source of truth for current focus state
- A dedicated history page beyond the `GET /api/focus/history` endpoint
- Syncing `squirrel.db` across devices (vault sync does not include `~/.squirrel/`)
- AM/PM picks for the `week` slot — week remains a single pick
