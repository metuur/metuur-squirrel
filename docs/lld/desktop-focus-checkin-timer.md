# Desktop Focus Check-in / Check-out & Live Timer — Low-Level Design

## Architecture

All changes live in `apps/desktop/src`. Three touch points plus one new hook.

### 1. API client — `src/api/client.ts`
Add three methods to the `api` object, mirroring the existing `call<T>(path, opts)`
+ `focusSet` style:

```ts
focusCheckin: (body: { project_slug: string; intent_slug: string; slot: "today" | "today_pm" | "week" }) =>
  call<{ session_id: number }>("/api/focus/checkin", { method: "POST", body: JSON.stringify(body) }),

focusCheckout: () =>
  call<{ session_id: number; duration_minutes: number; time_invested_minutes: number }>(
    "/api/focus/checkout", { method: "POST" }),

focusSession: () =>
  call<OpenSession | null>("/api/focus/session"),
```

`GET /api/focus/session` returns **404** (`no_open_session`) when nothing is open.
The client maps that 404 to `null` (do not throw), so callers treat "no session"
as a normal state. New type:

```ts
export interface OpenSession {
  project_slug: string;
  intent_slug: string;
  checkin_at: string; // UTC ISO-8601, as written by the backend
}
```

### 2. Session hook — `src/hooks/useFocusSession.ts` (new)
Fetches the single open session and exposes the derived elapsed minutes. Pattern
follows `useHome` (generation-guarded fetch, re-fetch on `triggerKey`).

- On mount, on `triggerKey` change, and on `document` `visibilitychange → visible`,
  call `api.focusSession()` and store `{ session, checkinAtMs }` where
  `checkinAtMs = Date.parse(checkin_at)` — `Date.parse` resolves the backend's UTC
  ISO string to an absolute epoch in ms.
