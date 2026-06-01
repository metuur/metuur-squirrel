//! Backend lifecycle supervisor — Step 3 of the harden-backend-lifecycle LLD.
//!
//! Owns whether the Python `/api/*` backend at `127.0.0.1:3939` exists and
//! is reachable for as long as the Tauri app is running. Two modes:
//!
//! - **Adopted**: someone else (launchd, `make backend-start`, an IDE) is
//!   running the backend. We just monitor it. Quitting Squirrel does NOT
//!   kill it.
//! - **Managed**: we spawned the bundled `squirrel-backend` sidecar via
//!   `tauri-plugin-shell`. We own its lifecycle: kill on app exit, respawn
//!   on repeated health-check failures (bounded).
//! - **Failed**: spawn failed (binary not bundled or shell permission
//!   missing) AND nothing is listening on 3939. The tray icon goes to
//!   `IconState::Error` so the user sees the failure instead of staring at
//!   a permanently empty tray menu.
//!
//! Choice of mode happens once at startup via `spawn_or_adopt`. The health
//! loop in `health_check_tick` calls `spawn_or_adopt` again only to recover
//! from a backend that died mid-session (and only in Managed mode — we
//! never forcibly restart an Adopted backend).
//!
//! Implements R-9.1–R-9.7 from `docs/ears/phase-2-data-plane-and-desktop-popup.md`.

use std::net::{SocketAddr, TcpStream};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

pub(crate) const BACKEND_PORT: u16 = 3939;
const HEALTH_URL: &str = "http://127.0.0.1:3939/api/me";
const PORT_PROBE_TIMEOUT: Duration = Duration::from_millis(200);
const HEALTH_REQ_TIMEOUT: Duration = Duration::from_secs(3);
const STARTUP_BUDGET_ATTEMPTS: u32 = 10;
const STARTUP_ATTEMPT_GAP: Duration = Duration::from_secs(1);
const HEALTH_INTERVAL: Duration = Duration::from_secs(30);
const RESPAWN_COOLDOWN: Duration = Duration::from_secs(60);
const MAX_RESPAWNS_PER_HOUR: u32 = 5;
const STRIKES_BEFORE_ERROR: u32 = 3;
const SIDECAR_NAME: &str = "squirrel-backend";

/// Mint a per-launch shared-secret token used to authenticate the Tauri shell
/// to the backend it spawns or adopts (Runtime Trust Handshake, R-1.1, R-1.2,
/// R-1.5). Returns 64 lowercase ASCII hex characters drawn from 32 bytes of
/// OS-provided entropy. Caller is expected to store the value in `RuntimeToken`
/// process state; this function does not persist it.
pub(crate) fn mint_runtime_token() -> String {
    use rand::RngCore;
    use std::fmt::Write;
    let mut bytes = [0u8; 32];
    rand::rngs::OsRng.fill_bytes(&mut bytes);
    let mut s = String::with_capacity(64);
    for b in bytes {
        write!(s, "{:02x}", b).expect("writing to a String never fails");
    }
    s
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum SupervisionMode {
    Adopted,
    Managed,
    Failed,
}

pub(crate) struct SupervisorState {
    pub mode: SupervisionMode,
    pub child: Option<CommandChild>,
    pub consecutive_failures: u32,
    pub respawn_timestamps: Vec<Instant>,
}

impl SupervisorState {
    pub(crate) fn new() -> Self {
        Self {
            mode: SupervisionMode::Failed,
            child: None,
            consecutive_failures: 0,
            respawn_timestamps: Vec::new(),
        }
    }
}

/// R-9.1: probe whether port 3939 already has a TCP listener. Used to
/// decide between Managed (spawn) and Adopted (don't spawn). 200ms budget
/// keeps the cold-launch path snappy even if the host is congested.
fn port_in_use(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect_timeout(&addr, PORT_PROBE_TIMEOUT).is_ok()
}

/// Try the sidecar spawn. On success, returns the `CommandChild` and the
/// async task draining stdout/stderr is detached. On failure (missing
/// binary, capability not granted, fork failed) returns Err with a message
/// suitable for tracing.
fn spawn_sidecar<R: Runtime>(app: &AppHandle<R>) -> Result<CommandChild, String> {
    // R-1.3: hand the per-launch token to the sidecar via argv. R-1.4: never
    // via env — env leaks through /proc and is inherited by grandchildren.
    // We pass `--token` and set NO environment variables on the command.
    let token = app.state::<crate::RuntimeToken>().0.clone();
    let cmd = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|e| format!("sidecar resolution: {e}"))?;
    let (mut rx, child) = cmd
        .args(["--port", &BACKEND_PORT.to_string(), "--token", &token])
        .spawn()
        .map_err(|e| format!("sidecar spawn: {e}"))?;

    // Drain stdout/stderr into our tracing log so backend output isn't lost.
    tauri::async_runtime::spawn(async move {
        while let Some(ev) = rx.recv().await {
            match ev {
                CommandEvent::Stdout(line) | CommandEvent::Stderr(line) => {
                    tracing::debug!(target: "backend", "{}", String::from_utf8_lossy(&line).trim_end());
                }
                CommandEvent::Terminated(payload) => {
                    tracing::warn!(?payload, "backend child terminated");
                }
                _ => {}
            }
        }
    });
    Ok(child)
}

