# Estimate↔Actual Reconciliation — Low-Level Design

## Architecture

### Data model (new intent frontmatter keys)
Written to an intent file `01-Proyectos-Activos/<project_slug>/<intent_slug>.md`, alongside the
existing `time_invested_minutes`:

| Key | Type | Source |
|-----|------|--------|
| `estimate_user_minutes` | int | raw user input (minutes) |
| `estimate_multiplier`   | float | `estimate_buffer.get_multiplier()` value applied |
| `estimate_minutes`      | int | adjusted estimate = `adjust_estimate()["adjusted_minutes"]` |

Existing (unchanged): `time_invested_minutes` (int, cumulative actual across completed sessions).

All three estimate keys are written together in one frontmatter update so they never disagree.
`write_frontmatter` (`intent_parser.py:137`) is a verified per-key **upsert** — it leaves untouched
keys byte-identical — so writing the three estimate keys does not disturb `time_invested_minutes`
(the same merge semantics `_update_time_invested` already relies on, `server.py:1031`).

**Read-side type note (critical):** `_parse_yaml_subset` (`intent_parser.py:117`) returns every
frontmatter scalar as a **string**. So `estimate_minutes`/`estimate_user_minutes`/
`estimate_multiplier` come back as `"135"`, `"45"`, `"3.0"` — never as numbers. `_build_pick`
already defends against this for the existing field (`int(fm.get("time_invested_minutes") or 0)`,
`focus_picker.py:203`). `estimate_minutes` is stored as informational; `estimate_multiplier` is
stored but **not displayed** in v1.

### Variance is derived, never stored (key invariant)
Variance is **computed at read time** from the two stored numbers — it is NOT persisted. With two
durable source values, a stored variance could only drift; deriving it guarantees the displayed
number always matches the data. (This deliberately deviates from the PO's "store variance"
wording — see Key Decisions.)

Derivation (pure arithmetic, scripts-only). **Every value is coerced with a tolerant
`int()`/`float()` wrapper inside a try/except — any non-coercible/malformed value is treated as
absent and never raises** (mirrors `int(... or 0)` in `_build_pick`):
```
estimate_minutes      = coerce_int(fm.get("estimate_minutes"))        # None if missing/malformed
time_invested_minutes = coerce_int(fm.get("time_invested_minutes"))   # None if missing/malformed
have_estimate = estimate_minutes is not None and estimate_minutes > 0
have_actual   = time_invested_minutes is not None and time_invested_minutes > 0
# variance only when BOTH present:
variance_minutes = time_invested_minutes - estimate_minutes               # signed
variance_ratio   = round(time_invested_minutes / estimate_minutes, 2)
```
- `variance_ratio` is computed against the **adjusted** `estimate_minutes` (the number the user
  actually planned around) — this is the multiplier-calibration signal (ratio > 1 ⇒ padding was
  too low; < 1 ⇒ too high). The raw `estimate_user_minutes` is also surfaced so the user sees gut
  guess → plan → actual, but the headline ratio is actual ÷ adjusted.

### Components & flow

**1. Estimate engine — `apps/cli/lib/estimate_buffer.py`**
- Add `apply_estimate_to_intent(vault_path, intent_id, minutes) -> dict`: resolves the intent file,
  calls `adjust_estimate(minutes)`, writes the three keys via `intent_parser.write_frontmatter`,
  returns the stored dict. Atomic write (reuse existing temp+replace).
- **Resolution scope (authoritative): `01-Proyectos-Activos` only.** The CLI `--intent <id>` path
  resolves the id within WIP projects using the same scope as `_iter_intent_paths`
  (`focus_picker.py:125`) — *not* a whole-vault `rglob`. The API path resolves the deterministic
  `01-Proyectos-Activos/<project_slug>/<intent_slug>.md` pattern (same as `set_manual_focus`,
  `focus_picker.py:237`, and `_update_time_invested`, `server.py:1028`). An intent outside
  `01-Proyectos-Activos` (e.g. `03-Areas`, `02-Parking-Lot`) is **rejected** — estimate-setting,
  actual-tracking, and variance display must share one scope so an estimate can never be set where
  variance will never render. Do not introduce a third scanner; do not reuse the vault-wide
  `_find_note` (`server.py:2101`).
- `main()` gains an optional `--intent <intent-id>`: when present, persist instead of just print.

**1b. Variance helper — co-located in `apps/cli/lib/estimate_buffer.py`** (not a new module)
- Add `estimate_variance(frontmatter: dict) -> dict`: the read-side counterpart of the same domain
  concept. Coerces the three estimate keys + `time_invested_minutes` tolerantly (see Derivation),
  returns `{estimate_user_minutes, estimate_minutes, time_invested_minutes, variance_minutes,
  variance_ratio, has_variance}` with `None`s where a side is absent. Never raises.

**2. CLI surface — `apps/cli/squirrel`**
- `squirrel estimate --minutes N --intent <id>` (and `--hours`/`--estimate` variants) persists and
  prints the stored estimate. Without `--intent`, behavior is unchanged (print only).

**3. Backend — `apps/backend/server.py`**
- New endpoint `PUT /api/intent/estimate` (body `{project_slug, intent_slug, minutes}`) →
  `apply_estimate_to_intent`, **then `self._invalidate_vault_cache(ctx)`** (every sibling mutating
  handler does this — checkout `server.py:1059`, focus-put `1019`), return stored estimate.
  `do_PUT`/OPTIONS already advertise PUT (`server.py:456,463`), so this fits existing conventions.
