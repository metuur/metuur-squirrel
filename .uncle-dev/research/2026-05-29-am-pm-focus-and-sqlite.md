# AM/PM Focus Slots + Embedded SQLite — Research

**Date:** 2026-05-29  
**Question:** How to add AM/PM daily focus selection, and is SQLite the right store for focus history?

---

## 1. Current Focus System — What IS

### Slots and Tokens
Two hard-coded slots exist in `apps/cli/lib/focus_picker.py`:

| Slot | Frontmatter key | Token format | Example |
|------|----------------|--------------|---------|
| `today` | `focus_today` | `YYYY-MM-DD` | `2026-05-28` |
| `week` | `focus_week` | `GGGG-Www` | `2026-W22` |

`_token_now(slot)` — `focus_picker.py:58` — generates the token using `datetime.datetime.now()` (local wall clock). Invalid slot names raise `ValueError`.

**No AM/PM, no time-of-day concept exists anywhere in the codebase.**

### Storage
Focus is stored as a frontmatter key on the intent file itself:

```yaml
---
id: SIDEPROJECT-FOYER-FAMILY-NEXT
estado: in-progress
focus_today: 2026-05-28   ← token, written by set_manual_focus()
---
```

`focus_picker.py:196-214` — `set_manual_focus()` runs a **strip pass** (removes current token from all other intents) then an **upsert pass** on the target. One token active at a time per slot.

### API Endpoints (backend)
```
GET  /api/focus               → {today: ManualPick|null, week: ManualPick|null}
PUT  /api/focus/today         → body {project_slug, intent_slug} or {clear: true}
PUT  /api/focus/week          → same
```
`server.py:209-211`

Response `ManualPick` shape (`test_web_ui_focus_get.py:128-130`):
```json
{
  "intent_slug": "…",
  "picked_on": "2026-05-28",
  "project_slug": "…",
  "project_title": "…",
  "intent_title": "…",
  "next_action": "…"
}
```

### Frontend — What's Missing
- **No focus picker UI** exists in `apps/backend/app/src/`. — `Explore agent finding`
- The home page (`HomePage.tsx:58-68`) renders focus **read-only** from `HomePayload.focus`.
- The API client (`client.ts`) has **no `api.setFocus()` call** — the PUT endpoints are unused by the frontend.
- A `FocusPickerModal` component exists at `apps/backend/app/src/components/FocusPickerModal.tsx` — but it is not wired to any PUT endpoint; it is used for the "help me start" prompt flow, not for manual selection.

### Recommended Focus vs Manual Focus
- `recommended_focus` — heuristic in `status_aggregator.py:384-430`: priority order is critical/stale → deadline < 3 days → most recent activity.
- `manual_focus` — user's explicit pick stored in frontmatter.
- **Invariant (R-4.2-4.4)**: manual pick does NOT modify recommended_focus — both are independent.

---

## 2. AM/PM Slot Design — What It Would Take

### Option A — Two New Slots (minimal change to focus_picker.py)

Add `"today_am"` and `"today_pm"` as valid slot strings:

```python
# focus_picker.py — _token_now extension
if slot == "today_am":
    return n.strftime("%Y-%m-%d-AM")
if slot == "today_pm":
    return n.strftime("%Y-%m-%d-PM")
```

New frontmatter keys: `focus_today_am`, `focus_today_pm` (via `_slot_key()`).

New API endpoints:
```
PUT /api/focus/today/am
PUT /api/focus/today/pm
```
or keep the current path and pass slot in the body.

**Impact surface:**
- `focus_picker.py:58-82` — `_token_now` + `_slot_key`
- `server.py:209-580` — route table + `_api_focus_put(slot)`
- All existing tests in `test_focus_picker.py` pass unchanged (they only test `"today"` and `"week"`)
- New tests needed for strip-pass cross-slot invariant (AM clear should not clear PM)

### Option B — Keep "today" as AM, Add "today_pm" Only

- `"today"` = current AM slot (backwards-compatible)
- `"today_pm"` = new PM slot
- No migration needed; old picks remain valid

### Frontend UX implication
The existing homepage shows one `TODAY'S FOCUS` card. With AM/PM it becomes two cards or a toggle. The FocusPicker modal (`FocusPickerModal.tsx`) would need wiring to PUT the correct slot.

---

## 3. SQLite — What Exists Today and What It Would Add

### Current State — Zero Database
- No `sqlite3`, SQLAlchemy, or `.db` files anywhere. — `grep finding, backend/server.py`
- Server: `socketserver.ThreadingMixIn` + `http.server.HTTPServer` on `127.0.0.1:3939`. Multi-threaded. Single process.
- All persistence is:
  - TOML: `~/.squirrel/config.toml` (vaults config)
  - JSON: `~/.squirrel/state/<vault>.json` (current context per vault)
  - JSONL: `<vault>/.squirrel/session-manifest.jsonl` (edit history)
  - JSONL: `<vault>/.squirrel/switches.jsonl` (context switches)
  - Markdown frontmatter: all project/intent data

### What SQLite Would Add

Focus history is not stored anywhere today. The only way to know what was focused when is to grep the switches log. A SQLite DB at `~/.squirrel/squirrel.db` could store:

```sql
CREATE TABLE focus_history (
  id         INTEGER PRIMARY KEY,
  vault      TEXT NOT NULL,
  slot       TEXT NOT NULL,          -- 'today', 'today_am', 'today_pm', 'week'
  date       TEXT NOT NULL,          -- YYYY-MM-DD
  project_slug TEXT NOT NULL,
  intent_slug  TEXT NOT NULL,
  picked_at  TEXT NOT NULL,          -- ISO datetime
  cleared_at TEXT                    -- NULL = still active when cleared
);
```

Every `set_manual_focus()` call appends a row. Every `clear_manual_focus()` sets `cleared_at`.

### Threading Consideration
Python's `sqlite3` module requires connections per-thread OR using `check_same_thread=False` with an explicit lock. The server is multi-threaded (`ThreadingMixIn`, `server.py:1233`). A module-level `threading.Lock` wrapping all DB writes (reads can use WAL mode) is the minimal safe pattern — no extra dependencies.

### What SQLite Would NOT Replace
The frontmatter-based token system (`focus_today`, `focus_week`) is the source of truth for the **current** focus because `get_manual_focus()` reads it on every request by scanning intent files. SQLite history would be a write-through log, not a replacement.

### Alternative — Append to switches.jsonl
`<vault>/.squirrel/switches.jsonl` already records context switches with `{timestamp, date, from, to, reason}` (`switch_tracker.py:30-56`). A `reason: "focus-pick"` entry with `slot`, `project_slug`, `intent_slug` could be appended there without introducing a new dependency. Query = grep + filter. No schema, no migration.

---

## 4. Key Numbers

| Item | File | Line |
|------|------|------|
| `_token_now()` | `apps/cli/lib/focus_picker.py` | 58 |
| `_slot_key()` | `apps/cli/lib/focus_picker.py` | 76 |
| `set_manual_focus()` | `apps/cli/lib/focus_picker.py` | 175 |
| `get_manual_focus()` | `apps/cli/lib/focus_picker.py` | 101 |
| Focus API routes | `apps/backend/server.py` | 209–211 |
| `_api_focus_put()` | `apps/backend/server.py` | 558 |
| ThreadingMixIn server | `apps/backend/server.py` | 1233 |
| State dir | `apps/cli/lib/config_loader.py` | 78 |
| switches.jsonl writer | `apps/cli/lib/switch_tracker.py` | 30–56 |
| No DB anywhere | — | — |