/// R-9.1/R-9.2: pick the right lifecycle mode for the backend.
///
/// Order of preference:
///   1. Port already taken → Adopted (don't double-spawn).
///   2. Spawn succeeds → Managed.
///   3. Spawn fails → Failed (caller surfaces via tray Error icon).
///
/// Returns the new `(mode, child)`. The caller is responsible for storing
/// these in `SupervisorState`.
pub(crate) fn spawn_or_adopt<R: Runtime>(
    app: &AppHandle<R>,
) -> (SupervisionMode, Option<CommandChild>) {
    if port_in_use(BACKEND_PORT) {
        tracing::info!(port = BACKEND_PORT, "backend supervisor: port already bound, adopting");
        return (SupervisionMode::Adopted, None);
    }
    match spawn_sidecar(app) {
        Ok(child) => {
            tracing::info!(pid = child.pid(), "backend supervisor: spawned sidecar (Managed)");
            (SupervisionMode::Managed, Some(child))
        }
        Err(e) => {
            tracing::error!(error = %e, "backend supervisor: spawn failed");
            (SupervisionMode::Failed, None)
        }
    }
}

/// Wait for the backend's `/api/me` to return 2xx, up to
/// `STARTUP_BUDGET_ATTEMPTS × STARTUP_ATTEMPT_GAP` (~10s). Returns true on
/// first success, false if the budget elapses. Used right after
/// `spawn_or_adopt` so the tray icon can flip to Normal as soon as the
/// backend is ready, or Error if the budget is exceeded.
pub(crate) async fn wait_for_ready<R: Runtime>(app: &AppHandle<R>) -> bool {
    let client = match build_client() {
        Some(c) => c,
        None => return false,
    };
    for attempt in 0..STARTUP_BUDGET_ATTEMPTS {
        if probe_health(&client).await {
            tracing::info!(attempt, "backend supervisor: health-check OK at startup");
            let _ = crate::tray::set_state(app, crate::tray::IconState::Normal);
            return true;
        }
        tokio::time::sleep(STARTUP_ATTEMPT_GAP).await;
    }
    tracing::warn!(
        attempts = STARTUP_BUDGET_ATTEMPTS,
        "backend supervisor: startup health-check budget exhausted"
    );
    let _ = crate::tray::set_state(app, crate::tray::IconState::Error);
    false
}

/// Long-running health loop. Wakes every `HEALTH_INTERVAL`, probes
/// `/api/me`, and reacts:
///
/// - 2xx → reset the consecutive-failure counter, keep icon Normal.
/// - <2xx for STRIKES_BEFORE_ERROR consecutive ticks → set icon Error.
///   In Managed mode, also try to respawn (subject to rate limit).
/// - Adopted mode never respawns; the user manages launchd or `make
///   backend-start` themselves.
pub(crate) async fn run_health_loop<R: Runtime>(app: AppHandle<R>) {
    let client = match build_client() {
        Some(c) => c,
        None => {
            tracing::error!("backend supervisor: failed to build health-check client");
            return;
        }
    };
    loop {
        tokio::time::sleep(HEALTH_INTERVAL).await;
        health_check_tick(&app, &client).await;
    }
}

