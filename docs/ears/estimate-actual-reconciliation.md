# Estimate↔Actual Reconciliation — EARS Specifications

Arrow of intent: HLD → LLD → **EARS** → code/tests.
Scope: persist an ADHD-adjusted estimate per intent; derive estimate-vs-actual variance; surface it
on the desktop popup and web HomePage with neutral framing. Local, scripts-only, no LLM/network.

**v1 implementation status:** All requirements shipped EXCEPT **R-2.5 (deferred)** — entering an
estimate *inside the focus-pick modal* at pick time. The capability is covered adjacently by the
`+ estimate` / `edit estimate` affordance on the focus row (R-2.4 desktop, R-2.6 web), which sets
an estimate on the just-picked intent; only the in-modal entry step is deferred.

## Unit 1: Estimate persistence

| ID | EARS statement |
|----|----------------|
| R-1.1 | WHEN a user sets a time estimate for an intent, THE SYSTEM SHALL compute the adjusted estimate via the existing focus multiplier (`estimate_buffer.adjust_estimate`) and write `estimate_user_minutes`, `estimate_multiplier`, and `estimate_minutes` to that intent's Markdown frontmatter in a single atomic update. |
| R-1.2 | THE SYSTEM SHALL persist the three estimate keys such that the values survive a vault re-scan and a backend restart. |
| R-1.3 | WHEN an estimate is set on an intent that already has an estimate, THE SYSTEM SHALL overwrite all three estimate keys with the new values (one estimate per intent; no history). |
| R-1.4 | THE SYSTEM SHALL resolve the target intent **only within `01-Proyectos-Activos`** — the API path via the deterministic `01-Proyectos-Activos/<project_slug>/<intent_slug>.md`, the CLI `--intent <id>` path via the WIP-scoped intent set (same scope as `_iter_intent_paths`). It SHALL NOT use a vault-wide scan. |
| R-1.5 | IF the target intent does not exist **or resolves outside `01-Proyectos-Activos`** (e.g. `03-Areas`, `02-Parking-Lot`, `06-Archive`), THE SYSTEM SHALL return an error and SHALL NOT create a file or write partial frontmatter. |
| R-1.6 | THE SYSTEM SHALL NOT modify `time_invested_minutes` or any non-estimate frontmatter when writing an estimate (relying on the verified per-key upsert of `write_frontmatter`). |
| R-1.7 | WHEN a user clears an estimate, THE SYSTEM SHALL delete all three estimate keys in a single atomic update (via the existing `_DELETE` sentinel) and SHALL leave `time_invested_minutes` untouched. |

## Unit 2: Set-estimate surfaces

| ID | EARS statement |
|----|----------------|
| R-2.1 | THE SYSTEM SHALL accept an optional `--intent <intent-id>` argument on the `squirrel estimate` command; WHEN present THE SYSTEM SHALL persist the estimate to that intent (per Unit 1) and print the stored result. |
| R-2.2 | WHERE `squirrel estimate` is invoked without `--intent`, THE SYSTEM SHALL preserve current behavior (compute and print only; persist nothing). |
| R-2.3 | THE SYSTEM SHALL expose `PUT /api/intent/estimate` accepting `{project_slug, intent_slug, minutes}`, persisting the estimate (per Unit 1), invalidating the vault cache, and returning the stored estimate object. |
| R-2.4 | WHEN the desktop popup user sets an estimate on the focused intent, THE SYSTEM SHALL call `PUT /api/intent/estimate` and reflect the stored estimate without a full reload. |
| R-2.5 | *(DEFERRED — not in v1.)* WHERE a user picks an intent as focus via the focus-pick flow, THE SYSTEM SHALL allow an optional estimate to be entered in the pick modal, persisting it via the same endpoint; omitting it SHALL leave the intent without an estimate. |
| R-2.6 | THE SYSTEM SHALL provide the same set-estimate affordance on the web SPA intent/home view. |
| R-2.7 | IF `minutes` is missing, non-numeric, ≤ 0, or above a sane upper bound (e.g. > 6000 min / 100h), THE SYSTEM SHALL reject the request with a client error and persist nothing. |

