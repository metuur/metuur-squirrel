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
    let cmd = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|e| format!("sidecar resolution: {e}"))?;
    let (mut rx, child) = cmd
        .args(["--port", &BACKEND_PORT.to_string()])
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
/// In Managed mode the cached `CommandChild` is killed. Plugin's `.kill()`
/// sends SIGKILL on Unix; the backend is a stateless HTTP server with
/// atomic writes so this is safe (no half-finished commits to recover).
pub(crate) fn shutdown<R: Runtime>(app: &AppHandle<R>) {
    let state = app.state::<Mutex<SupervisorState>>();
    let mut s = state.lock().unwrap_or_else(|p| p.into_inner());
    if s.mode != SupervisionMode::Managed {
        return;
    }
    if let Some(child) = s.child.take() {
        let pid = child.pid();
        match child.kill() {
            Ok(()) => tracing::info!(pid, "backend supervisor: child killed on shutdown"),
            Err(e) => tracing::warn!(pid, error = %e, "backend supervisor: kill failed on shutdown"),
        }
    }
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
}