/// One iteration of the health loop. Public for tests.
pub(crate) async fn health_check_tick<R: Runtime>(app: &AppHandle<R>, client: &reqwest::Client) {
    let ok = probe_health(client).await;

    let (should_attempt_respawn, mode_was_failed) = {
        let state = app.state::<Mutex<SupervisorState>>();
        let mut s = state.lock().unwrap();
        if ok {
            // Recover icon if we were degraded.
            if s.consecutive_failures >= STRIKES_BEFORE_ERROR
                || s.mode == SupervisionMode::Failed
            {
                let _ = crate::tray::set_state(app, crate::tray::IconState::Normal);
            }
            s.consecutive_failures = 0;
            return;
        }
        s.consecutive_failures += 1;
        if s.consecutive_failures < STRIKES_BEFORE_ERROR {
            return;
        }
        let _ = crate::tray::set_state(app, crate::tray::IconState::Error);
        let attempt = s.mode == SupervisionMode::Managed && should_respawn(&mut s);
        let was_failed = s.mode == SupervisionMode::Failed;
        (attempt, was_failed)
    };

    if should_attempt_respawn {
        tracing::warn!("backend supervisor: 3 strikes — attempting respawn");
        let (mode, child) = spawn_or_adopt(app);
        let state = app.state::<Mutex<SupervisorState>>();
        let mut s = state.lock().unwrap();
        s.mode = mode;
        s.child = child;
        s.consecutive_failures = 0;
    } else if mode_was_failed {
        // Failed-mode recovery: someone may have started the backend by
        // hand in the meantime; if a probe will pass on the next tick, the
        // ok-branch will recover the icon. Nothing to do here besides the
        // Error icon we already set.
    }
}

