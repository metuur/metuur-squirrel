# LLD: Harden Backend Lifecycle + Caching

Status: proposed (2026-05-31)
Owner: Uncle Lead
Related EARS: R-9.1–R-9.13 (in `docs/ears/phase-2-data-plane-and-desktop-popup.md`, Unit 9), superseding R-1.7 and R-7.1
Supersedes: nothing on disk; first hardening pass on the Phase 2 lifecycle posture

---

## 1. Context & problem

Three risks identified in the prior stability/performance assessment compound into the same failure mode for real users: **the app appears to be running but silently shows nothing**.

- **Risk 1 — Backend not supervised.** `apps/desktop/src-tauri/src/lib.rs:47-167` never spawns or health-checks the Python backend. Phase 2 explicitly required the user to start the backend by hand (`make backend-start`) or install an optional launchd plist. The plist installer (`apps/backend/launchd/install.sh`) is also broken: it substitutes `__PYTHON__`/`__SERVER_PY__` placeholders that don't exist in the current `plist.template` (which only has `__BINARY__`/`__PORT__`/`__HOME__`). Net effect: an end user who runs the DMG installer gets a tray icon whose menus are permanently empty, with no on-screen explanation.
- **Risk 3 — Vault scanned 3× per 30s poll.** `server.py:476-549` calls `aggregate_status`, `scan_vault_deadlines`, and `scan_vault_reminders` sequentially on every `/api/home` request. Each is an independent `rglob("*.md")` over the vault. With a 300-file vault that is ~900 file reads + frontmatter parses every 30 seconds, all wall-clock-blocking the HTTP thread.
- **Risk 6 — `rusqlite::Connection::open()` on every poll.** `tray_alerts.rs:159, 179, 559-565` opens a brand-new SQLite connection on every `insert_notification_if_new`, `unread_count`, and `init_notif_db` call. Each open re-runs `PRAGMA journal_mode=WAL` and pays the page-cache cold-start cost.

This LLD bundles fixes for all three under a single rollout because the lifecycle fix and the cache fix interact: hardened supervision pushes the backend through more `/api/home` cycles, which makes the cache more important.

## 2. Goals & non-goals

**Goals**

- The user can install the DMG and get a working tray without touching a terminal, ever.
- `/api/home` median latency drops by ≥50% on a 300-file vault.
- SQLite churn in the tray poller goes from N opens per cycle to one open per app lifetime.
- The "silent empty tray" failure mode is replaced by a visible error state.
- No new external dependencies on the Rust or Python side that aren't already in `Cargo.toml`.

**Non-goals**

- Re-architecting the polling model itself (still 30 s, still HTTP, still tray-pulled). Push notifications, websockets, or a Rust-native scanner are out of scope.
- Changing the bundle format (still PyInstaller `--onefile`).
- Cross-platform: macOS only this round. Linux/Windows lifecycle is a separate LLD.
- Auth/CSP changes — still localhost-only.

## 3. NFRs introduced

This LLD is the contract for **R-9.1 through R-9.13** added to `docs/ears/phase-2-data-plane-and-desktop-popup.md` Unit 9. The new requirements explicitly **supersede R-1.7 and R-7.1** (which forbade Tauri-side backend supervision in Phase 2). The supersession is recorded inline in the EARS file.

Key NFRs the implementation must satisfy:

- R-9.1 / R-9.2: spawn-or-adopt the backend.
- R-9.3: graceful shutdown with SIGTERM → SIGKILL escalation.
- R-9.4 / R-9.5 / R-9.6: health-check cadence and respawn policy.
- R-9.7: visible error state when the binary can't be located.
- R-9.8 / R-9.9 / R-9.10: vault-scan cache with TTL, write-invalidation, observability endpoint.
- R-9.11 / R-9.12 / R-9.13: cached `rusqlite::Connection` with WAL + `busy_timeout`.

## 4. Design overview

The Tauri app gains a `backend_supervisor` module that runs alongside the existing `tray_alerts` poller and shares its 30 s heartbeat. The supervisor decides at startup whether to spawn a managed child (Tauri owns lifecycle) or adopt an externally-running backend (launchd or `make backend-start`). The backend's `/api/home` handler gains a process-local TTL cache around the three scanners. The Rust tray state gains a single cached SQLite connection that every notification helper borrows.

**Cold-launch sequence:**

