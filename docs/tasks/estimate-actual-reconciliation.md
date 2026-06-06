# Estimate↔Actual Reconciliation — Tasks

Source specs: `docs/hld/estimate-actual-reconciliation.md`, `docs/lld/estimate-actual-reconciliation.md`, `docs/ears/estimate-actual-reconciliation.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Dependency layers:
```
A   (foundation: apply_estimate_to_intent + estimate_variance in estimate_buffer.py)
 │
 ├─ B   (CLI: squirrel estimate --intent)
 │
 ├─ C   (backend: PUT /api/intent/estimate + cache invalidation + validation)
 │
 └─ D   (variance injection in _build_pick → manual_focus payload)
          │
          ├─ E   (desktop typed client: setEstimate + estimate/variance fields)  ──► F (desktop UI)
          │
          └─ G   (web SPA: set-estimate input + variance line on HomePage)        [deps C, D]
                                                                                     │
                                                                                     H (backward-compat + structural-exclusion e2e)  [deps F, G]
```

## Unit 1: Estimate persistence & variance engine (`apps/cli/lib/estimate_buffer.py`)

- [x] **A.1** Add `apply_estimate_to_intent(vault_path, intent_id_or_slugs, minutes) -> dict` — resolve intent **within `01-Proyectos-Activos` only**, call `adjust_estimate`, write `estimate_user_minutes`/`estimate_multiplier`/`estimate_minutes` via `intent_parser.write_frontmatter` (one atomic call). (est: ~60m)
  - acceptance:
    - R-1.1 — writes the three keys in a single atomic frontmatter update.
    - R-1.2 — values survive vault re-scan / backend restart.
    - R-1.3 — re-setting overwrites all three keys (no history).
    - R-1.4 — resolution scoped to `01-Proyectos-Activos` (API: `<project>/<intent>.md`; CLI id: WIP-scoped like `_iter_intent_paths`); no vault-wide scan.
    - R-1.5 — non-existent **or out-of-scope** (`03-Areas`/`02-Parking-Lot`/`06-Archive`) intent → error, no file created, no partial write.
    - R-1.6 — `time_invested_minutes` and all non-estimate frontmatter untouched (per-key upsert).
    - R-5.4 — write is atomic per `write_frontmatter` call (temp + replace).
  - verify:
    - pytest: set estimate on a fixture WIP intent → assert 3 keys present, `time_invested_minutes` (if pre-set) byte-identical, body unchanged.
    - pytest: re-set with new minutes → all 3 keys overwritten, exactly one of each.
    - pytest: target an `03-Areas` intent → raises/returns error, file unmodified.
    - pytest: target missing intent id → error, no file created.

- [x] **A.2** Add estimate clear via `_DELETE` sentinel (`clear_estimate(...)` or `minutes=None` path). (deps: A.1, est: ~20m)
  - acceptance:
    - R-1.7 — clearing deletes all three estimate keys in one atomic update; `time_invested_minutes` untouched; no `null`/empty values left.
  - verify:
    - pytest: file with all 3 estimate keys + `time_invested_minutes` → clear → assert 3 keys gone, `time_invested_minutes` intact, no `null` written.

- [x] **A.3** Add `estimate_variance(frontmatter: dict) -> dict` (co-located in `estimate_buffer.py`) — tolerant coercion + derived variance. (deps: A.1, est: ~45m)
  - acceptance:
    - R-3.1 — both sides present & >0 → `variance_minutes = actual − estimate`, `variance_ratio = round(actual/estimate, 2)`.
    - R-3.2 — variance is returned, never written to frontmatter/any store.
    - R-3.3 — ratio computed against adjusted `estimate_minutes`; `estimate_user_minutes` (raw guess) also returned.
    - R-3.6 — coerces string scalars to numbers; missing/non-coercible → treated absent, never raises.
    - R-5.2 — partial/malformed estimate frontmatter → treated as absent, no raise.
  - verify:
    - pytest: fm with `estimate_minutes="135"`, `time_invested_minutes="130"` (strings) → ratio ≈ 0.96, no error.
    - pytest: fm with only `time_invested_minutes` → `has_variance=False`, actual surfaced.
    - pytest: fm with only `estimate_minutes` → `has_variance=False`, estimate surfaced.
    - pytest: fm with `estimate_minutes="abc"` → treated absent, no raise.

## Unit 2: Set-estimate surfaces — CLI & backend

- [x] **B.1** Add optional `--intent <intent-id>` to `squirrel estimate` (`apps/cli/squirrel` + `estimate_buffer.main`). (deps: A.1, est: ~30m)
  - acceptance:
    - R-2.1 — with `--intent`, persists (per Unit 1) and prints stored result.
    - R-2.2 — without `--intent`, behavior unchanged (compute + print only, persist nothing).
  - verify:
    - cli test: `squirrel estimate --minutes 30 --intent <wip-id>` → intent file gains 3 keys; stdout shows stored dict.
    - cli test: `squirrel estimate --minutes 30` (no `--intent`) → no file write anywhere.

- [x] **C.1** Add `PUT /api/intent/estimate` handler + route in `apps/backend/server.py`. (deps: A.1, est: ~45m)
  - acceptance:
    - R-2.3 — accepts `{project_slug, intent_slug, minutes}`, persists, **invalidates vault cache** (`self._invalidate_vault_cache(ctx)`), returns stored estimate.
    - R-2.7 — `minutes` missing / non-numeric / ≤0 / >6000 → client error, persist nothing.
    - R-3.4 — no LLM import, no outbound request.
  - verify:
    - api test: PUT valid body → 200, stored estimate returned, intent file updated.
    - api test: PUT `minutes=0` and `minutes=99999` → 4xx, file unchanged.
    - api test: assert no `anthropic`/`httpx`/`requests` import path touched (consistent with existing server.py).

## Unit 3: Variance in the read payload

- [x] **D.1** Inject `estimate_variance(fm)` fields into `_build_pick` (`apps/cli/lib/focus_picker.py`) so `manual_focus` carries estimate + variance to both UIs. (deps: A.3, est: ~30m)
  - acceptance:
    - R-3.5 — variance fields injected only at `_build_pick`; `recommended_focus`-derived payload untouched.
    - R-4.5 (data) — estimate present, no actual → estimate surfaced, no variance.
    - R-4.6 (data) — actual present, no estimate → actual surfaced, no variance.
  - verify:
    - pytest on `get_manual_focus`: fixture intent with estimate+actual → pick dict includes `estimate_minutes`, `estimate_user_minutes`, `variance_minutes`, `variance_ratio`, `has_variance=True`.
    - pytest: estimate-only and actual-only fixtures → `has_variance=False`, correct single value present.

## Unit 4: Desktop popup display & input (`apps/desktop/src`)

- [x] **E.1** Widen the manual-pick type + add `setEstimate` to `apps/desktop/src/api/client.ts`. (deps: C.1, D.1, est: ~20m)
  - acceptance: typed `setEstimate(project_slug, intent_slug, minutes)` → `PUT /api/intent/estimate`; ManualPick type gains estimate/variance fields.
  - verify: typecheck passes (`pnpm -F squirrel-desktop build` or tsc); manual call hits endpoint.

- [x] **F.1** `FocusWidget.tsx`: "Set estimate" affordance + variance line (copy bands inlined here). (deps: E.1, est: ~60m)
  - acceptance:
    - R-2.4 — setting an estimate calls the endpoint and reflects without full reload.
    - R-4.1 — when `has_variance`, shows raw guess + est + actual + ratio (e.g. "guessed 45m · est 2h15m · actual 2h10m · 1.0×").
    - R-4.3 — copy only from neutral set; forbidden words absent.
    - R-4.4 — ratio band copy: 0.85–1.15 "about right — learning your pace"; >1.15 "ran longer than planned — learning your pace"; <0.85 "finished ahead of plan".
    - R-4.5 — estimate-only intent shows estimate alone, no variance.
  - verify:
    - manual/devtools: set estimate, check in/out, confirm variance line + band copy; grep component for forbidden words → none.

- [ ] **F.2** `FocusPickerModal.tsx`: optional estimate input at pick time (best-effort secondary write). (deps: E.1, est: ~30m)
  - DEFERRED (v1): the `+ estimate` / `edit estimate` affordance on the focus row (F.1) already lets the user set an estimate on the just-picked intent immediately after picking. In-modal entry at pick time (R-2.5) is the only deferred slice; everything else in the feature is implemented.
  - acceptance:
    - R-2.5 — optional estimate entered at pick persists via `PUT /api/intent/estimate` **after** focus-pick succeeds; omitting it leaves intent without an estimate; pick success never depends on estimate write.
  - verify: pick with estimate → both focus token and estimate written; pick without → only focus token; simulate estimate failure → pick still stands, non-blocking warning.

## Unit 5: Web SPA display & input (`apps/backend/app`)

- [x] **G.1** `HomePage.tsx`: set-estimate input + variance line (copy bands inlined here). (deps: C.1, D.1, est: ~50m)
  - acceptance:
    - R-2.6 — same set-estimate affordance on the web home/intent view.
    - R-4.2 — shows the same guess/est/actual/ratio grouping when `has_variance`.
    - R-4.3 / R-4.4 — neutral copy + ratio bands (inlined; not shared with desktop).
    - R-4.4 (display) — estimate-only → estimate alone; actual-only → actual alone.
  - verify: `pnpm -F squirrel-web-ui build`; manual check in web UI — set estimate, see variance after a tracked session.

## Unit 6: Backward-compat & structural exclusion

- [x] **H.1** Backward-compat + Quick-Task exclusion verification (e2e/integration). (deps: F.1, G.1, est: ~30m)
  - acceptance:
    - R-5.1 — legacy intent (no estimate keys) renders actual (if any), no variance, no error.
    - R-5.3 — Quick Tasks (`QT-NNN`, `quick_task: true`) excluded from estimate-setting & variance — exclusion is structural (never resolve within `01-Proyectos-Activos` intent scanning), not a special-case check.
  - verify:
    - pytest: pre-feature fixture intent → `get_manual_focus` returns actual, `has_variance=False`, no exception.
    - test: attempt to resolve a `QT-NNN` id via `apply_estimate_to_intent` → not found / rejected; QTs never appear in `_build_pick` output.

---

## Coordination notes
- **Bottom-up order:** A → (B, C, D in parallel) → E → F → G → H. A is the god-node foundation; everything depends on it.
- **Parallelizable:** B (CLI), C (endpoint), D (payload) once A lands; F (desktop) and G (web) once E/D land — different apps, no shared code.
- **Mutex:** none — stories touch distinct files. A.1/A.2/A.3 all edit `estimate_buffer.py` (same author/session recommended; `mutex: estimate_buffer.py`).
- **No cross-page helper:** neutral-copy band logic is inlined in F.1 and G.1 separately (per project convention), not extracted to a shared module.
- **Pre-existing risk (not new):** concurrent estimate-write + checkout = last-writer-wins at file level (disjoint keys, safe in practice); no file lock exists today.

## Checkpoint: after A–D
- [ ] `make test-cli` green (engine + payload).
- [ ] PUT endpoint persists + invalidates cache; CLI `--intent` writes.
- [ ] Review before building UI (F/G).
