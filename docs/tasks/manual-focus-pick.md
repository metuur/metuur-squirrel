# Manual Focus Pick (Today & Week) — Tasks

Source specs: `docs/hld/manual-focus-pick.md`, `docs/lld/manual-focus-pick.md`, `docs/ears/manual-focus-pick.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Dependency layers:
```
A,B  (foundation: frontmatter round-trip + focus_picker module)
 │
 C   (REST endpoints)
 │
 ├─ D   (/api/home additive)
 │
 ├─ E   (typed client + useHome widening)        ──► F, G (modal + widget pills)
 │
 ├─ H   (CLI /sq-focus)
 │
 └─ I   (active_intent_for helper) ──► J         (daemon "Focus now")
                                          │
                                          K       (e2e verification)
```

## Unit 1: Frontmatter storage contract

- [x] **1.1** Add `write_frontmatter(path, mutations)` helper to `apps/cli/lib/intent_parser.py` (est: ~45m)
  - acceptance:
    - R-1.6 — Round-trip preservation: read → no-op write → byte-identical file.
    - R-1.7 — `mutations = {"focus_today": _DELETE}` removes the key entirely (no `null`, no empty string).
  - verify:
    - Golden-file pytest: load fixture intent `.md` with frontmatter (incl. comment line and mixed-type keys), call helper with no mutations, assert `read() == original`.
    - Second pytest: call with `{"focus_today": "2026-05-28"}`, assert key appears in frontmatter at end of block, body unchanged.
    - Third pytest: call with `{"focus_today": _DELETE}` on a file that has the key, assert key is gone, no `null` written.

- [x] **1.2** Create `apps/cli/lib/focus_picker.py` with `_token_now(slot, tz)`, `get_manual_focus(vault)`, `set_manual_focus(vault, slot, project_slug, intent_slug)`, `clear_manual_focus(vault, slot)` (deps: 1.1, est: ~90m)
  - acceptance:
    - R-1.1 / R-1.2 — Writes `focus_today: YYYY-MM-DD` or `focus_week: GGGG-Www` on the chosen intent file.
    - R-1.3 — Uses local timezone (not UTC) for both tokens.
    - R-1.4 / R-1.5 — On read, ignores stale values (date or week token that doesn't match "now").
    - R-1.8 — Writes nothing under `~/.squirrel/` or `apps/backend/`; all I/O is inside the vault.
    - R-9.3 / R-9.4 — No background process; expiry is read-time only.
  - verify:
    - Unit test: freeze clock to 2026-05-28 12:00 local. Create vault fixture with three intent files: one with `focus_today: 2026-05-28` (today), one with `focus_today: 2026-05-27` (stale), one with no key. Call `get_manual_focus(vault).today` → returns the "today" intent only.
    - Unit test: same fixture, call `set_manual_focus(vault, "today", new_project, new_intent)`. Assert: new file gets the key with today's date; original today-tagged file no longer has the key; stale file is left untouched (per R-2.5).
    - Unit test: ISO-week token format — freeze to a known Monday and a known Sunday in the same week; assert both return the same `GGGG-Www` token.

## Unit 2: Single-pick invariant

- [x] **2.1** Implement the strip-before-write step inside `set_manual_focus` (covered by 1.2's code; this story adds the dedicated tests) (deps: 1.2, est: ~30m)
  - acceptance:
    - R-2.1 / R-2.2 — Before writing the new key, scan vault and strip existing keys whose value equals the current slot token.
    - R-2.3 — Setting `today` does not touch `focus_week`; setting `week` does not touch `focus_today`.
    - R-2.4 — Idempotent: setting the same intent twice in a row leaves a single key.
  - verify:
    - Pytest: seed two intent files both with `focus_today: <today>` (simulating a manual Obsidian dup). Call `set_manual_focus(... new_intent)`. Assert exactly one file in the vault has `focus_today: <today>` afterwards, and it is the new one.
    - Pytest: file has both `focus_today` and `focus_week` set. Call `set_manual_focus(vault, "today", ...)` targeting a different intent. Assert the original's `focus_week` is preserved.

- [x] **2.2** Read-time tiebreak by file mtime when duplicates exist (deps: 1.2, est: ~15m)
  - acceptance:
    - R-2.6 — Two intents both carry `focus_today: <today>` (manual edit case) → `get_manual_focus` returns the more recently modified one and does not error.
  - verify:
    - Pytest: create two duped files, `touch` one to bump mtime, assert `get_manual_focus().today.intent_slug` matches the touched one.

## Unit 3: `/api/focus/*` endpoints

- [x] **3.1** Add `GET /api/focus` to `apps/backend/server.py` (deps: 1.2, est: ~30m)
  - acceptance:
    - R-3.1 — Returns `{today: ManualPick|null, week: ManualPick|null}`.
    - R-3.2 — `picked_on` is the verbatim YAML value.
    - R-3.8 — Bound to `127.0.0.1` (inherits existing server binding).
  - verify:
    - `curl http://127.0.0.1:3939/api/focus` against a vault with a known fixture → matches expected JSON shape (assert via a pytest backend test).

- [x] **3.2** Add `PUT /api/focus/today` and `PUT /api/focus/week` (deps: 1.2, 3.1, est: ~45m)
  - acceptance:
    - R-3.3 / R-3.4 — Accepts `{project_slug, intent_slug}` or `{clear: true}`.
    - R-3.5 — `{clear: true}` removes the key from any intent carrying it with the current token.
    - R-3.6 — Unknown slug → HTTP 404 `{error: "intent_not_found"}`, no file mutation.
    - R-3.7 — Missing both keys → HTTP 400 `{error: "bad_request"}`.
  - verify:
    - Pytest backend: PUT with valid pair → 200, response shows new pick.
    - Pytest backend: PUT with bogus project_slug → 404, vault filesystem unchanged (compare mtime + content).
    - Pytest backend: PUT with `{}` → 400.
    - Pytest backend: PUT `{clear: true}` → 200, subsequent GET shows `null` for the slot.

## Unit 4: `/api/home` integration (additive)

- [x] **4.1** Extend `GET /api/home` response with `manual_focus` field (deps: 3.1, est: ~30m)
  - acceptance:
    - R-4.1 — New top-level `manual_focus: {today, week}` field.
    - R-4.2 / R-10.2 — Existing `focus`, `pressing[]`, `projects[]` fields shape-identical.
    - R-4.3 / R-4.4 / R-10.1 — `_recommend_focus()` and pressing logic untouched.
    - R-4.5 — Stale or unset → `null` (not missing key).
    - R-9.1 / R-9.2 — After local midnight / Monday rollover, the API returns `null` even if the YAML key still physically exists with the previous token.
  - verify:
    - Pytest: snapshot the response of `/api/home` from a known fixture BEFORE the change. After the change, the same fixture must produce a response where every existing key has identical value and a new `manual_focus` key is present.
    - Pytest with frozen clock: set `focus_today: 2026-05-27` on an intent, freeze clock to 2026-05-28, hit `/api/home` → `manual_focus.today` is `null`. Verify the YAML line still physically exists.
    - Pytest: overdue project present + manual pick set on a different project → response.focus still points to overdue project; response.manual_focus.today points to the picked one; response.pressing[] still contains the overdue project.

## Unit 5: `FocusWidget` rendering

- [x] **5.1** Widen the typed client + `useHome` to include `manual_focus` (deps: 4.1, est: ~20m)
  - acceptance:
    - The `useHome()` hook return type exposes `manual_focus: {today: ManualPick|null, week: ManualPick|null}`.
  - verify:
    - `pnpm tsc --noEmit` passes after the type widening. A throwaway `console.log(home.manual_focus.today?.intent_title)` compiles.

- [x] **5.2** Render two manual-focus pills below the primary card in `FocusWidget.tsx` (deps: 5.1, est: ~60m)
  - acceptance:
    - R-5.1 — Primary card visually unchanged from pre-feature.
    - R-5.2 / R-5.3 / R-5.4 / R-5.5 — Today pill then This-week pill, populated or "Pick…" CTA depending on null/non-null.
    - R-5.7 — When heuristic focus and a pill point to the same (project, intent), the pill shows ✓ and "(aligned with critical)".
    - R-5.8 — Primary card is never hidden.
    - R-5.9 — When backend offline, pills show "—" and the picker action is disabled (reuse existing `useBackend` state).
  - verify:
    - Manual smoke: `pnpm tauri dev` against a fixture vault → screenshot matches three states (none picked, today picked alone, today picked + matches critical).
    - Vitest component test: render `FocusWidget` with `manual_focus.today = null`, assert pill shows "Pick today's focus". Render with populated pick, assert intent title appears.

- [x] **5.3** Wire `Change` and `Clear` controls on each populated pill (deps: 5.2, 6.1, est: ~30m)
  - acceptance:
    - R-5.6 — `Change` opens `FocusPickerModal` pre-selected on the slot. `Clear` issues `PUT /api/focus/<slot>` with `{clear: true}`.
  - verify:
    - Vitest: render populated pill, click `Clear`, assert a `PUT` to `/api/focus/today` with `{clear: true}` body is made via mocked fetch.

## Unit 6: FocusPickerModal

- [x] **6.1** Create `apps/desktop/src/components/FocusPickerModal.tsx` (deps: 5.1, est: ~75m)
  - acceptance:
    - R-6.1 — Modal overlay opens above the popup.
    - R-6.2 — Project list sourced from cached `/api/home.projects[]` (no extra fetch).
    - R-6.3 — Expanding a project fetches `GET /api/projects/{slug}` once per modal session.
    - R-6.4 — Clicking an intent issues `PUT /api/focus/{slot}` and closes on 2xx.
    - R-6.5 — Non-2xx keeps modal open, shows inline error, preserves selection.
    - R-6.6 — `Clear current pick` button calls `PUT /api/focus/{slot}` with `{clear: true}`.
    - R-6.7 — `Cancel` closes without any network request.
    - R-6.8 — Re-opening the modal refetches.
  - verify:
    - Vitest: open modal with mock projects[], assert project rows render.
    - Vitest: click expand → asserts single `/api/projects/{slug}` fetch; collapse + re-expand → no second fetch.
    - Vitest: click intent → asserts PUT with correct body; mock 200 → modal closes.
    - Vitest: mock 500 with `{error: "boom"}` → modal stays open with "boom" inline.

## Unit 7: `/sq-focus` CLI command

- [x] **7.1** Add slash command file `agent-pack/commands/sq-focus.md` and matching skill (deps: 3.2, est: ~60m)
  - acceptance:
    - R-7.1 — Command registered as `/sq-focus`.
    - R-7.2 — Bare invocation prints `Today: …` and `This week: …` (or `(none)`).
    - R-7.3 / R-7.4 — `today TAG/INTENT-SLUG` and `week TAG/INTENT-SLUG` set the slot.
    - R-7.5 — `today --clear` and `week --clear` clear the slot.
    - R-7.6 — Backend offline → prints "Backend offline — run `make backend-start`" and exits status 1.
    - R-7.7 — 404 from server → prints "No such intent: …" and exits status 1.
    - R-7.8 — All mutation flows via `/api/focus/*`; no direct file writes from the CLI.
  - verify:
    - Manual: with backend running, `/sq-focus today TEST-PROJECT/intent-slug` → reads back via `/sq-focus` and via Obsidian frontmatter.
    - Manual: kill backend, run `/sq-focus today X/Y` → expected offline message + exit 1.
    - Manual: `/sq-focus today BOGUS/BOGUS` → expected 404 message + exit 1.

## Unit 8: macOS reminder daemon "Focus now" button

- [x] **8.1** Export `active_intent_for(vault, project_slug)` helper from `apps/cli/lib/status_aggregator.py` (est: ~20m)
  - acceptance:
    - Wraps existing intent-resolution logic at `status_aggregator.py:163–181` without changing its behaviour.
    - Returns `intent_slug: str | None`.
  - verify:
    - Pytest: against a fixture with two intents on the same project, the more-recently-updated one is returned. With no intents, returns `None`.

- [ ] **8.2** Replace the `Open` button with `Focus now` in `agent-pack/companions/macos-reminders/reminder-daemon.sh` and wire the focus-set + browser-open flow (deps: 3.2, 8.1, mutex: daemon-script, est: ~60m)
  - acceptance:
    - R-8.1 — Dialog buttons become `{"Dismiss", "Snooze", "Focus now"}`, default `Focus now`.
    - R-8.2 — Active intent resolved via the new helper.
    - R-8.3 — `curl -sS --max-time 2 -X PUT http://127.0.0.1:3939/api/focus/today -H 'Content-Type: application/json' -d '{...}'`.
    - R-8.4 / R-8.5 — Failures (offline, missing intent) are logged but the daemon still proceeds to R-8.6.
    - R-8.6 — `open http://localhost:3939/projects/{TAG}` runs after the focus-set attempt.
    - R-8.7 — State file records `Focus now` analogously to the prior `Open`.
    - R-8.8 — Workday window / cadence / cap behaviour unchanged.
    - R-8.9 / R-10.3 — Dismiss and Snooze behave byte-identically to today.
  - verify:
    - Manual: `reminder-daemon.sh --force` against a vault with a critical item, click `Focus now` → verify the alerted project's active intent file gains `focus_today: <today>` and the browser opens.
    - Manual: stop the backend, repeat → log shows the curl failure, browser still opens.
    - Manual: click `Snooze` → confirm `snoozed_until` is set as before (regression check).

## Unit 9: Invariants & end-to-end verification

- [ ] **9.1** End-to-end golden-path verification against the HLD success criteria (deps: 5.3, 6.1, 7.1, 8.2, est: ~45m)
  - acceptance:
    - HLD success criteria #1–#11 all pass (see `docs/hld/manual-focus-pick.md`).
    - R-10.1 — `_recommend_focus()` unchanged (diff check).
    - R-10.2 — `/api/home.focus`, `.pressing[]`, `.projects[]` shape-identical (snapshot).
    - R-10.3 — Daemon polling/window/cadence/cap unchanged (manual snooze regression).
    - R-10.4 — `grep -rn "state.json" apps/backend apps/cli/lib apps/desktop/src` returns no new references introduced by this feature.
    - R-10.5 — `grep -rn "focus_today\|focus_week" apps/desktop/src-tauri/` returns nothing.
  - verify:
    - Run `make test-cli` → green.
    - Walk the 11 HLD success criteria one by one, tick each in a `.devlocal/<user>/manual-focus-pick/checklist.md`.
    - Capture the new `/api/home` snapshot under `apps/backend/tests/snapshots/` so future regressions are caught.