/// Returns true and records the timestamp if a respawn is allowed by the
/// rate limit (max `MAX_RESPAWNS_PER_HOUR`, at least `RESPAWN_COOLDOWN`
/// between attempts).
fn should_respawn(s: &mut SupervisorState) -> bool {
    let now = Instant::now();
    s.respawn_timestamps
        .retain(|t| now.duration_since(*t) < Duration::from_secs(3600));
    if s.respawn_timestamps.len() as u32 >= MAX_RESPAWNS_PER_HOUR {
        tracing::warn!(
            limit = MAX_RESPAWNS_PER_HOUR,
            "backend supervisor: respawn rate-limit reached, giving up for this hour"
        );
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

/// R-9.3: shutdown hook called from the Tauri `RunEvent::ExitRequested`.
/// In Adopted mode this is a no-op — the user owns the backend's lifecycle.
/// In Managed mode we attempt a graceful shutdown:
///
///   1. Send SIGTERM (Unix) — gives the backend a chance to close logs,
///      flush the journal-mode WAL, and exit on its own terms.
///   2. Sleep for GRACEFUL_SHUTDOWN_TIMEOUT to give the backend room
///      to actually exit.
///   3. Call `CommandChild::kill()` — a no-op if the child already exited,
///      and a SIGKILL escalation if it didn't. This call also performs
///      the cleanup that Tokio expects (zombie reaping).
///
/// Why a fixed sleep instead of polling for exit: `kill(pid, 0)` returns
/// "alive" for zombie children (post-exit, pre-reap) and racing with
/// Tokio's SIGCHLD reaper via `waitpid(pid, WNOHANG)` adds complexity
/// for a 2-second wait that the user tolerates anyway. Trade-off
/// accepted: shutdown always takes ~2s, but is always correct.
///
/// Windows has no SIGTERM analogue, so step 1+2 are skipped and we go
/// straight to the platform-native hard kill. The backend has atomic
/// writes and no half-committed-transaction class of bugs, so even a
/// hard kill is safe.
pub(crate) fn shutdown<R: Runtime>(app: &AppHandle<R>) {
    let state = app.state::<Mutex<SupervisorState>>();
    let mut s = state.lock().unwrap_or_else(|p| p.into_inner());
    if s.mode != SupervisionMode::Managed {
        return;
    }
    let Some(child) = s.child.take() else {
        return;
    };
    let pid = child.pid();

    #[cfg(unix)]
    {
        if send_term(pid) {
            tracing::info!(
                pid,
                timeout_secs = GRACEFUL_SHUTDOWN_TIMEOUT.as_secs(),
                "backend supervisor: SIGTERM sent; waiting for graceful exit",
            );
            std::thread::sleep(GRACEFUL_SHUTDOWN_TIMEOUT);
        } else {
            tracing::warn!(pid, "backend supervisor: SIGTERM failed; escalating to SIGKILL");
        }
    }

    // child.kill() is a no-op if the process already exited from SIGTERM;
    // otherwise it sends SIGKILL on Unix / TerminateProcess on Windows.
    // Either way the Tokio Child handle gets properly cleaned up.
    match child.kill() {
        Ok(()) => tracing::info!(pid, "backend supervisor: shutdown complete"),
        Err(e) => tracing::warn!(pid, error = %e, "backend supervisor: kill failed on shutdown"),
    }
}

const GRACEFUL_SHUTDOWN_TIMEOUT: Duration = Duration::from_secs(2);

#[cfg(unix)]
fn send_term(pid: u32) -> bool {
    // SAFETY: libc::kill takes a pid_t + signal. Passing SIGTERM and a
    // valid (non-zero) pid is well-defined. Returns 0 on success or -1
    // with errno set on failure.
    let rc = unsafe { libc::kill(pid as libc::pid_t, libc::SIGTERM) };
    rc == 0
}

/// Pure state-inspection helper — true when the backend is either in
/// permanent Failed mode or has accumulated enough consecutive health-check
/// failures that the user should see an error UI. Split out so tests can
/// exercise the logic without an AppHandle.
fn is_degraded_state(s: &SupervisorState) -> bool {
    matches!(s.mode, SupervisionMode::Failed)
        || s.consecutive_failures >= STRIKES_BEFORE_ERROR
}

/// True when the tray UI should show a backend-error message instead of
/// the normal "No pressing items" empty state. Used by `tray::build_menu`.
/// Returns false if the supervisor state hasn't been registered yet
/// (early startup, or test runs that don't init the supervisor).
pub(crate) fn is_degraded<R: Runtime>(app: &AppHandle<R>) -> bool {
    let Some(state) = app.try_state::<Mutex<SupervisorState>>() else {
        return false;
    };
    let s = state.lock().unwrap_or_else(|p| p.into_inner());
    is_degraded_state(&s)
}

fn build_client() -> Option<reqwest::Client> {
    reqwest::Client::builder()
        .timeout(HEALTH_REQ_TIMEOUT)
        .build()
        .ok()
}

async fn probe_health(client: &reqwest::Client) -> bool {
    match client.get(HEALTH_URL).send().await {
        Ok(r) => r.status().is_success(),
        Err(_) => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── Runtime Trust Handshake token minting (R-1.1, R-1.5) ────────────────

    #[test]
    fn mint_runtime_token_is_64_lowercase_hex_chars() {
        let t = mint_runtime_token();
        assert_eq!(t.len(), 64, "token must be 64 hex chars (32 bytes)");
        assert!(
            t.chars().all(|c| c.is_ascii_hexdigit() && !c.is_ascii_uppercase()),
            "token must be lowercase ASCII hex only, got {t:?}"
        );
    }

    #[test]
    fn mint_runtime_token_two_calls_differ() {
        // CSPRNG draw — collision probability is 2^-256, effectively never.
        assert_ne!(mint_runtime_token(), mint_runtime_token());
    }

    #[test]
    fn supervisor_state_starts_in_failed_mode_with_no_child() {
        let s = SupervisorState::new();
        assert_eq!(s.mode, SupervisionMode::Failed);
        assert!(s.child.is_none());
        assert_eq!(s.consecutive_failures, 0);
        assert!(s.respawn_timestamps.is_empty());
    }

    #[test]
    fn should_respawn_first_call_succeeds_and_records_timestamp() {
        let mut s = SupervisorState::new();
        assert!(should_respawn(&mut s));
        assert_eq!(s.respawn_timestamps.len(), 1);
    }

    #[test]
    fn should_respawn_cooldown_blocks_immediate_second_attempt() {
        let mut s = SupervisorState::new();
        assert!(should_respawn(&mut s));
        // Immediately ask again — cooldown is 60s so we expect a block.
        assert!(!should_respawn(&mut s));
        // The blocked attempt must not record a timestamp.
        assert_eq!(s.respawn_timestamps.len(), 1);
    }

    #[test]
    fn should_respawn_rate_limit_blocks_after_max_per_hour() {
        let mut s = SupervisorState::new();
        // Pretend MAX_RESPAWNS_PER_HOUR distinct attempts already happened
        // recently — synthesize their timestamps so we don't actually wait.
        let synthetic = Instant::now() - Duration::from_secs(120);
        for _ in 0..MAX_RESPAWNS_PER_HOUR {
            s.respawn_timestamps.push(synthetic);
        }
        assert!(!should_respawn(&mut s), "rate limit should block");
        assert_eq!(
            s.respawn_timestamps.len(),
            MAX_RESPAWNS_PER_HOUR as usize,
            "blocked attempt should not be recorded"
        );
    }

    #[test]
    fn should_respawn_old_timestamps_are_garbage_collected() {
        let mut s = SupervisorState::new();
        // Hour-old timestamps must not count against the limit. We rely on
        // the `retain(... < 3600s)` line — push timestamps that are
        // *exactly* outside the window.
        let stale = Instant::now() - Duration::from_secs(3700);
        for _ in 0..MAX_RESPAWNS_PER_HOUR {
            s.respawn_timestamps.push(stale);
        }
        // Should succeed because all the old timestamps get pruned first.
        assert!(should_respawn(&mut s));
        assert_eq!(s.respawn_timestamps.len(), 1, "stale entries pruned, one new added");
    }

    #[test]
    fn port_in_use_returns_false_for_unbound_port() {
        // Pick a high port unlikely to be in use. There is a small chance
        // of a false positive on a busy machine; if this test ever flakes,
        // bind a TcpListener first and then probe a separate ephemeral.
        let unlikely = 59231;
        assert!(!port_in_use(unlikely));
    }

    #[test]
    fn port_in_use_returns_true_for_bound_port() {
        use std::net::TcpListener;
        let listener = TcpListener::bind(SocketAddr::from(([127, 0, 0, 1], 0))).unwrap();
        let port = listener.local_addr().unwrap().port();
        assert!(port_in_use(port));
        drop(listener);
    }

    #[test]
    fn is_degraded_state_returns_true_for_failed_mode_regardless_of_strikes() {
        let mut s = SupervisorState::new();
        s.mode = SupervisionMode::Failed;
        s.consecutive_failures = 0;
        assert!(is_degraded_state(&s));
    }

    #[test]
    fn is_degraded_state_returns_true_for_managed_mode_at_or_above_strike_limit() {
        let mut s = SupervisorState::new();
        s.mode = SupervisionMode::Managed;
        s.consecutive_failures = STRIKES_BEFORE_ERROR;
        assert!(is_degraded_state(&s));
    }

    #[test]
    fn is_degraded_state_returns_false_for_managed_mode_below_strike_limit() {
        let mut s = SupervisorState::new();
        s.mode = SupervisionMode::Managed;
        s.consecutive_failures = STRIKES_BEFORE_ERROR - 1;
        assert!(!is_degraded_state(&s));
    }

    #[test]
    fn is_degraded_state_returns_false_for_adopted_with_zero_strikes() {
        let mut s = SupervisorState::new();
        s.mode = SupervisionMode::Adopted;
        s.consecutive_failures = 0;
        assert!(!is_degraded_state(&s));
    }

    #[test]
    fn is_degraded_state_returns_true_for_adopted_after_three_strikes() {
        let mut s = SupervisorState::new();
        s.mode = SupervisionMode::Adopted;
        s.consecutive_failures = STRIKES_BEFORE_ERROR;
        assert!(is_degraded_state(&s));
    }

    // ── Graceful-shutdown helpers (Unix only) ──────────────────────────────

    #[cfg(unix)]
    #[test]
    fn send_term_delivers_sigterm_to_a_running_child() {
        use std::process::Command;
        // Spawn `sleep` directly (no shell wrapper) so SIGTERM hits the
        // actual sleep process. We don't assert on exit timing — proving
        // a child has exited from a separate thread races with the
        // kernel's reaper. We assert two narrower properties:
        //   - send_term returns true when the pid exists
        //   - the kernel does NOT return -1/ESRCH from kill(pid, 0) before
        //     we send SIGTERM (i.e. the child was actually alive)
        // Anything stronger (e.g. "child exited within 1s") needs
        // waitpid + reaper coordination that we intentionally don't do
        // in the production shutdown path.
        let mut child = Command::new("sleep")
            .arg("30")
            .spawn()
            .expect("spawn sleep");
        let pid = child.id();

        let alive_before = unsafe { libc::kill(pid as libc::pid_t, 0) } == 0;
        assert!(alive_before, "child should be alive before SIGTERM");

        assert!(send_term(pid), "send_term should succeed for a live child");

        // Cleanup — wait so we don't leave a zombie.
        let _ = child.wait();
    }

    #[cfg(unix)]
    #[test]
    fn send_term_returns_false_for_nonexistent_pid() {
        // A high but plausibly-unused pid. Skip the assertion if it
        // happens to be in use right now (extremely unlikely).
        let phantom = 999_999;
        let exists = unsafe { libc::kill(phantom as libc::pid_t, 0) } == 0;
        if exists {
            return;
        }
        assert!(!send_term(phantom), "SIGTERM to nonexistent pid should fail");
    }
}
