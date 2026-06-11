# Desktop Focus Check-in / Check-out & Live Timer — Tasks

Source specs: `docs/hld/desktop-focus-checkin-timer.md`, `docs/lld/desktop-focus-checkin-timer.md`, `docs/ears/desktop-focus-checkin-timer.md`.
Scope is **frontend-only** in `apps/desktop/src` — no backend, SQLite, or web-UI changes (R-5.4). Backend endpoints (`/api/focus/checkin`, `/api/focus/checkout`, `/api/focus/session`) are consumed as they exist today.

> Back-filled after implementation. All units are checked because the code already shipped on this branch; acceptance/verify blocks document the contract each touch point satisfies.

Dependency layers (LLD build sequence: client → hook → card → switch modal → orchestration):
```
A.1 (api client: checkin/checkout/session + OpenSession type)
        │
       B.1 (useFocusSession hook — derived timer)
        │
   ┌────┴───────────────┬───────────────┐
  C.1                  C.2             D.1
 (FocusWidget         (HH:MM          (FocusSwitchModal)
  check-in controls)   formatter)        │
        └───────────────┬────────────────┘
                       E.1
              (App orchestration:
               handleCheckin/out + switch gate)
```

---

## Unit A: API client — `src/api/client.ts`

- [x] **A.1** Add `focusCheckin` / `focusCheckout` / `focusSession` + `OpenSession` type (est: ~25m)
  - acceptance:
    - R-1.1 — `api.focusCheckin({project_slug, intent_slug, slot})` `POST`s `/api/focus/checkin`, resolves `{session_id}`.
    - R-1.2 — `api.focusCheckout()` `POST`s `/api/focus/checkout`, resolves `{session_id, duration_minutes, time_invested_minutes}`.
    - R-1.3 — `api.focusSession()` `GET`s `/api/focus/session`, resolves an `OpenSession {project_slug, intent_slug, checkin_at}`.
    - R-1.4 — A `404` (`no_open_session`) from the session endpoint maps to `null` and does **not** throw.
  - verify:
    - Type-check passes; manual: with no open session `focusSession()` returns `null`; after a check-in it returns the open session with a UTC ISO `checkin_at`.

## Unit B: Session hook — `src/hooks/useFocusSession.ts` (new)

- [x] **B.1** `useFocusSession(triggerKey)` — derived elapsed minutes, visibility-gated interval (deps: A.1, est: ~45m)
  - acceptance:
    - R-2.1 — Derives `elapsedMinutes = max(0, floor((nowMs − checkinAtMs) / 60000))` from `checkin_at`, never from an accumulator.
    - R-2.3 — Advances `nowMs` via a single 60 000 ms `setInterval` created **only while** `document.visibilityState === "visible"`.
    - R-2.4 — Clears the interval when the document becomes hidden (no timer work while the window is closed).
    - R-2.5 — On `visibilitychange → visible`, re-fetches the session and resets `nowMs` immediately (no up-to-59 s lag on reopen).
    - R-2.6 — Negative `now − checkin_at` (clock skew) clamps to `0`.
    - R-2.7 — Resolves `checkin_at` via `Date.parse` (absolute epoch) and compares against `Date.now()`; elapsed is timezone-correct.
  - verify:
    - Vitest (mirror `useHome`): mount fetches the session; emitting `triggerKey` refetches; hiding the document clears the interval; re-showing recomputes immediately. Manual: card shows `00:00`, advances to `00:01` after a minute; close N minutes, reopen → shows ≈ N minutes.

## Unit C: Card controls — `src/components/FocusWidget.tsx`

- [x] **C.1** `ManualFocusRow` check-in / check-out controls (deps: B.1, est: ~40m)
  - acceptance:
    - R-3.1 — While online and no session open, every focus pick (Today AM, Today PM, This Week) shows a **Check in** control.
    - R-3.3 — While a session is open for a row, that row shows the live `HH:MM` chip + **Check out** and hides its **Check in**.
    - R-3.6 — Only the running-segment timer renders on the card; accumulated totals stay in the existing `EstimateLine`.
    - R-5.1 — Offline hides/disables the controls, matching the existing dimmed focus-card pattern.
    - New props threaded from `App`: `session`, `elapsedMinutes`, `onCheckin(pick)`, `onCheckout()`; a pick is keyed `${project_slug}/${intent_slug}`.
  - verify:
    - Vitest (mirror `manual-focus-pick` widget tests): no session → all picks show Check in; open session row shows chip + Check out and no Check in. Manual: tap Check in → chip appears.

- [x] **C.2** `HH:MM` formatter helper (deps: B.1, est: ~10m)
  - acceptance:
    - R-2.2 — Formats elapsed minutes as zero-padded `HH:MM` with unbounded hours (`00:07`, `12:34`).
    - Inlined next to `fmtMins` in `FocusWidget.tsx` — **not** a shared cross-page helper (project convention).
  - verify:
    - Unit: `7 → "00:07"`, `754 → "12:34"`, `0 → "00:00"`.

## Unit D: Switch confirm — `src/components/FocusSwitchModal.tsx` (new)

- [x] **D.1** Friendly switch-gate modal (deps: A.1, est: ~30m)
  - acceptance:
    - R-4.2 — Centered in-app modal (panel + dim backdrop, matching `CaptureModal`) stating the friendly message and naming the currently-open and attempted tasks; does **not** call `api.focusCheckin`.
    - R-4.3 — Offers **Check out current task** (calls the check-out handler, then dismisses).
    - R-4.4 — Does **not** auto-check-out or auto-check-in; after checkout the user re-taps Check in.
    - R-4.5 — Keep current task / Escape / backdrop dismiss leaves the open session running (dismiss disabled while a checkout is in flight).
  - verify:
    - Vitest (mirror `CaptureModal`): modal renders both task titles; Check out current task invokes the handler; Escape/backdrop dismiss without starting a session. Manual: open dialog by tapping a second pick.

## Unit E: Orchestration — `src/App.tsx`

- [x] **E.1** Wire `useFocusSession` + check-in/out handlers + switch gate (deps: C.1, D.1, est: ~35m)
  - acceptance:
    - R-3.2 — `handleCheckin(pick)` with no open session calls `api.focusCheckin` for the pick's `{project_slug, intent_slug, slot}`, then bumps home + `focusSession.refetch()`.
    - R-1.5 — `slot` is `"today"` for an AM pick, `"today_pm"` for PM, `"week"` for the weekly pick.
    - R-4.1 / R-4.2 — When a session is open for a *different* intent, `handleCheckin` opens `FocusSwitchModal` and returns without calling the API; at most one open session vault-wide.
    - R-3.4 — `handleCheckout()` calls `api.focusCheckout`, bumps + refetches; the pick returns to Check in.
    - R-5.2 — Check-in/out/session failures fail best-effort (leave UI in place) without crashing the popup.
  - verify:
    - Vitest: check-in with no session calls the API + refetch; check-in on a different intent opens the modal and skips the API; check-out refetches. Manual: full check-in → timer → check-out cycle; second-pick check-in shows the dialog.

## Unit F: Invariants

- [x] **F.1** No backend / web-UI changes; one-session invariant respected (est: ~10m)
  - acceptance:
    - R-5.3 — When the server has auto-closed a stale prior-day session, `api.focusSession()` returns `null` and no live timer renders.
    - R-5.4 — No edits under `apps/backend`, SQLite, or the web UI; endpoints used exactly as they exist.
  - verify:
    - `git diff --stat` for the change touches only `apps/desktop/src`; manual: stale prior-day session → no timer shown.