```
1.  lib::run()  →  setup hook
2.  check if 127.0.0.1:3939 is taken  (TCP connect, 200ms budget)
       ├─ taken      → mode = Adopted ;  child = None
       └─ free       → mode = Managed ;  spawn ./resources/squirrel-backend --port 3939
                                          → child handle stored in state
3.  spawn health-check loop:
       wait up to 10s for first 2xx from /api/me  (poll every 1s)
         ├─ never succeeded     → tray icon = Error ; tray entry = "Backend unavailable"
         └─ succeeded           → tray icon = Normal ; emit "squirrel:backend-up"
4.  tray_alerts::start_polling()  (existing) takes over the 30s rhythm
5.  on app quit:
       if mode == Managed:  SIGTERM the child, wait 2s, SIGKILL if still alive
```

## 5. Detailed design

### 5.1 Backend sidecar lifecycle

#### Packaging assumption (from Step 1 investigation)

**The backend is packaged as a PyInstaller onefile binary by `scripts/build-dmg.sh`, but it is NOT wired into Tauri.** A frozen `squirrel-backend` exists at `dist/squirrel-backend` (8.6 MB) and `apps/backend/server.py` is already frozen-aware (`server.py:41-46, 62-66`). However, `tauri.conf.json` has no `bundle.externalBin` entry and no `beforeBundleCommand` to invoke PyInstaller as part of the Tauri build. The DMG produced by `scripts/build-dmg.sh` is a parallel installer that copies binaries to `/usr/local/bin/`-style locations — it is **not** the Tauri `.app` bundle. So today the user has two disjoint distribution paths, neither of which makes the Tauri `.app` self-sufficient.

**The design assumes** that PyInstaller is wired into the Tauri build via `bundle.externalBin` so the binary ships inside the `.app`. This is part of the implementation work (Step 1 of the rollout in §6).

#### Spawn strategy — opinion: use `tauri-plugin-shell` with `externalBin`, not `Command::new`

I'm choosing `tauri-plugin-shell`'s `sidecar()` API over `std::process::Command` because:
1. Tauri's bundler will automatically copy the binary to the right place inside `.app/Contents/Resources/` and rename it per-target-triple (`squirrel-backend-x86_64-apple-darwin`, etc.).
2. The plugin already handles platform-specific quirks (Windows hides the console window; macOS sets the right working dir).
3. The `CommandChild` returned has a typed `.kill()` for shutdown and `.write()` for stdin, both of which we need.

The alternative (raw `Command::new`) means hand-rolling the resource-path resolution and the per-OS sandbox/notarization quirks. Not worth the savings.

#### Tauri config snippet

```jsonc
// apps/desktop/src-tauri/tauri.conf.json
{
  "bundle": {
    "active": true,
    "targets": "all",
    "externalBin": ["bin/squirrel-backend"],
    "resources": []
  }
}
```

Plus the `tauri-plugin-shell` permission for the sidecar:

```json
// apps/desktop/src-tauri/capabilities/default.json
{
  "permissions": [
    "shell:allow-execute",
    {
      "identifier": "shell:allow-spawn",
      "allow": [{ "name": "squirrel-backend", "sidecar": true, "args": ["--port", "3939"] }]
    }
  ]
}
```

And `Cargo.toml`:

```toml
[dependencies]
tauri-plugin-shell = "2"
```

The PyInstaller `.spec` file moves into the Tauri build pipeline. `apps/desktop/package.json` gets a `prebuild` script:

```json
"scripts": {
  "tauri:prebuild": "pyinstaller --onefile --name squirrel-backend --distpath src-tauri/bin --paths ../../apps/cli/lib --add-data ../../apps/backend/app/dist:app/dist --clean ../../apps/backend/server.py"
}
```

#### Rust pseudocode — `backend_supervisor.rs`