## Unit 3: Variance derivation

| ID | EARS statement |
|----|----------------|
| R-3.1 | WHEN an intent has both `estimate_minutes` > 0 and `time_invested_minutes` > 0, THE SYSTEM SHALL derive `variance_minutes` = `time_invested_minutes` − `estimate_minutes` and `variance_ratio` = `time_invested_minutes` ÷ `estimate_minutes` (rounded to 2 decimals). |
| R-3.2 | THE SYSTEM SHALL derive variance on read and SHALL NOT persist `variance_minutes` or `variance_ratio` to frontmatter or any store. |
| R-3.3 | THE SYSTEM SHALL compute `variance_ratio` against the adjusted `estimate_minutes` while also exposing `estimate_user_minutes` (the raw guess) in the same payload. |
| R-3.4 | WHILE computing or persisting any part of this feature, THE SYSTEM SHALL use scripts-only arithmetic with no LLM import and no outbound network request. |
| R-3.5 | THE SYSTEM SHALL inject the derived variance fields at the single `_build_pick` site (`focus_picker.py`) so the one `manual_focus` object feeds both the desktop popup and the web HomePage; it SHALL NOT add variance to the `recommended_focus`-derived payload (which carries no time data). |
| R-3.6 | WHEN deriving variance, THE SYSTEM SHALL coerce frontmatter scalar values (returned as strings by the parser) to numbers, and SHALL treat any missing or non-coercible value as absent without raising. |

## Unit 4: Variance display & framing

| ID | EARS statement |
|----|----------------|
| R-4.1 | WHEN an intent has a derivable variance, THE desktop popup SHALL display the raw guess, adjusted estimate, actual, and `variance_ratio` together on the focus/intent card (e.g. "guessed 45m · est 2h15m · actual 2h10m · 1.0×"). |
| R-4.2 | WHEN an intent has a derivable variance, THE web HomePage SHALL display the same grouping. |
| R-4.3 | THE SYSTEM SHALL render variance copy only from the approved neutral-framing copy set and SHALL NOT use shame/failure language ("over budget", "missed", "failed", "behind", "blew"). |
| R-4.4 | THE SYSTEM SHALL select variance copy by ratio band: ratio 0.85–1.15 → "about right — learning your pace"; ratio > 1.15 → "ran longer than planned — learning your pace"; ratio < 0.85 → "finished ahead of plan". |
| R-4.5 | WHERE an intent has an estimate but no tracked actual (no checkout yet), THE SYSTEM SHALL display the estimate alone and SHALL NOT display a variance. |
| R-4.6 | WHERE an intent has tracked actual time but no estimate, THE SYSTEM SHALL display the actual alone and SHALL NOT display a variance. |

## Unit 5: Backward compatibility & invariants

| ID | EARS statement |
|----|----------------|
| R-5.1 | WHEN an intent predating this feature (no estimate keys) is read, THE SYSTEM SHALL render its actual (if any) without variance and without raising an error. |
| R-5.2 | IF estimate frontmatter is partially present or malformed (e.g. `estimate_minutes` missing or non-numeric), THE SYSTEM SHALL treat the estimate as absent and SHALL NOT raise (per the coercion rule R-3.6). |
| R-5.3 | THE SYSTEM SHALL exclude Quick Tasks (`QT-NNN`, `quick_task: true`) from estimate setting and variance display; this exclusion is structural (QTs never resolve within `01-Proyectos-Activos` intent scanning), not a special-case check. |
| R-5.4 | THE SYSTEM SHALL perform each estimate frontmatter write atomically per `write_frontmatter` call (temp + replace) so a crash mid-write cannot leave a corrupt frontmatter block. No cross-process lock is claimed; a concurrent estimate-write and checkout touch disjoint keys. |
