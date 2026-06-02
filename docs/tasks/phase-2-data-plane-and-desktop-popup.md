# Phase 2 — Data Plane + Desktop Popup — Tasks

Source spec: `docs/ears/phase-2-data-plane-and-desktop-popup.md`
Architectural context: `docs/lld/phase-2-data-plane-and-desktop-popup.md`

Conventions:
- `R-x.y` references the EARS requirement that gates the story.
- `deps:` references story IDs in this same file.
- `(mutex: tag)` blocks concurrent execution with stories sharing the same tag.
- Estimates are wall-clock for one engineer in focus. Focus buffer not pre-applied.

---

## Unit 0: Project bootstrap (prerequisite — not in EARS)

- [x] 0.1 Migrate v0.5 squirrel components into the monorepo (commit `4b92a06`).
- [x] 0.2 Wire `apps/cli` and `apps/backend` into the monorepo tooling (commit `c5c384b`).
- [x] 0.3 Triage v0.5 tests; `make test-cli` green (commit `b3f0ae8`).
- [x] 0.4 Smoke-test the migrated backend end-to-end against the real vault; fix `ProjectListItem.last_activity` type drift (commit `65898c7`).
- [x] 0.5 HLD + LLD + EARS for Phase 2 (commits `92cd5d7`, `e4cafa4`, and this commit).

---

## Unit 1: API client and backend liveness (popup foundation)

- [x] 1.1 Add Phase 2 React deps to `apps/desktop/package.json` (deps: none, est: ~10m)
  - implementation: add no new runtime deps; popup uses plain React. If a toast or modal helper is needed, write it; do NOT add a UI library.
  - acceptance: R-7.4 — no new package added that wraps into `packages/ui/` later. `pnpm install` clean.
  - verify: `pnpm install` succeeds; `pnpm -F @squirrel/desktop ls --depth -1` shows the same dep set as Phase 1 except whatever is genuinely new.

- [x] 1.2 Scaffold `apps/desktop/src/api/client.ts` with hard-coded backend origin and typed methods (deps: 1.1, est: ~30m)
  - implementation: export `BACKEND_ORIGIN = "http://127.0.0.1:3939"`. Export typed wrappers: `me()`, `home()`, `parakeet()`, `noteCreate(text, project_slug)`. Copy interfaces (`Me`, `HomePayload`, `FocusItem`, `PressingItem`, `ProjectListItem`) verbatim from `apps/backend/app/src/api/client.ts` (including the `last_activity?` field). 3s timeout on every call via `AbortController`.
  - acceptance: R-1.1, R-6.1, R-6.2 — client uses `127.0.0.1:3939` only, types match the live shape, `last_activity?` declared.
  - verify: `pnpm -F @squirrel/desktop exec tsc --noEmit` clean.

- [x] 1.3 Implement `useBackend()` hook with 10s polling (deps: 1.2, est: ~30m)
  - implementation: `apps/desktop/src/hooks/useBackend.ts`. Returns `{ online: boolean, lastOnlineAt: number | null, lastError: string | null }`. Calls `me()` on mount and every 10000ms. Cancels on unmount. Treats abort/network errors as offline.
  - acceptance: R-1.2, R-1.3, R-1.4, R-1.7 — first call within 500ms, repeats every 10s, never spawns subprocesses.
  - verify: Render a debug page that prints `JSON.stringify(useBackend())`; with backend running on 3939, shows `online: true` within 500ms; kill backend, status flips to `online: false` within 13s.

- [x] 1.4 Implement `BackendStatusBanner` component (deps: 1.3, est: ~15m)
  - implementation: `apps/desktop/src/components/BackendStatusBanner.tsx`. Renders nothing when `online`; renders a sticky top bar with the exact text from R-1.5 when `offline`.
  - acceptance: R-1.5 — banner text matches verbatim.
  - verify: Toggle the backend on/off; banner appears within 13s on offline, disappears immediately on online.

---

## Unit 2: Widgets (data display)

- [x] 2.1 `FocusWidget` reads `/api/home.focus` (deps: 1.2, 1.4, est: ~25m)
  - implementation: `apps/desktop/src/components/FocusWidget.tsx`. Fetches `/api/home` on mount and when `useBackend()` transitions to online (R-1.6). Renders `focus.title` + `focus.next_action`. Caches last successful payload in state.
  - acceptance: R-2.2, R-2.3, R-2.9 — happy path renders both fields; null focus shows the empty-state text; offline keeps last-good at ≤0.5 opacity.
  - verify: With real vault: opens popup, sees current focus. Disable vault config to force null: sees empty-state message. Kill backend: focus stays visible but dimmed.