```rust
// apps/desktop/src-tauri/src/backend_supervisor.rs
use std::sync::Mutex;
use std::time::Duration;
use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_PORT: u16 = 3939;
const HEALTH_URL: &str = "http://127.0.0.1:3939/api/me";
const STARTUP_BUDGET: Duration = Duration::from_secs(10);
const HEALTH_INTERVAL: Duration = Duration::from_secs(30);
const RESPAWN_COOLDOWN: Duration = Duration::from_secs(60);
const MAX_RESPAWNS_PER_HOUR: u32 = 5;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum SupervisionMode {
    Managed,   // we spawned it; we kill it on quit
    Adopted,   // someone else (launchd) runs it; we just monitor
    Failed,    // can't spawn AND nothing answers — tray shows Error
}

pub struct SupervisorState {
    pub mode: SupervisionMode,
    pub child: Option<CommandChild>,
    pub consecutive_failures: u32,
    pub respawn_timestamps: Vec<std::time::Instant>,
}

pub fn spawn_or_adopt<R: Runtime>(app: &AppHandle<R>) -> SupervisionMode {
    if port_in_use(BACKEND_PORT) {
        tracing::info!("backend supervisor: port 3939 already bound; adopting");
        return SupervisionMode::Adopted;
    }
    match app.shell().sidecar("squirrel-backend") {
        Ok(cmd) => match cmd.args(["--port", "3939"]).spawn() {
            Ok((mut rx, child)) => {
                // drain stdout/stderr to our own tracing target
                tauri::async_runtime::spawn(async move {
                    while let Some(ev) = rx.recv().await {
                        match ev {
                            CommandEvent::Stdout(line) | CommandEvent::Stderr(line) => {
                                tracing::debug!(target: "backend", "{}", String::from_utf8_lossy(&line));
                            }
                            CommandEvent::Terminated(payload) => {
                                tracing::warn!(?payload, "backend child terminated");
                            }
                            _ => {}
                        }
                    }
                });
                store_child(app, child);
                SupervisionMode::Managed
            }
            Err(e) => {
                tracing::error!(error = %e, "backend supervisor: spawn failed");
                SupervisionMode::Failed
            }
        },
        Err(e) => {
            tracing::error!(error = %e, "backend supervisor: sidecar resolution failed");
            SupervisionMode::Failed
        }
    }
}

fn port_in_use(port: u16) -> bool {
    use std::net::{SocketAddr, TcpStream};
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, Duration::from_millis(200)).is_ok()
}

/// Reuses the tray-alerts reqwest client; called from the existing 30s loop.
pub async fn health_check_tick<R: Runtime>(app: &AppHandle<R>, client: &reqwest::Client) {
    let ok = client.get(HEALTH_URL).timeout(Duration::from_secs(3))
        .send().await.map(|r| r.status().is_success()).unwrap_or(false);
    let state = app.state::<Mutex<SupervisorState>>();
    let mut s = state.lock().unwrap();
    if ok {
        s.consecutive_failures = 0;
        return;
    }
    s.consecutive_failures += 1;
    if s.consecutive_failures < 3 {
        return;
    }
    // 3 strikes — surface to user and (maybe) respawn
    let _ = crate::tray::set_state(app, crate::tray::IconState::Error);
    if s.mode == SupervisionMode::Managed && should_respawn(&mut s) {
        tracing::warn!("backend supervisor: respawning");
        drop(s); // release lock before spawn
        spawn_or_adopt(app);
    }
}

fn should_respawn(s: &mut SupervisorState) -> bool {
    let now = std::time::Instant::now();
    s.respawn_timestamps.retain(|t| now.duration_since(*t) < Duration::from_secs(3600));
    if s.respawn_timestamps.len() as u32 >= MAX_RESPAWNS_PER_HOUR {
        return false;
    }
    if let Some(last) = s.respawn_timestamps.last() {
        if now.duration_since(*last) < RESPAWN_COOLDOWN {
            return false;
        }
    }
    s.respawn_timestamps.push(now);
    true
}

pub fn shutdown<R: Runtime>(app: &AppHandle<R>) {
    let state = app.state::<Mutex<SupervisorState>>();
    let mut s = state.lock().unwrap();
    if let Some(child) = s.child.take() {
        let pid = child.pid();
        // SIGTERM (Tauri-side: child.kill() sends SIGTERM on Unix in plugin-shell v2)
        let _ = child.kill();
        // give it 2s
        std::thread::sleep(Duration::from_secs(2));
        // hard kill via libc if still alive (rare; sidecar terminates on SIGTERM normally)
        #[cfg(unix)]
        unsafe { libc::kill(pid as i32, libc::SIGKILL); }
        tracing::info!(pid, "backend supervisor: child terminated");
    }
}
```

#### Wiring into `lib.rs`

