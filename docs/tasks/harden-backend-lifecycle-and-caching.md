# Harden Backend Lifecycle + Caching — Tasks

Source specs: `docs/hld/harden-backend-lifecycle-and-caching.md`, `docs/lld/harden-backend-lifecycle-and-caching.md`.
EARS: **R-9.1–R-9.13 in `docs/ears/phase-2-data-plane-and-desktop-popup.md` (Unit 9)** — these supersede R-1.7 and R-7.1 and are not duplicated into a separate EARS file.

> Back-filled after implementation. Implementation units are checked because the code already shipped on this branch (`apps/backend/cache.py`, `apps/desktop/src-tauri/src/backend_supervisor.rs`, cached `notif_db` in `tray_alerts.rs`, `externalBin` in `tauri.conf.json`). The automated-test units (Unit D) are **left unchecked** — those test files do not yet exist and are the real remaining work.

Rollout order (LLD §6): **cache first, SQLite-conn cache second, sidecar third** — the two cache fixes are pure-internal, low-risk wins; the sidecar inverts the lifecycle contract and needs build-pipeline wiring, so it lands last.
```
A (vault scan cache)      B (SQLite conn cache)
   pure-internal             pure-internal
        │                        │
        └──────────┬─────────────┘
                   C (backend supervisor / sidecar)
                   inverts lifecycle; build wiring
                   │
                   D (tests — cache, invalidation, adoption, conn)  ← remaining
```

---

## Unit A: Vault scan cache — `apps/backend/cache.py` (new) + `server.py`

- [x] **A.1** `cache.py` — `get_or_compute` / `invalidate` / `stats_snapshot` (est: ~40m)
  - acceptance:
    - R-9.8 — Process-local cache keyed `(vault_path, scan_kind)` with a `DEFAULT_TTL_SECONDS = 25.0` TTL; `get_or_compute` returns the cached value while fresh, else computes (outside the lock), stores, and returns. Stdlib only (`time.monotonic`, `threading.RLock`).
    - R-9.9 — `invalidate(vault_path, scan_kind=None)` drops matching entries and returns the eviction count; `None` kind drops all kinds for the vault.
    - R-9.10 — `stats_snapshot()` exposes `entries`, `hit_rate`, `last_evicted_at`.
  - verify:
    - Hit path: two same-key calls inside TTL return the same object, `compute` called once. Expiry: past TTL (monkeypatched clock) recomputes. Invalidate: next call recomputes. (See D.1.)

- [x] **A.2** Wire cache into `api_home` (deps: A.1, est: ~20m)
  - acceptance:
    - R-9.8 — `aggregate_status`, `scan_vault_deadlines`, `scan_vault_reminders` each go through `get_or_compute(vault, kind, lambda: …)`; on a 300-file vault this cuts ~900 reads / 30 s to ~30 reads / 30 s.
    - Each scanner keeps its existing best-effort `try/except` fallback shape.
  - verify:
    - Manual: hit `/api/home` repeatedly inside 25 s → `/api/cache/stats` `hit_rate` climbs toward 1.0; first call after TTL boundary re-scans.

- [x] **A.3** Write-path invalidation (deps: A.1, est: ~20m)
  - acceptance:
    - R-9.9 — `POST /api/notes` invalidates `(vault, "status")` and `(vault, "deadlines")`; `POST /api/focus` invalidates `(vault, "status")`; vault switch needs no invalidation (new vault has its own key). Invalidation runs before the JSON response.
  - verify:
    - Integration: POST a note with a deadline, then GET `/api/home` inside the TTL window → the new deadline appears in `pressing[]`. (See D.2.)

- [x] **A.4** `GET /api/cache/stats` observability endpoint (deps: A.1, est: ~10m)
  - acceptance:
    - R-9.10 — Registers alongside other GET routes; returns `stats_snapshot()`.
  - verify:
    - `curl http://127.0.0.1:3939/api/cache/stats | python3 -m json.tool` returns `entries` / `hit_rate` / `last_evicted_at`.

## Unit B: SQLite connection cache — `apps/desktop/src-tauri/src/tray_alerts.rs`

- [x] **B.1** Cache the connection on `TauriNotificationState` (est: ~25m)
  - acceptance:
    - R-9.11 — Add `notif_db: Option<Mutex<rusqlite::Connection>>` (inner `Mutex`, separate from the outer state mutex so the DB lock is held briefly without blocking unrelated state mutations); `None` until init succeeds.
  - verify:
    - `cargo build` succeeds; field present and populated once.

- [x] **B.2** Rewrite `init_notif_db` as a one-time startup op (deps: B.1, est: ~20m)
  - acceptance:
    - R-9.12 — `init_notif_db` opens the connection once, runs `PRAGMA journal_mode=WAL; busy_timeout=5000; synchronous=NORMAL;` and the `CREATE TABLE/INDEX IF NOT EXISTS`, and returns the `Connection` to be stored in state (instead of opening-then-dropping per call).
    - Called once in `start_polling`; on failure logs at WARN and leaves `notif_db = None`.
  - verify:
    - `cargo build`; manual: notifications DB opened once at startup, reused thereafter.