- [x] 2.2 `DeadlinesWidget` reads `/api/home.pressing[]` (deps: 2.1, est: ~25m)
  - implementation: Same data fetch as 2.1; can share via a `useHome()` hook. Renders first 3 items per R-2.5 format string.
  - acceptance: R-2.4, R-2.5, R-2.6, R-2.9.
  - verify: Against the user's real vault (3 overdue deadlines verified in smoke test), shows "CASA-CONTABILIDAD-TAXES-2025 — OVERDUE 43d" as the first item.

- [x] 2.3 `ParakeetWidget` reads `/api/parakeet` (deps: 1.4, est: ~15m)
  - implementation: `apps/desktop/src/components/ParakeetWidget.tsx`. Renders `message` verbatim; renders nothing when message is empty/whitespace.
  - acceptance: R-2.7, R-2.8, R-2.9.
  - verify: With current vault: shows "4 thing(s) slipped past." Mock the endpoint to return `{ message: "" }`; widget renders zero pixels.

- [x] 2.4 Refactor 2.1 + 2.2 to share `useHome()` (deps: 2.1, 2.2, est: ~15m) — implemented up-front rather than as a refactor.
  - implementation: Extract the `/api/home` fetch into `apps/desktop/src/hooks/useHome.ts`; FocusWidget and DeadlinesWidget consume the same payload. Single network call per popup mount + per online-transition.
  - acceptance: per-widget independence (D2) is preserved at the failure-mode level; this is a fetch-dedup optimization not a coupling.
  - verify: Network panel in webview devtools shows exactly one `/api/home` request on popup open, not two.

---

## Unit 3: Capture path

- [x] 3.1 Build `CaptureButton` + `CaptureModal` (deps: 1.2, 1.4, est: ~50m)
  - implementation: `apps/desktop/src/components/CaptureButton.tsx` + `CaptureModal.tsx`. Modal has a single `<textarea>` and Save / Cancel. Save calls `client.noteCreate(text, null)`. On 2xx → close + toast. On non-2xx → keep modal open, render server's `error` or `message` inline above the textarea, leave input value untouched.
  - acceptance: R-3.1, R-3.3, R-3.4, R-3.5, R-3.6.
  - verify: Click button → modal opens. Type "test capture from popup" → Save → modal closes, toast appears, vault inbox file gains a new note. Force backend to 500 (e.g. send invalid body via devtools); error renders inline, text stays.

- [x] 3.2 Wire offline-disable on CaptureButton (deps: 3.1, est: ~10m)
  - acceptance: R-3.2 — button disabled while offline, tooltip exact text.
  - verify: Kill backend; button shows disabled state with hover tooltip; clicks are inert.

- [x] 3.3 Implement minimal toast primitive (deps: none, est: ~25m, mutex: ui-primitives)
  - implementation: `apps/desktop/src/components/Toast.tsx`. ~30 lines. Single-toast queue, 3s auto-dismiss, manual dismiss button.
  - acceptance: nothing in EARS gates this directly; supports R-3.5.
  - verify: Trigger from a test button; toast appears, fades, dismisses.

---

## Unit 4: "Open Web UI" affordance

- [x] 4.1 Add "Open Web UI" item to tray menu between "Open Squirrel" and "Background Watcher" (deps: 0.5, est: ~20m)
  - implementation: Edit `apps/desktop/src-tauri/src/tray.rs`. Insert a new menu item with id `open-web-ui`. On click, call `app.opener().open_url("http://127.0.0.1:3939", None::<&str>)` (tauri-plugin-opener).
  - acceptance: R-4.1, R-4.3, R-4.4 — menu position correct, plugin invoked, no pre-flight check.
  - verify: Tray menu shows the five items in the new order: Open Squirrel, Open Web UI, Background Watcher, Settings, View Logs, Quit. Wait — that's 6. The Phase 1 menu was 5 items; this becomes 6. Confirm with R-4.1 wording: "between Open Squirrel and Background Watcher" → yes, 6 items.
  - note: This makes the tray menu 6 items long. Phase 1 R-2.5 mandated exactly 5 items in a specific order; Phase 2 R-4.1 extends it. Document the supersession in the implementation commit message.