```rust
// lib::run() setup hook — added after the existing tray::setup line
let mode = backend_supervisor::spawn_or_adopt(&app.handle());
app.manage(Mutex::new(backend_supervisor::SupervisorState {
    mode, child: None, consecutive_failures: 0, respawn_timestamps: vec![],
}));

// startup health-poll: 1s × 10 attempts before tray_alerts takes over
let handle = app.handle().clone();
tauri::async_runtime::spawn(async move {
    let client = reqwest::Client::builder().timeout(Duration::from_secs(3)).build().unwrap();
    for _ in 0..10 {
        if client.get(HEALTH_URL).send().await.map(|r| r.status().is_success()).unwrap_or(false) {
            let _ = crate::tray::set_state(&handle, crate::tray::IconState::Normal);
            return;
        }
        tokio::time::sleep(Duration::from_secs(1)).await;
    }
    let _ = crate::tray::set_state(&handle, crate::tray::IconState::Error);
});
```

#### Shutdown hook

Tauri v2 fires `RunEvent::ExitRequested`. In `lib::run()`:

```rust
.run(tauri::generate_context!())
.run(|app, event| {
    if let tauri::RunEvent::ExitRequested { .. } = event {
        backend_supervisor::shutdown(app);
    }
});
```

#### Error UI

When the supervisor fails (`SupervisionMode::Failed` or post-startup 3-strikes), `tray::set_state(app, IconState::Error)` is called (existing infrastructure at `tray.rs:55-58`). Additionally, `tray::update_alerts` should be taught to swap the "No pressing items" string for "Backend unavailable — see ~/.squirrel/squirrel.log" when supervision is in `Failed` mode. This adds one new conditional to `tray::build_menu` and one new `ids::BACKEND_ERROR` constant.

### 5.2 Vault scan cache

#### Where it lives

A new module `apps/backend/cache.py` (stdlib only — `time`, `threading.RLock`). The cache is a process-local dict keyed by `(vault_path: str, scan_kind: str)` → `CacheEntry`. It is wired into `api_home` at `server.py:476-549`.

#### TTL — opinion: 25 seconds

The tray poller runs every 30 seconds (`POLL_INTERVAL = Duration::from_secs(30)`, `tray_alerts.rs:24`). A 25 s TTL gives a near-100% hit rate for the poller while keeping the cache fresh enough that a human user who manually opens the popup right after editing a file will, in the worst case, see one stale second — and any actual write goes through the invalidation path in R-9.9 so they don't see stale data after their own writes at all.

For a 300-file vault on an M-class Mac, the prior estimate of ~900 file reads / 30 s drops to ~30 reads / 30 s (one full scan per TTL boundary) — a ~30× reduction. For a 10 MB vault that's the difference between 50–100 ms of disk-blocking on the HTTP thread per request and an O(1) dict lookup.

I considered 60 s (matches the human eye blink for "did anything change"); rejected because manual `/api/home` calls from a freshly-opened browser tab would feel laggy when reflecting writes that happened between Tauri polls.

I considered an mtime-based invalidation (rescan only when the vault root mtime is newer than the cache); rejected for v1 because mtime on the root directory doesn't propagate from nested edits on all filesystems (notably APFS clones), and the bookkeeping is complex. TTL + write-path invalidation is simpler and the staleness window is bounded.

#### Code shape

```python
# apps/backend/cache.py
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class CacheEntry:
    value: Any
    expires_at: float
    inserted_at: float


@dataclass
class _Stats:
    hits: int = 0
    misses: int = 0
    last_evicted_at: Optional[float] = None


_LOCK = threading.RLock()
_STORE: dict[tuple[str, str], CacheEntry] = {}
_STATS = _Stats()

DEFAULT_TTL_SECONDS = 25.0


def get_or_compute(
    vault_path: str,
    scan_kind: str,
    compute: Callable[[], Any],
    ttl: float = DEFAULT_TTL_SECONDS,
) -> Any:
    """Return cached value if fresh, else compute, store, and return."""
    key = (vault_path, scan_kind)
    now = time.monotonic()
    with _LOCK:
        entry = _STORE.get(key)
        if entry is not None and entry.expires_at > now:
            _STATS.hits += 1
            return entry.value
        _STATS.misses += 1
    # compute outside the lock — the scan is the slow part
    value = compute()
    with _LOCK:
        _STORE[key] = CacheEntry(value=value, expires_at=now + ttl, inserted_at=now)
    return value


def invalidate(vault_path: str, scan_kind: Optional[str] = None) -> int:
    """Drop entries for vault_path; if scan_kind is None, drop all kinds.
    Returns the number of entries evicted."""
    with _LOCK:
        if scan_kind is None:
            keys = [k for k in _STORE if k[0] == vault_path]
        else:
            keys = [k for k in _STORE if k == (vault_path, scan_kind)]
        for k in keys:
            del _STORE[k]
        if keys:
            _STATS.last_evicted_at = time.time()
        return len(keys)


def stats_snapshot() -> dict:
    with _LOCK:
        total = _STATS.hits + _STATS.misses
        return {
            "entries": len(_STORE),
            "hit_rate": (_STATS.hits / total) if total else 0.0,
            "last_evicted_at": _STATS.last_evicted_at,
        }
```