- [x] **B.3** `with_conn` helper + migrate the connection-opening touchpoints (deps: B.2, est: ~30m)
  - acceptance:
    - R-9.11 — `with_conn(app, |conn| …)` borrows the cached connection via a `MutexGuard`; `insert_notification_if_new` and `unread_count` are converted from `Connection::open(db_path)` to `with_conn`.
    - R-9.13 — With `busy_timeout=5000`, `rusqlite` retries internally; a residual `SQLITE_BUSY` is logged at WARN and the INSERT is skipped (the next 30 s poll retries the dedup-and-INSERT, so nothing is permanently lost).
  - verify:
    - `cargo build`; manual: insert/read a notification through the cached path; no per-call `Connection::open` remains in the two touchpoints.

## Unit C: Backend supervisor (sidecar) — `apps/desktop/src-tauri`

- [x] **C.1** Wire PyInstaller binary into the Tauri bundle (est: ~40m)
  - acceptance:
    - R-9.1 — `tauri.conf.json` `bundle.externalBin: ["bin/squirrel-backend"]` ships the frozen backend inside the `.app`; capabilities grant `shell:allow-execute` + `shell:allow-spawn` for the `squirrel-backend` sidecar; `tauri-plugin-shell = "2"` added to `Cargo.toml`.
    - Dev workflow unchanged: PyInstaller runs only for `tauri build` (release), not `tauri dev` (dev finds `make backend-start` via adoption).
  - verify:
    - `pnpm tauri build` produces a `.app` containing `squirrel-backend` under `Contents/Resources/`; `tauri dev` still uses the dev backend.

- [x] **C.2** `backend_supervisor.rs` — spawn-or-adopt (deps: C.1, est: ~45m)
  - acceptance:
    - R-9.1 / R-9.2 — At startup, `port_in_use(3939)` (200 ms TCP connect) → **Adopted** (no spawn, `child = None`); else `sidecar("squirrel-backend").args(["--port","3939"]).spawn()` → **Managed** with the `CommandChild` stored in state; spawn/resolution failure → **Failed**.
    - stdout/stderr drained to the `backend` tracing target.
  - verify:
    - Manual: fresh launch with no backend → Managed + one child; with launchd backend bound → Adopted + no child. (Adoption test: D.3.)

- [x] **C.3** Startup health-poll + 30 s health-check tick + respawn policy (deps: C.2, est: ~35m)
  - acceptance:
    - R-9.4 — Startup: poll `/api/me` every 1 s up to 10 s; first 2xx → tray Normal + emit `squirrel:backend-up`; never → tray Error.
    - R-9.5 — `health_check_tick` runs on the existing 30 s heartbeat; 3 consecutive failures flip the tray to Error.
    - R-9.6 — Managed mode respawns within bounds: `MAX_RESPAWNS_PER_HOUR = 5`, `RESPAWN_COOLDOWN = 60s` (sliding 1 h window).
  - verify:
    - Manual: `kill -9` the child → within ~90 s tray flips to Error, respawn within another 60 s; respawn storms are bounded.

- [x] **C.4** Graceful shutdown on exit (deps: C.2, est: ~20m)
  - acceptance:
    - R-9.3 — On `RunEvent::ExitRequested`, Managed mode `child.kill()` (SIGTERM), waits 2 s, then `libc::kill(pid, SIGKILL)` if still alive; Adopted mode leaves the external backend running.
  - verify:
    - Manual: Quit Squirrel → `squirrel-backend` PID gone within ~3 s (Managed); launchd backend survives (Adopted).

- [x] **C.5** Visible error state in the tray (deps: C.2, est: ~20m)
  - acceptance:
    - R-9.7 — On Failed/3-strikes, `tray::set_state(IconState::Error)` and the menu swaps "No pressing items" for "Backend unavailable — see ~/.squirrel/squirrel.log" (new `ids::BACKEND_ERROR`, one conditional in `build_menu`).
  - verify:
    - Manual: with no backend reachable, the tray shows the Error icon and the "Backend unavailable" entry instead of an empty menu.

## Unit D: Tests — remaining work

- [ ] **D.1** `apps/backend/tests/test_cache.py` (deps: A.1, est: ~30m)
  - acceptance:
    - R-9.8 / R-9.9 / R-9.10 — hit path (same key inside TTL → `compute` once), expiry path (monkeypatched `time.monotonic` past TTL → recompute), invalidate (recompute after `invalidate(vault)`), stats (`hit_rate` reflects ratio, `last_evicted_at` set on invalidate).
  - verify:
    - `pytest apps/backend/tests/test_cache.py` green.

- [ ] **D.2** `apps/backend/tests/test_home_invalidation.py` (deps: A.3, est: ~30m)
  - acceptance:
    - R-9.9 — POST a note via the test HTTP harness, then GET `/api/home`; the new note's deadline shows up in `pressing[]` despite being inside the TTL window (proves end-to-end write invalidation).
  - verify:
    - `pytest apps/backend/tests/test_home_invalidation.py` green.

- [ ] **D.3** `apps/desktop/src-tauri/tests/` — adoption + cached-conn (deps: B.3, C.2, est: ~40m)
  - acceptance:
    - R-9.2 — `supervisor_adoption.rs`: bind `127.0.0.1:3939` in the test thread, call `spawn_or_adopt`, assert mode `Adopted` and `child` is `None`.
    - R-9.11 / R-9.13 — `notif_db_cached.rs`: open a temp DB via `init_notif_db`, insert via cached `with_conn`, read the row back; best-effort busy-timeout test proves a contended call waits-then-succeeds rather than instantly erroring.
  - verify:
    - `cargo test` (src-tauri) green.