- [x] 4.2 Add "Open Web UI" button to popup body (deps: 2.4, est: ~15m)
  - implementation: Render a button at the bottom of `apps/desktop/src/App.tsx` that invokes `tauri-plugin-opener` with the same URL.
  - acceptance: R-4.2, R-4.3.
  - verify: Click button in popup; default browser opens to `http://127.0.0.1:3939`.

---

## Unit 5: CSP and security hardening

- [x] 5.1 Set CSP in `apps/desktop/src-tauri/tauri.conf.json` (deps: 0.5, est: ~20m)
  - implementation: Set `app.security.csp` to the exact string from R-5.1.
  - acceptance: R-5.1.
  - verify: Open the popup in `pnpm tauri dev`. Open webview devtools. Confirm: a `fetch("https://example.com")` in the console is blocked by CSP; `fetch("http://127.0.0.1:3939/api/me")` succeeds.

- [x] 5.2 Audit popup for external resource references (deps: 5.1, est: ~15m, mutex: ui-primitives)
  - implementation: Replace any `<link href="https://...">` or `<script src="https://...">` in `apps/desktop/index.html` and components with local files or remove. No Tailwind CDN. No Material Icons CDN. No fonts.googleapis.com.
  - acceptance: R-5.2, R-5.3.
  - verify: `grep -rn "https://" apps/desktop/index.html apps/desktop/src/` returns zero matches (excluding code comments).

---

## Unit 6: Wire-up and ship

- [x] 6.1 Mount the popup in `apps/desktop/src/App.tsx` (deps: 1.4, 2.1, 2.2, 2.3, 3.1, 4.2, est: ~20m)
  - implementation: Replace the Phase 1 boilerplate `App.tsx` with a stack: BackendStatusBanner → FocusWidget → DeadlinesWidget → ParakeetWidget → CaptureButton → OpenWebUIButton.
  - acceptance: R-2.1.
  - verify: `pnpm tauri dev` opens popup showing all five widgets when backend is up, just banner + dimmed last-good when backend is down.

- [x] 6.2 Add `dev` Make targets for the two-process workflow (deps: none, est: ~10m)
  - implementation: Update root `Makefile`. Add `make dev-all` → starts backend in background and runs `pnpm tauri dev` in foreground; on Ctrl+C, kill backend. (Or just document the two-terminal workflow if the trap logic is messy.)
  - acceptance: Phase 2 success criterion #4 reachable from one command.
  - verify: `make dev-all` opens the popup with widgets populated; Ctrl+C stops both processes.

- [ ] 6.3 Manual end-to-end against the success criteria (deps: 6.1, 6.2, est: ~30m)
  - implementation: Walk through the 7 success criteria in HLD § "Success Criteria". Record results in a brief PR comment.
  - acceptance: All 7 criteria observable on the user's machine.
  - verify: Hand-run each; checkboxes in PR description.

---

## Out-of-scope guardrails (do not implement in Phase 2)

The following items have explicit EARS NOT requirements (Unit 7) and are tracked as Phase 3 candidates only:

- Tauri sidecar embedding of `server.py` — R-7.1
- launchd plist for the backend — R-7.2
- Repointing the user's existing `org.squirrel.web-ui.plist` away from the source repo — R-7.2, LLD D8
- `#[tauri::command]` Rust↔Python bridge — R-7.3
- `packages/ui/` shared component layer — R-7.4
- macOS deadline daemon refactor to consume `/api/deadlines` — R-7.5
- Real vault watcher replacing the Phase 1 fake — R-7.6
- `agent-pack/install.sh` update to build the SPA on install — tracked as Phase 3 distribution work (LLD D9 follow-up)

---

## Estimated wall-clock total

| Unit | Stories | Wall-clock |
|---|---|---|
| 1 | 1.1–1.4 | ~1h25m |
| 2 | 2.1–2.4 | ~1h20m |
| 3 | 3.1–3.3 | ~1h25m |
| 4 | 4.1–4.2 | ~35m |
| 5 | 5.1–5.2 | ~35m |
| 6 | 6.1–6.3 | ~1h |
| **Total** | **16 stories** | **~6h20m** (≈ 1.5 focused days with focus ×2 buffer) |