#### Wiring into `server.py`

```python
# server.py — inside api_home
from cache import get_or_compute

vault = str(ctx.active.path)
try:
    status = get_or_compute(vault, "status",
                            lambda: aggregate_status(ctx.active.path))
except Exception:
    status = {"wip": {"projects": []}, "recommended_focus": None}
try:
    deadlines = get_or_compute(vault, "deadlines",
                               lambda: scan_vault_deadlines(ctx.active.path))
except Exception:
    deadlines = {"by_urgency": {}}
# scan_vault_reminders identical pattern
```

#### Write-path invalidation (R-9.9)

`server.py` has these write paths:
- `POST /api/notes` → invalidate `(vault, "status")` and `(vault, "deadlines")` (notes can carry deadline frontmatter)
- `POST /api/focus` → invalidate `(vault, "status")` only
- `POST /api/vault` (vault switch) → no invalidation needed; the new vault has its own cache key

Add a one-line `cache.invalidate(str(ctx.active.path))` at the end of each write handler, before returning the JSON response. This is safe because invalidation is just a dict delete — cost is negligible.

#### What happens if cache is stale during a write

Sequence: Tauri poll T (cache miss → scan → cache populated, expires at T+25), user writes a note at T+10, write handler invalidates, Tauri poll T+30 (cache miss again → fresh scan). The user-visible behavior is: their own write is reflected immediately on the next poll; a stale entry can only persist for ≤25 s, and only for writes that come from outside the backend (e.g. user edits an .md file in Obsidian). For the Obsidian case, 25 s of staleness is well within the human "did my edit take" tolerance and matches the existing 30 s poll cadence.

#### New endpoint (R-9.10)

```python
# server.py — register alongside other GET routes
def api_cache_stats(self) -> None:
    from cache import stats_snapshot
    self._send_json(stats_snapshot())
```

### 5.3 SQLite connection caching in Rust

#### Where the cached connection lives

Add a field to `TauriNotificationState`:

```rust
// tray_alerts.rs
pub(crate) struct TauriNotificationState {
    // existing fields preserved unchanged
    last_notified: HashMap<String, Instant>,
    dialogs_today: u32,
    dialogs_date: String,
    last_check_at: Instant,
    last_poll_at: Instant,
    pending_clicks: HashMap<i32, String>,
    next_id: i32,
    pub(crate) notif_db_path: PathBuf,
    pub(crate) focus_prompted_date: Option<String>,
    pub(crate) last_break_notified: Option<Instant>,
    // NEW: cached connection (None until init_notif_db succeeds)
    pub(crate) notif_db: Option<Mutex<rusqlite::Connection>>,
}
```

I'm wrapping the `Connection` in its own inner `Mutex` (not relying on the outer `Mutex<TauriNotificationState>`) so callers can hold the DB lock briefly without blocking other state mutations. `rusqlite::Connection` is `Send + !Sync`, so the inner mutex is required for shared access.

#### Initialization

`init_notif_db` becomes a one-time-at-startup operation. Rewrite as:

```rust
pub(crate) fn init_notif_db(db_path: &Path) -> rusqlite::Result<rusqlite::Connection> {
    if let Some(parent) = db_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let conn = rusqlite::Connection::open(db_path)?;
    conn.execute_batch(
        "PRAGMA journal_mode=WAL;
         PRAGMA busy_timeout=5000;
         PRAGMA synchronous=NORMAL;",
    )?;
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS notifications (
           id           INTEGER PRIMARY KEY AUTOINCREMENT,
           type         TEXT NOT NULL,
           item_id      TEXT NOT NULL,
           title        TEXT NOT NULL,
           body         TEXT NOT NULL,
           item_url     TEXT,
           fired_at     TEXT NOT NULL,
           read_at      TEXT,
           dismissed_at TEXT
         );
         CREATE INDEX IF NOT EXISTS idx_notifications_item_day
           ON notifications(item_id, date(fired_at));",
    )?;
    Ok(conn)
}
```