- Maintains `nowMs` state (the computer's local clock via `Date.now()`) updated by a
  **60 000 ms `setInterval`** that is **created only while
  `document.visibilityState === "visible"`** and cleared on hidden. On becoming
  visible it both refetches the session and resets `nowMs` immediately, so reopening
  the window shows a fresh, correct value (no up-to-59 s lag on reopen).
- Derives `elapsedMinutes = max(0, floor((nowMs − checkinAtMs) / 60000))`. Because
  both operands are absolute epoch ms, the result is correct regardless of the
  machine's timezone.

```ts
export interface FocusSessionState {
  session: OpenSession | null;
  elapsedMinutes: number;   // live, derived
  loading: boolean;
  refetch: () => void;
}
export function useFocusSession(triggerKey: number): FocusSessionState
```

The timer string is formatted `HH:MM` with zero-padded, unbounded hours
(e.g. `00:07`, `12:34`) by a small inline helper next to `fmtMins` in
`FocusWidget.tsx` — **not** a shared cross-page helper (per project convention).

### 3. Card controls — `src/components/FocusWidget.tsx`
`ManualFocusRow` gains check-in controls driven by new props threaded from `App`:

- New props on `FocusWidget` / `ManualFocusRow`:
  `session: OpenSession | null`, `elapsedMinutes: number`,
  `onCheckin(pick)`, `onCheckout()`.
- A pick is identified by `key = ` `${project_slug}/${intent_slug}`.
- Render logic per focus row:
  - **No open session** → show **`Check in`** button.
  - **This row is the open session** → show live **`HH:MM`** chip + **`Check out`**
    button, and SHALL NOT show its **Check in** button.
  - **A different row's session is open** → its `Check in` is still shown but
    tapping it triggers the friendly-switch dialog (handled in `App`).
- Controls render only when `online`; offline mirrors the existing dimmed pattern.

### 3b. Switch confirm — `src/components/FocusSwitchModal.tsx` (new)
An in-app centered modal (panel + dim backdrop, matching `CaptureModal`) shown
when the user taps Check in on a different pick while a session is open. It states
the friendly message, shows the currently-open and attempted task titles, and
offers **Check out current task** (calls the check-out handler) and **Keep current
task** (dismiss). Escape / backdrop-click cancel (disabled while a checkout is in
flight). It does **not** auto-check-in the new task — the user re-taps Check in.

### 4. Orchestration — `src/App.tsx`
- Call `const focusSession = useFocusSession(triggerKey)` alongside `useHome`.
- `handleCheckin(pick)`:
  - If `focusSession.session` is open **and** it is a *different* intent → open the
    `FocusSwitchModal` (set `switchPromptPick`) and **return without calling the
    API**.
  - Else `await api.focusCheckin({ project_slug, intent_slug, slot })`, then
    `setHomeBump(n => n+1)` and `focusSession.refetch()`.
- `handleCheckout()`: `await api.focusCheckout()`, bump + refetch.
- `handleSwitchCheckout()`: same as check-out plus closes the modal and tracks a
  `switchBusy` flag; on failure it leaves the modal open to retry.
- `slot` for check-in is the slot the pick occupies: AM pick → `"today"`,
  PM pick → `"today_pm"`, week pick → `"week"`.

### Data flow
```
[user taps Check in on a pick]
  App.handleCheckin → guard: is a *different* session open?
     yes → friendly confirm, stop.
     no  → api.focusCheckin → setHomeBump + focusSession.refetch
                                   ↓
   useFocusSession.session = {checkin_at}
                                   ↓ (every 60s while visible, + on (re)show)
   elapsedMinutes = floor((Date.now() − Date.parse(checkin_at))/60000)
                                   ↓
   FocusWidget row renders HH:MM chip + Check out
```

## Constraints
- **Frontend-only**: no edits under `apps/backend` or SQLite. Endpoints are used
  exactly as they exist today.
- **No background process**: the only timer is a foreground `setInterval` that is
  torn down whenever the document is hidden; all elapsed values derive from
  `checkin_at`. Closing the window stops all ticking by construction.
- **One open session per vault** is a backend invariant; the UI must not attempt to
  open a second — it routes the user through check-out/pause instead.
- Timestamps from the backend are **UTC ISO**; parse with `Date.parse` (resolves the
  `+00:00`/`Z` suffix to an absolute epoch) and compare against the computer's local
  clock via `Date.now()` — both absolute, so elapsed is timezone-correct.
- Match existing style: `call<T>`, best-effort `try/catch` with home refetch, Tailwind
  utility classes, no new dependencies.

## Key Decisions
- **Derived timer, minute granularity.** `elapsedMinutes` is recomputed from
  `checkin_at`; the 60 s interval only drives re-render and is paused while hidden.
  Chosen over a stored countdown because it is correct across window close/reopen
  and needs zero persistence. Up-to-59 s display lag is eliminated on reopen by the
  visibility-triggered immediate recompute. (Rejected: per-second ticking — user
  asked for HH:MM by the minute.)
- **No Pause concept — stopping is a plain Check out.** Per user preference, there
  is no pause/resume; **Check out** ends the session and banks minutes into
  `time_invested_minutes` via the existing aggregation. Re-starting later is just a
  fresh **Check in**, and total time is the SQLite sum of segments. (Rejected: a
  Pause/Resume affordance — deferred to keep this frontend-only and simple.)
- **Switch is gated, not automatic.** Per user preference, checking into a new task
  while one is open shows a friendly confirmation and requires an explicit
  check-out first; we never auto-close the running session. (Rejected:
  auto-checkout-then-checkin.)
- **Separate `useFocusSession` hook, not folded into `useHome`.** `/api/home` does
  not carry the open session and we do not modify the backend; an independent fetch
  keeps widget independence (same rationale as the existing useHome dedup note).
- **Live timer only on the card.** Accumulated totals stay in the existing
  `EstimateLine`; the timer shows only the running segment (per user choice).

## Out of Scope
- Any Pause/Resume affordance; idle detection / auto-pause.
- Seconds display; multiple concurrent sessions; per-session history UI in the popup
  (history already exists via `GET /api/focus/history`).
- Any web-UI change; any backend change.