- **Single variance injection point: `_build_pick` (`focus_picker.py:170`).** That is the only
  object carrying `time_invested_minutes` to *both* UIs (`manual_focus` in `/api/home`,
  consumed by `FocusWidget.tsx:95` and `HomePage.tsx:156`). Call `estimate_variance(fm)` there with
  the already-parsed frontmatter and merge the fields onto the pick. The other focus object,
  `focus_payload` (built from `recommended_focus`, `server.py:778`), carries no time data and is
  **not** touched. (There is no `_focus` symbol — the earlier draft was wrong.)
- No LLM import, no outbound call (consistent with server.py importing no LLM SDK).

**4. Desktop popup — `apps/desktop/src`**
- `FocusWidget.tsx` (which already renders `time_invested_minutes`) gains:
  - a "Set estimate" affordance (small input/modal) → `PUT /api/intent/estimate`;
  - a variance line when `has_variance`: `guessed 45m · est 2h15m · actual 2h10m · 1.0×` using
    neutral copy (raw guess is shown, headline ratio is actual ÷ adjusted).
- `FocusPickerModal.tsx` gains an optional estimate input at pick time. It posts to
  `PUT /api/intent/estimate` **after** the focus-pick succeeds, as a best-effort secondary write:
  focus-pick success never depends on the estimate write, and an estimate failure surfaces a
  non-blocking warning (the pick still stands). The two writes are disjoint-key RMW cycles.
- API client (`apps/desktop/src/api/client.ts`) gains the `setEstimate` call + estimate/variance
  fields on the manual-pick type.

**5. Web SPA — `apps/backend/app`**
- `HomePage.tsx` (renders `time_invested_minutes` today) gains the same estimate-set input and the
  variance line.

### Neutral-framing copy set (single source for all surfaces)
Defined once (e.g. a small constant map) and reused desktop + web:
- ratio ≈ 1 (0.85–1.15): "about right — learning your pace"
- ratio > 1.15: "ran longer than planned — learning your pace"
- ratio < 0.85: "finished ahead of plan"
- No estimate: show actual only, no variance line.
- Estimate, no actual: "est <x> · not started yet".
Forbidden words anywhere in variance copy: "over budget", "missed", "failed", "behind", "blew".

## Constraints
- Markdown frontmatter is the source of truth; SQLite holds only the existing time-series
  (`work_sessions`). No new SQLite table.
- Estimates are per-intent and resolve to `01-Proyectos-Activos/<project>/<intent>.md` only
  (Areas/Parking/Archive rejected — see component 1).
- Frontmatter writes are atomic **per `write_frontmatter` call** (temp + `os.replace`,
  `intent_parser.py:266`). There is no cross-process file lock today (pre-existing). A concurrent
  estimate-write and checkout `_update_time_invested` touch *disjoint* keys, so the merge is safe;
  but two overlapping read-modify-write cycles are last-writer-wins at the file level — an accepted
  pre-existing risk, not a new guarantee. The EARS does not claim stronger.
- Quick-Task exclusion is **structural, not a special-case check**: `QT-NNN` files never flow
  through `_iter_intent_paths`/`_build_pick`, and `01-Proyectos-Activos`-scoped resolution won't
  match them — so they are inherently excluded from estimate-setting and variance display.
- Pure stdlib (CLI), no new dependencies; no LLM, no network for any of this feature's math.
- Spanish/English vocabulary handling follows existing `vocabulary.py` conventions for any
  user-visible label routed through the web UI.

## Key Decisions
- **Derive variance, don't store it.** Two stored numbers are the single source of truth; a stored
  variance is redundant and can drift — the exact failure mode this feature exists to fight.
  Deviation from the PO draft AC is intentional and improves the invariant.
- **Ratio is actual ÷ adjusted estimate** (not ÷ raw guess) as the headline, because that is the
  multiplier-calibration signal; the raw guess is still displayed for the gut-vs-reality insight.
- **Comparison is at the intent level** (cumulative `time_invested_minutes` vs whole-intent
  estimate) — matches how actuals already accumulate; no per-session variance in v1.
- **Reuse checkout, add no daemon.** Variance becomes meaningful after the existing checkout
  updates `time_invested_minutes`; nothing new is scheduled.
- **One estimate per intent in v1.** Re-running `estimate --intent` overwrites; no history of
  estimates (re-estimation is out of scope).
- **Clearing is supported** via the existing `_DELETE` sentinel (`intent_parser.py:131`, already
  used by `focus_picker.py:254`) — removing all three estimate keys in one atomic write. Cheap,
  no new primitive; in scope for v1 (R-1.7).
- **Scope = `01-Proyectos-Activos` only.** Estimate-setting, actual-tracking, and variance display
  share one directory scope so an estimate can never be set where variance will never render.

## Out of Scope
- **R-2.5 (deferred to a follow-up):** in-modal estimate entry at focus-pick time. The focus-row
  `+ estimate` / `edit estimate` affordance (R-2.4 / R-2.6) covers setting an estimate on the
  just-picked intent, so this is a one-fewer-click convenience, not a capability gap.
- Aggregate calibration / auto-tuning the multiplier from accumulated variance.
- Re-estimation history (multiple estimates over time per intent).
- Charts / timeline / visual time representation.
- Per-chunk estimates (`chunk_helper.py`).
- Variance notifications/nudges; gamification.
- Quick Tasks (`QT-NNN`) — they are explicitly excluded from focus/estimate scanners.