Call site in `start_polling` (currently at `tray_alerts.rs:563-574`) changes from "call init_notif_db then drop the connection" to "call init_notif_db and store the connection in state":

```rust
// start_polling, replacing the existing init block
{
    let state = app.state::<Mutex<TauriNotificationState>>();
    let mut s = state.lock().unwrap();
    if s.notif_db.is_none() {
        match init_notif_db(&s.notif_db_path) {
            Ok(conn) => s.notif_db = Some(Mutex::new(conn)),
            Err(e) => tracing::warn!(error = %e, "tray-alerts: failed to init notifications DB"),
        }
    }
}
```

#### Migration of the four touchpoints

The cached connection is accessed through a small helper that returns a `MutexGuard`:

```rust
fn with_conn<F, T>(app: &AppHandle<impl Runtime>, f: F) -> rusqlite::Result<T>
where F: FnOnce(&rusqlite::Connection) -> rusqlite::Result<T>
{
    let state = app.state::<Mutex<TauriNotificationState>>();
    let outer = state.lock().unwrap();
    let conn_mutex = outer.notif_db.as_ref()
        .ok_or_else(|| rusqlite::Error::InvalidQuery)?;  // sentinel for "DB not init'd"
    let conn = conn_mutex.lock().unwrap();
    f(&conn)
}
```

**Touchpoint 1 — `insert_notification_if_new` (tray_alerts.rs:159).** Change signature from `(db_path, ...) -> rusqlite::Result<bool>` to `(app, ...) -> rusqlite::Result<bool>`; replace the body's `Connection::open` with `with_conn(app, |conn| { ... })`.

**Touchpoint 2 — `unread_count` (tray_alerts.rs:179).** Same shape: `(app) -> rusqlite::Result<u32>` using `with_conn`.

**Touchpoint 3 — `init_notif_db` call site (tray_alerts.rs:559-565).** Already covered above; the helper returns the `Connection` to be stored, not just `Ok(())`.

**Touchpoint 4 — the focus-prompt notification block (tray_alerts.rs:595).** That code path doesn't actually touch SQLite directly (it sends a Tauri notification); it just sits next to DB code. No migration needed there — but the next DB call in the polling loop body should also be audited and converted.

#### Handling `SQLITE_BUSY` (R-9.13)

With `busy_timeout=5000` set on the connection, `rusqlite` will internally retry for up to 5 seconds before returning `SQLITE_BUSY`. If we still get the error (very unlikely in practice since we only have one writer — the tray poller — and the macOS reminder daemon is read-mostly), we log at WARN and skip the INSERT. The next 30 s poll will retry the dedup-and-INSERT for the same item, so no data is permanently lost; we just delay one notification by 30 s.

## 6. Migration / rollout order

**Order: cache first, sidecar second, SQLite-conn cache third.**

Rationale: the cache and the SQLite-conn cache are pure-internal optimizations — they ship behind no flag, can be reverted by removing a few imports, and don't change the external contract. They reduce load on a system that is currently surviving, so they're low-risk wins to bank first. The sidecar is the higher-risk change because it inverts the lifecycle contract that R-1.7 codified, requires PyInstaller-into-Tauri build wiring, and risks shipping a `.app` that hangs at startup if a child fails to spawn. Doing it last means we can validate the cache improvements on the current architecture before stacking the lifecycle change on top.

**Step 1 — Vault scan cache (R-9.8–R-9.10).** New `cache.py`, wiring in `api_home`, write-path invalidation in 3 handlers, new `/api/cache/stats` endpoint. ~150 LOC. Unit tests in `apps/backend/tests/test_cache.py`. Ship immediately.

**Step 2 — SQLite connection cache (R-9.11–R-9.13).** Modify `TauriNotificationState`, rewrite `init_notif_db`, add `with_conn` helper, migrate the two `Connection::open` call sites. ~80 LOC. New tests in `apps/desktop/src-tauri/tests/` that exercise `with_conn` against a temp DB. Ship.

**Step 3 — Backend supervisor (R-9.1–R-9.7).** New `backend_supervisor.rs`, `tauri.conf.json` change, capabilities change, PyInstaller hook in the Tauri build, error-state UI in `tray.rs`. ~300 LOC of Rust + 30 LOC of JSON + build-pipeline wiring. Most testing is manual smoke. Ship.

