# Research: How Focus Is Selected (Today & Week)

**Date:** 2026-05-28  
**Question:** How can the app select the current focus for today and the week?

---

## 1. Current Focus Selection — Fully Automatic

There is **no manual selection mechanism anywhere**. Focus is computed read-only at request time by `_recommend_focus()` in `apps/cli/lib/status_aggregator.py:340–386`.

### 3-Rule Heuristic (priority order)

| Priority | Trigger | Source field |
|---|---|---|
| 1. Critical alert | `prioridad: finishing-tax` + >7 days stale, OR deadline already past | `status_aggregator.py:194–212` |
| 2. Urgent alert | `deadline` within 7 days | `status_aggregator.py:213–217` |
| 3. Most recent activity | `last_activity` timestamp from shutdown notes | `status_aggregator.py:375–384` |

The result is `{ project, intent, next_action, reason }` returned as `recommended_focus` in the aggregate, then served by `GET /api/home` (`server.py:438–446`).

---

## 2. Data Flow (end-to-end)

```
Vault files (01-Proyectos-Activos/)
  → status_aggregator.aggregate_status()        # scans all WIP projects
    → _recommend_focus(wip_projects)             # 3-rule heuristic
  → deadline_scanner.scan_vault_deadlines()      # urgency buckets
GET /api/home → { focus, pressing, projects }
  → useHome() hook (apps/desktop/src/hooks/useHome.ts:25)
    → FocusWidget (apps/desktop/src/components/FocusWidget.tsx:14)
    → DeadlinesWidget (apps/desktop/src/components/DeadlinesWidget.tsx)
```

---

## 3. What Drives Each Alert Level

### `critical` (becomes focus rule 1)
- `prioridad: finishing-tax` in frontmatter AND `days_since_activity > 7` — `status_aggregator.py:194–199`
- OR `deadline` already past (`days < 0`) — `status_aggregator.py:208–212`

### `urgent` (becomes focus rule 2)
- `deadline` present AND `0 ≤ days_until_deadline < 7` — `status_aggregator.py:213–217`

### Most recent (focus rule 3)
- The WIP project whose shutdown note has the latest timestamp — `status_aggregator.py:375–378`

---

## 4. "Today" vs "Week" — Deadline Buckets

These live in `apps/cli/lib/deadline_scanner.py:37–72` and power the **PRESSING** section (not the focus card):

| Level | Time window | Notes |
|---|---|---|
| `critical` | past deadline OR due today with <4h left | `is_overdue=True`, `days_overdue` set |
| `urgent` | due today (≥4h left) OR due tomorrow | `hours_left` set when same-day |
| `soon` | due in 2–3 days | — |
| `upcoming` | due in 4–7 days | — |
| `eventual` | due in 8–30 days | — |
| `distant` | due in >30 days | — |

Server caps PRESSING at 5 items, pulling from `overdue → critical → urgent` (`server.py:449`).

---

## 5. What Influences the Focus Result (vault-side levers)

| Lever | Where in vault | Effect |
|---|---|---|
| `prioridad: finishing-tax` frontmatter | Project Page `.md` | Becomes critical if stale >7d → highest priority |
| `deadline: YYYY-MM-DD` frontmatter | Project Page `.md` | Overdue → critical; <7d → urgent |
| Shutdown note `### YYYY-MM-DD HH:MM` block | Intent `.md` or Project Page | Updates `last_activity`; latest-activity project wins rule 3 |
| `- **Next Physical Action**: …` bullet | Inside shutdown note block | Populates `next_action` shown in FocusWidget |

---

## 6. `active_intent` and `next_physical_action`

- **`active_intent`**: the intent file (sibling `.md` inside project folder) with the most recent `### YYYY-MM-DD` shutdown note — `status_aggregator.py:163–181`
- **`next_physical_action`**: parsed from the `- **Next Physical Action**:` or `- **Next**:` bullet inside the most recent shutdown note block — `intent_parser.py:237–248`

---

## 7. What Does NOT Influence Focus

- `~/.squirrel/state.json` (written by `/sq-start`) — **not read** by `status_aggregator.py` or `server.py`
- `/sq-start PROJECT-TAG` CLI — updates `state.json` only; has no effect on focus algorithm
- Any `GET /api/home` call — there is no `PUT`/`POST`/`PATCH` focus endpoint (`server.py:244–246`)
- `ProjectSelector.tsx` — only routes capture notes to a project, not focus (`apps/desktop/src/components/ProjectSelector.tsx`)

---

## 8. Key File References

| File | Line(s) | Topic |
|---|---|---|
| `apps/cli/lib/status_aggregator.py` | 340–386 | `_recommend_focus()` — 3-rule heuristic |
| `apps/cli/lib/status_aggregator.py` | 193–219 | Alert generation (critical / urgent) |
| `apps/cli/lib/status_aggregator.py` | 163–188 | `active_intent` + `last_activity` resolution |
| `apps/cli/lib/deadline_scanner.py` | 37–72 | `classify_urgency()` — time buckets |
| `apps/cli/lib/deadline_scanner.py` | 123–141 | Deadline item fields |
| `apps/cli/lib/intent_parser.py` | 216–254 | Shutdown note parsing |
| `apps/cli/lib/intent_parser.py` | 237–248 | `next_physical_action` extraction |
| `apps/backend/server.py` | 424–493 | `/api/home` — assembles focus + pressing |
| `apps/desktop/src/components/FocusWidget.tsx` | 14–45 | Display only, no interaction |
| `apps/desktop/src/hooks/useHome.ts` | 25–58 | Fetches `/api/home` |