Each step is its own commit (and ideally its own PR) so the rollback unit is small. If Step 3 ships and breaks something, Steps 1 and 2 keep their value independently.

## 7. Test plan

**Unit tests**

- `apps/backend/tests/test_cache.py`:
  - hit path: two `get_or_compute` calls with same key inside TTL return the same object reference, `compute` called once
  - expiry path: after `time.monotonic` advances past TTL (monkeypatched), `compute` is called again
  - invalidate: after `invalidate(vault)`, next call recomputes
  - stats: hit_rate reflects observed ratio; `last_evicted_at` populated on invalidate
- `apps/desktop/src-tauri/tests/notif_db_cached.rs`:
  - new test that opens a temp DB through `init_notif_db`, inserts via the cached `with_conn`, and reads the row back — verifies the connection-cache path
  - busy-timeout test (best-effort): open a second connection holding a write txn, prove the first call waits-then-succeeds rather than instantly erroring

**Integration tests**

- `apps/backend/tests/test_home_invalidation.py`: POST a note via the test HTTP harness, then GET `/api/home`, assert that the new note's deadline shows up in `pressing[]` even though we're inside the TTL window — proves write-invalidation works end-to-end.
- `apps/desktop/src-tauri/tests/supervisor_adoption.rs`: bind 127.0.0.1:3939 in the test thread, call `spawn_or_adopt`, assert mode is `Adopted` and `child` is None.

**Manual smoke test the user can run**

1. Fresh Mac, no launchd plist installed. Install the new DMG. Launch Squirrel.
   - Expect: tray icon goes to Normal within 10 s, "PRESSING NOW" populates within 30 s.
   - Verify: `ps aux | grep squirrel-backend` shows one child process owned by the Squirrel app.
2. Quit Squirrel via tray → "Quit Squirrel".
   - Expect: `squirrel-backend` PID is gone within 3 s.
3. Install the launchd plist (`bash apps/backend/launchd/install.sh`), then launch Squirrel.
   - Expect: tray works normally; `pgrep -f squirrel-backend` returns the launchd-spawned PID, not a Squirrel-spawned one. Quitting Squirrel does NOT kill the launchd-managed backend.
4. With Squirrel running, `kill -9` the backend child.
   - Expect: within ~90 s (3 × 30 s health checks) the tray icon flips to Error and within another 60 s a respawn happens.
5. `curl http://127.0.0.1:3939/api/cache/stats` repeatedly while the tray polls; `hit_rate` should climb toward 1.0.

## 8. Risks & open questions

- **Build pipeline:** wiring PyInstaller into `pnpm tauri build` is the messiest piece. PyInstaller is slow (~30 s+ per backend build) and produces an 8.6 MB binary; running it on every `cargo build` during Rust development would be punishing. Mitigation: only run PyInstaller for `tauri build` (release), not `tauri dev` — in dev, the supervisor finds the dev backend (`make backend-start`) via `port_in_use` and goes into `Adopted` mode. This means dev workflow is unchanged.
- **Code signing & notarization:** the bundled `squirrel-backend` is a separate Mach-O binary inside the `.app` and must be signed under the same identity as the parent. Tauri's bundler can be configured to do this, but it adds notarization-related complexity. Open question: who owns the signing identity for distribution? If the answer is "no one yet, the DMG ships unsigned," the supervisor change is still safe but Gatekeeper will whinge. Not blocking for v1.
- **Two distribution paths still exist** (`scripts/build-dmg.sh` and `pnpm tauri build`). After this change the Tauri `.app` is self-sufficient; the standalone DMG installer becomes legacy. Recommend deprecating it in a follow-up.
- **`install.sh` template mismatch:** `apps/backend/launchd/install.sh:64-68` substitutes `__PYTHON__`/`__SERVER_PY__`, but the current `plist.template` only has `__BINARY__`/`__PORT__`/`__HOME__`. This is an existing bug — the installer would produce a plist with the placeholders un-substituted. Out of scope for this LLD (the user who runs `install.sh` is going around the Tauri lifecycle anyway), but worth filing.
- **Reminder daemon overlap:** `agent-pack/companions/macos-reminders/reminder-daemon.sh` shells out to `lib/deadline_scanner.py` directly, bypassing the backend cache. That's fine — it has its own process and the cache is intentionally process-local. But if the daemon is killed and re-spawned often, it can't benefit from the cache. Not in scope here.
- **Vault size assumption:** the 25 s TTL is justified for vaults up to ~300 files. If a user grows a vault to ~3000 files, the scan cost per cache miss climbs from ~30–100 ms to ~300 ms–1 s. At that point the right move is incremental indexing (per-file mtime tracking), not TTL extension. Tracked as a future LLD.

## 9. Decisions

| Decision | Rationale | Alternatives considered |
|----------|-----------|--------------------------|
| Use `tauri-plugin-shell` `sidecar()` for spawn | Bundles binary into `.app/Contents/Resources/`, handles per-target naming, types `CommandChild` for shutdown | `std::process::Command` (rejected: hand-roll resource paths); `launchd`-only (rejected: that's the bug we're fixing) |
| Adopt-if-running policy (don't double-spawn) | Lets power users with launchd setups coexist with the Tauri lifecycle | Hard kill any existing backend (rejected: hostile to launchd users) |
| 25 s TTL on vault scan cache | Just under the 30 s poll period; near-100% hit rate for the tray; bounded staleness for human writes | 5 s (too low — every poll misses); 60 s (UI lag for manual `/api/home`); mtime-based (filesystem caveats on APFS) |
| Cache lives in-process in Python, no Redis/SQLite | We're optimizing one server process; out-of-process cache adds operational surface for zero gain | shared-memory cache (overkill); SQLite-backed (extra IO) |
| Inner `Mutex<Connection>` separate from `Mutex<TauriNotificationState>` | Lets the DB lock be held briefly without blocking state mutations | Single outer mutex (rejected: serialization of unrelated work); `r2d2` pool (rejected: only one writer, pool is overkill) |
| Cache first, sidecar last | Cache is pure-internal, low-risk, immediately valuable; sidecar inverts lifecycle and needs build-pipeline work | Sidecar first (rejected: stacks risk on risk) |
| Max 5 respawns/hour, 60 s cooldown | Prevents respawn storms when the backend is genuinely broken; still lets transient failures self-heal | Unlimited respawn (rejected: log spam, CPU); single try (rejected: too brittle) |

---

## Appendix: How to capture an Activity Monitor / `top` measurement

To validate the impact of these changes empirically on your own machine, before and after:

**Before applying the change** (control run, ~10 minutes):

```bash
# Find the backend PID
BACKEND_PID=$(pgrep -f "apps/backend/server.py" | head -1)
echo "backend pid: $BACKEND_PID"

# Sample CPU + RSS once every 5 seconds for 10 minutes (120 samples)
top -pid "$BACKEND_PID" -l 120 -s 5 -stats pid,cpu,mem,time \
  > ~/squirrel-baseline.log 2>&1 &

# In another shell, also capture macOS-level Disk I/O for the same PID
sudo fs_usage -w -f filesys "$BACKEND_PID" > ~/squirrel-baseline-fs.log 2>&1 &
```

Let it run for 10 minutes — that's 20 poll cycles. Then `kill %1 %2`.

**Activity Monitor GUI alternative:**
1. Open Activity Monitor → View → All Processes
2. Search for `squirrel-backend` (or `Python` if you haven't switched to the bundled binary yet)
3. Double-click the row → "Sample" tab → "Sample" button (captures a 3-second CPU trace)
4. Repeat after 5 minutes; compare "CPU Usage" and "Mach Messages" between samples

**After applying the change**, repeat the same procedure with the same vault and the same idle desktop. Compare:

- **Mean CPU%** across the 10-minute window. Expect 30 s "spike-and-idle" sawtooth before the change; after the change, expect roughly the same peak height but only one peak per ~25 s instead of three.
- **RSS (resident memory)** should be flat both before and after; if it climbs after the change, the cache eviction is broken.
- **Disk reads** (`fs_usage` output, grep for `.md`): expect a roughly 3× reduction on poll cycles where the cache hits.

If you also want to check the Tauri side:

```bash
TAURI_PID=$(pgrep -i squirrel | head -1)
top -pid "$TAURI_PID" -l 60 -s 10 > ~/squirrel-tauri.log 2>&1
```

Look at the user/sys CPU split — the SQLite connection-cache change should reduce sys-time (file opens), not user-time.

For a cache-stats spot check at any moment:

```bash
curl -s http://127.0.0.1:3939/api/cache/stats | python3 -m json.tool
```

Expect `hit_rate` to climb toward 1.0 within ~2 minutes of starting the app and stay there.
