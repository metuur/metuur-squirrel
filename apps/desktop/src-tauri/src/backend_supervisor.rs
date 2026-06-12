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

use serde::Serialize;
use tauri::{AppHandle, Emitter, Manager, Runtime};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

/// Parse a decimal `u16` at compile time (no std const str→int). Used only on
/// the `SQUIRREL_BACKEND_PORT` build-time override below.
const fn parse_port(s: &str) -> u16 {
    let bytes = s.as_bytes();
    let mut n: u16 = 0;
    let mut i = 0;
    while i < bytes.len() {
        n = n * 10 + (bytes[i] - b'0') as u16;
        i += 1;
    }
    n
}

/// Backend port. Defaults to 3939; the dev build overrides it to 3940 by setting
/// `SQUIRREL_BACKEND_PORT=3940` at compile time (see package.json dev scripts) so
/// `tauri dev` / "Squirrel Dev.app" never collides with an installed prod app on
/// the same port. `option_env!` bakes the value in; build.rs reruns on change.
pub(crate) const BACKEND_PORT: u16 = match option_env!("SQUIRREL_BACKEND_PORT") {
    Some(s) => parse_port(s),
    None => 3939,
};

/// Dev builds set `SQUIRREL_ALLOW_DEV_BACKEND=1` at compile time (package.json
/// tauri:dev / tauri:build:dev) so the handshake ADOPTS an unauthenticated
/// dev-mode backend (`make dev-local`'s live server.py on :3940) instead of
/// refusing it. Never set for production builds — there `mode: dev` keeps the
/// R-4.3 refusal.
const ALLOW_DEV_BACKEND: bool = option_env!("SQUIRREL_ALLOW_DEV_BACKEND").is_some();
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

/// Outcome of the adoption handshake probe against a backend already bound to
/// port 3939 (Runtime Trust Handshake, R-4.2..R-4.6). Only `Adopted` proceeds;
/// every other variant is a terminal refusal.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum HandshakeOutcome {
    /// 200 with a constant-time-equal `token_echo` → the backend is ours.
    Adopted,
    /// 200 `{"mode": "dev"}` → an unauthenticated dev backend (R-4.3).
    RefusedDev,
    /// 401 → a process that does not know our token (R-4.4).
    Refused401,
    /// 200 with a body matching neither shape, or any other status (R-4.5).
    RefusedUnknown,
    /// connect/send/read exceeded the 3s budget (R-4.6).
    RefusedTimeout,
    /// `~/.squirrel/launchd-token` exists but failed the R-2.3 file checks, so
    /// it could not be used for the probe (R-5.5). Set before any probe runs.
    RefusedLaunchdToken,
}

/// Why a present `~/.squirrel/launchd-token` could not be trusted (R-5.5).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum LaunchdTokenError {
    BadMode,
    BadOwner,
    Malformed,
    Unreadable,
}

/// Map a refusal outcome to the typed banner cause emitted to the React shell
/// (R-4.3..R-4.6). `Adopted` is not a refusal, so it maps to `None`.
fn handshake_refusal_cause(o: HandshakeOutcome) -> Option<&'static str> {
    match o {
        HandshakeOutcome::Adopted => None,
        HandshakeOutcome::RefusedDev => Some("DevModeDetected"),
        HandshakeOutcome::Refused401 | HandshakeOutcome::RefusedUnknown => Some("UnknownProcess"),
        HandshakeOutcome::RefusedTimeout => Some("NotResponding"),
        HandshakeOutcome::RefusedLaunchdToken => Some("LaunchdTokenInvalid"),
    }
}

/// Payload for the `handshake-refused` event consumed by the React banner
/// (Unit 6). `cause` is one of the typed strings from `handshake_refusal_cause`.
#[derive(Serialize, Clone)]
pub(crate) struct HandshakeRefusalPayload {
    pub cause: &'static str,
}

/// Current handshake-refusal cause, or `None` when adoption was not refused.
///
/// The `handshake-refused` event is a one-shot emitted during early startup,
/// before the webview registers its listener — and Tauri does not replay events,
/// so a banner mounting late would miss it and the user falls through to a
/// confusing "Load failed" during onboarding instead of the recovery banner.
/// Exposing the state as a queryable command lets the frontend recover the
/// banner on mount regardless of emit timing.
pub(crate) fn current_refusal_cause<R: Runtime>(app: &AppHandle<R>) -> Option<&'static str> {
    let state = app.try_state::<Mutex<SupervisorState>>()?;
    let mode = {
        let s = state.lock().unwrap_or_else(|p| p.into_inner());
        s.mode
    };
    match mode {
        SupervisionMode::RefusedAdoption(o) => handshake_refusal_cause(o),
        _ => None,
    }
}

/// R-4.3..R-4.6: when the supervisor refused adoption, set the tray to Error
/// and emit a typed `handshake-refused` event carrying the cause so the React
/// shell can render the recovery banner. No-op in any non-refusal mode.
pub(crate) fn notify_refusal<R: Runtime>(app: &AppHandle<R>) {
    let outcome = {
        let Some(state) = app.try_state::<Mutex<SupervisorState>>() else {
            return;
        };
        let s = state.lock().unwrap_or_else(|p| p.into_inner());
        match s.mode {
            SupervisionMode::RefusedAdoption(o) => o,
            _ => return,
        }
    };
    if let Some(cause) = handshake_refusal_cause(outcome) {
        let _ = crate::tray::set_state(app, crate::tray::IconState::Error);
        if let Err(e) = app.emit("handshake-refused", HandshakeRefusalPayload { cause }) {
            tracing::warn!(error = %e, "failed to emit handshake-refused event");
        } else {
            tracing::info!(cause, "handshake refused; banner event emitted");
        }
    }
}

/// Stable `tracing` label for a handshake outcome (R-4.10).
fn handshake_outcome_label(o: HandshakeOutcome) -> &'static str {
    match o {
        HandshakeOutcome::Adopted => "adopted",
        HandshakeOutcome::RefusedDev => "refused_dev",
        HandshakeOutcome::Refused401 => "refused_401",
        HandshakeOutcome::RefusedUnknown => "refused_unknown",
        HandshakeOutcome::RefusedTimeout => "refused_timeout",
        HandshakeOutcome::RefusedLaunchdToken => "refused_launchd_token",
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum SupervisionMode {
    Adopted,
    Managed,
    Failed,
    /// Port 3939 was bound by a process that failed the trust handshake. The
    /// inner outcome drives the banner cause (Unit 6). Terminal: no fallback
    /// port, no sidecar spawn, and no API request is ever issued (R-4.7..R-4.9).
    RefusedAdoption(HandshakeOutcome),
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
    let token = app.state::<crate::RuntimeToken>().get();
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
/// Total budget for the adoption handshake — connect + send + read (R-4.1).
/// Matches the existing health-check timeout so a wedged backend can't stall
/// startup longer than the user already tolerates.
const HANDSHAKE_TIMEOUT: Duration = HEALTH_REQ_TIMEOUT;

/// R-4.1..R-4.6: probe a backend already bound to port 3939 and classify it.
///
/// Issues exactly one `GET /api/_handshake` with `X-Squirrel-Token: <token>`
/// over a raw TCP connection (no async runtime, no extra deps) so it is safe
/// to call from both the sync setup hook and the async health loop. One
/// attempt, 3s total, no retry (LLD timing constraint). Any timeout maps to
/// `RefusedTimeout`; any other transport/parse failure maps to `RefusedUnknown`.
fn probe_handshake(token: &str) -> HandshakeOutcome {
    match probe_handshake_inner(token) {
        Ok(outcome) => outcome,
        Err(e) if e.kind() == std::io::ErrorKind::TimedOut
            || e.kind() == std::io::ErrorKind::WouldBlock => HandshakeOutcome::RefusedTimeout,
        Err(_) => HandshakeOutcome::RefusedUnknown,
    }
}

fn probe_handshake_inner(token: &str) -> std::io::Result<HandshakeOutcome> {
    use std::io::{Read, Write};
    let addr = SocketAddr::from(([127, 0, 0, 1], BACKEND_PORT));
    let mut stream = TcpStream::connect_timeout(&addr, HANDSHAKE_TIMEOUT)?;
    stream.set_read_timeout(Some(HANDSHAKE_TIMEOUT))?;
    stream.set_write_timeout(Some(HANDSHAKE_TIMEOUT))?;
    let req = format!(
        "GET /api/_handshake HTTP/1.0\r\nHost: 127.0.0.1:{port}\r\n\
         X-Squirrel-Token: {token}\r\nAccept: application/json\r\nConnection: close\r\n\r\n",
        port = BACKEND_PORT,
    );
    stream.write_all(req.as_bytes())?;
    stream.flush()?;
    let mut raw = Vec::new();
    stream.read_to_end(&mut raw)?;
    Ok(classify_handshake_response(&raw, token, ALLOW_DEV_BACKEND))
}

/// Map a raw HTTP/1.x response to a `HandshakeOutcome`. Split out as a pure
/// function so every branch (R-4.2..R-4.5) is unit-testable without a socket.
/// `allow_dev` is `ALLOW_DEV_BACKEND` in production code; tests pass both.
fn classify_handshake_response(raw: &[u8], token: &str, allow_dev: bool) -> HandshakeOutcome {
    let text = String::from_utf8_lossy(raw);
    let Some((head, body)) = text.split_once("\r\n\r\n") else {
        return HandshakeOutcome::RefusedUnknown;
    };
    let status = head
        .lines()
        .next()
        .and_then(|line| line.split_whitespace().nth(1))
        .and_then(|code| code.parse::<u16>().ok());
    match status {
        Some(401) => HandshakeOutcome::Refused401,
        Some(200) => {
            if body.contains("\"mode\"") && body.contains("\"dev\"") {
                if allow_dev {
                    HandshakeOutcome::Adopted
                } else {
                    HandshakeOutcome::RefusedDev
                }
            } else if let Some(echo) = extract_token_echo(body) {
                if ct_eq(echo.as_bytes(), token.as_bytes()) {
                    HandshakeOutcome::Adopted
                } else {
                    HandshakeOutcome::RefusedUnknown
                }
            } else {
                HandshakeOutcome::RefusedUnknown
            }
        }
        _ => HandshakeOutcome::RefusedUnknown,
    }
}

/// Pull the string value of `"token_echo"` out of a JSON body without a JSON
/// dependency. Returns None if the field is absent or unterminated.
fn extract_token_echo(body: &str) -> Option<String> {
    let key = "\"token_echo\"";
    let after = &body[body.find(key)? + key.len()..];
    let rest = &after[after.find(':')? + 1..];
    let start = rest.find('"')? + 1;
    let end = start + rest[start..].find('"')?;
    Some(rest[start..end].to_string())
}

/// Constant-time byte comparison (R-4.2 / LLD D4). The length check leaks only
/// the length, which is not secret (both sides are 64-char hex tokens).
fn ct_eq(a: &[u8], b: &[u8]) -> bool {
    use subtle::ConstantTimeEq;
    if a.len() != b.len() {
        return false;
    }
    a.ct_eq(b).into()
}

/// Path to the launchd-provisioned token (`~/.squirrel/launchd-token`).
fn launchd_token_path() -> std::path::PathBuf {
    crate::logging::squirrel_dir().join("launchd-token")
}

/// R-5.4/R-5.5: read the launchd token if present. `Ok(None)` means the file is
/// absent — a legitimate signal to fall back to the in-memory runtime token.
/// `Err` means the file is present but failed the R-2.3 checks (mode 0600,
/// owner == euid, 64 hex chars), which must refuse adoption rather than probe.
fn read_launchd_token() -> Result<Option<String>, LaunchdTokenError> {
    read_launchd_token_at(&launchd_token_path())
}

fn read_launchd_token_at(path: &std::path::Path) -> Result<Option<String>, LaunchdTokenError> {
    use std::os::unix::fs::MetadataExt;
    let meta = match std::fs::metadata(path) {
        Ok(m) => m,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(LaunchdTokenError::Unreadable),
    };
    if meta.mode() & 0o777 != 0o600 {
        return Err(LaunchdTokenError::BadMode);
    }
    // SAFETY: geteuid() is always-safe and never fails.
    let euid = unsafe { libc::geteuid() };
    if meta.uid() != euid {
        return Err(LaunchdTokenError::BadOwner);
    }
    let raw = std::fs::read_to_string(path).map_err(|_| LaunchdTokenError::Unreadable)?;
    let token = raw.trim_end_matches('\n');
    if token.len() != 64 || !token.bytes().all(|b| b.is_ascii_hexdigit()) {
        return Err(LaunchdTokenError::Malformed);
    }
    Ok(Some(token.to_string()))
}

/// R-4.11: which refusal outcomes are eligible for self-reclaim. A token
/// mismatch (`Refused401` / `RefusedUnknown`) or a wedged listener
/// (`RefusedTimeout`) can be our own orphaned sidecar from a prior launch.
/// `RefusedDev` (a deliberate `make backend-start`) and `RefusedLaunchdToken`
/// are excluded — those keep their refusal banners.
fn refusal_is_self_reclaimable(outcome: HandshakeOutcome) -> bool {
    matches!(
        outcome,
        HandshakeOutcome::Refused401
            | HandshakeOutcome::RefusedUnknown
            | HandshakeOutcome::RefusedTimeout
    )
}

/// macOS: PIDs listening on `port` (loopback) via `lsof`. Empty on any error.
#[cfg(target_os = "macos")]
fn listener_pids(port: u16) -> Vec<u32> {
    let Ok(out) = std::process::Command::new("/usr/sbin/lsof")
        .args(["-nP", &format!("-iTCP:{port}"), "-sTCP:LISTEN", "-t"])
        .output()
    else {
        return Vec::new();
    };
    String::from_utf8_lossy(&out.stdout)
        .lines()
        .filter_map(|l| l.trim().parse::<u32>().ok())
        .collect()
}

/// macOS: absolute executable path of `pid` via `ps -o comm=` (prints the path
/// of the running binary). None if the process is gone or unreadable.
#[cfg(target_os = "macos")]
fn pid_exe_path(pid: u32) -> Option<String> {
    let out = std::process::Command::new("/bin/ps")
        .args(["-o", "comm=", "-p", &pid.to_string()])
        .output()
        .ok()?;
    if !out.status.success() {
        return None;
    }
    let path = String::from_utf8_lossy(&out.stdout).trim().to_string();
    if path.is_empty() {
        None
    } else {
        Some(path)
    }
}

/// R-4.11/R-4.12: reclaim port 3939 iff it is held by our own orphaned
/// `squirrel-backend` (a stale sidecar from a previous launch). Returns true
/// only when a self-owned sidecar was killed AND the port actually freed.
///
/// Safety boundary (R-4.12): only a process whose executable basename is
/// `squirrel-backend` is targeted, and `SIGKILL` only succeeds against
/// processes the Tauri user owns. A foreign listener is therefore never
/// displaced — a non-matching exe is skipped, and an unkillable process leaves
/// the refusal intact.
#[cfg(target_os = "macos")]
fn reclaim_own_stale_sidecar() -> bool {
    let mut killed_any = false;
    for pid in listener_pids(BACKEND_PORT) {
        let is_ours = pid_exe_path(pid)
            .as_deref()
            .and_then(|p| std::path::Path::new(p).file_name())
            .map(|name| name == "squirrel-backend")
            .unwrap_or(false);
        if !is_ours {
            tracing::info!(pid, ":3939 held by a non-Squirrel process — not reclaiming (R-4.12)");
            continue;
        }
        // SAFETY: libc::kill with a valid pid + SIGKILL is well-defined. It
        // fails with EPERM for processes we do not own, which we treat as
        // "not reclaimable" and leave the refusal intact.
        let rc = unsafe { libc::kill(pid as libc::pid_t, libc::SIGKILL) };
        if rc == 0 {
            tracing::warn!(pid, "backend supervisor: killed orphaned own sidecar to reclaim :3939 (R-4.11)");
            killed_any = true;
        } else {
            tracing::warn!(pid, "backend supervisor: listener on :3939 not killable — preserving refusal (R-4.12)");
        }
    }
    if !killed_any {
        return false;
    }
    // Wait for the kernel to release the port before we attempt to bind.
    for _ in 0..20 {
        if !port_in_use(BACKEND_PORT) {
            return true;
        }
        std::thread::sleep(Duration::from_millis(100));
    }
    !port_in_use(BACKEND_PORT)
}

/// Non-macOS: the supervisor's process-reclaim is macOS-specific (lsof/ps/kill).
#[cfg(not(target_os = "macos"))]
fn reclaim_own_stale_sidecar() -> bool {
    false
}

pub(crate) fn spawn_or_adopt<R: Runtime>(
    app: &AppHandle<R>,
) -> (SupervisionMode, Option<CommandChild>) {
    if port_in_use(BACKEND_PORT) {
        // R-4.1: something is on 3939. Don't blindly adopt — prove it's ours.
        // R-5.4/R-5.5: prefer the launchd-provisioned token when the file is
        // present and valid; a present-but-invalid file refuses immediately.
        let token = match read_launchd_token() {
            Ok(Some(launchd)) => launchd,
            Ok(None) => app.state::<crate::RuntimeToken>().get(),
            Err(e) => {
                tracing::warn!(error = ?e, "launchd-token present but invalid; refusing adoption");
                tracing::info!(
                    target: "handshake",
                    outcome = handshake_outcome_label(HandshakeOutcome::RefusedLaunchdToken),
                    elapsed_ms = 0u64,
                    "handshake_attempt"
                );
                return (
                    SupervisionMode::RefusedAdoption(HandshakeOutcome::RefusedLaunchdToken),
                    None,
                );
            }
        };
        let started = Instant::now();
        let outcome = probe_handshake(&token);
        tracing::info!(
            target: "handshake",
            outcome = handshake_outcome_label(outcome),
            elapsed_ms = started.elapsed().as_millis() as u64,
            "handshake_attempt"
        );
        return match outcome {
            HandshakeOutcome::Adopted => {
                // R-5.7: the adopted backend authenticates with `token` (the
                // launchd token when `~/.squirrel/launchd-token` is present),
                // which can differ from this launch's minted runtime token.
                // Promote it to the effective token so every client — the
                // webview (`runtime_token`), `open_web_url`, and the health /
                // alert pollers — authenticates against the backend we adopted.
                // Without this, /api/* returns 401 and pages render empty.
                app.state::<crate::RuntimeToken>().set(token.clone());
                (SupervisionMode::Adopted, None)
            }
            // R-4.11: a token-mismatch / wedged listener that is verifiably our
            // OWN orphaned sidecar (prior launch) is reclaimed — kill it and
            // spawn fresh. Self-ownership is enforced inside
            // reclaim_own_stale_sidecar(); a foreign listener is never displaced.
            o if refusal_is_self_reclaimable(o) && reclaim_own_stale_sidecar() => {
                match spawn_sidecar(app) {
                    Ok(child) => {
                        tracing::info!(
                            pid = child.pid(),
                            "backend supervisor: reclaimed :3939 from own stale sidecar; spawned fresh (Managed)"
                        );
                        (SupervisionMode::Managed, Some(child))
                    }
                    Err(e) => {
                        tracing::error!(error = %e, "backend supervisor: spawn after reclaim failed");
                        (SupervisionMode::Failed, None)
                    }
                }
            }
            // R-4.7/4.8/4.9/4.12: refusal is terminal for foreign listeners — no
            // fallback port, no displacing spawn, no further requests.
            refused => (SupervisionMode::RefusedAdoption(refused), None),
        };
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
    // R-4.7: a refused adoption is terminal. Never issue /api/me (or any other
    // request) to the squatter. Surface the error state + banner cause and bail.
    if is_refused_adoption(app) {
        notify_refusal(app);
        return false;
    }
    let client = match build_client(&app.state::<crate::RuntimeToken>().get()) {
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
    // R-4.7: never poll a backend whose adoption we refused.
    if is_refused_adoption(&app) {
        tracing::info!("backend supervisor: adoption refused — health loop disabled (R-4.7)");
        return;
    }
    let client = match build_client(&app.state::<crate::RuntimeToken>().get()) {
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

/// Kill the current backend (if Managed) and respawn it. Used by the
/// "Restart Service" tray menu item. In Adopted mode the external process is
/// not touched; we simply re-probe and re-adopt when it comes back.
pub(crate) async fn restart<R: Runtime>(app: &AppHandle<R>) {
    tracing::info!("backend supervisor: restart requested");
    let _ = crate::tray::set_state(app, crate::tray::IconState::Processing);

    // Kill the Managed child (if any) while holding the lock, then drop it.
    {
        let state = app.state::<Mutex<SupervisorState>>();
        let mut s = state.lock().unwrap_or_else(|p| p.into_inner());
        if s.mode == SupervisionMode::Managed {
            if let Some(child) = s.child.take() {
                let pid = child.pid();
                #[cfg(unix)]
                send_term(pid);
                let _ = child.kill();
                tracing::info!(pid, "backend supervisor: sidecar killed for restart");
            }
        }
        s.mode = SupervisionMode::Failed;
        s.consecutive_failures = 0;
        s.respawn_timestamps.clear();
    }

    // Give the OS a moment to free the port before we try to bind again.
    tokio::time::sleep(Duration::from_millis(800)).await;

    let (mode, child) = spawn_or_adopt(app);
    {
        let state = app.state::<Mutex<SupervisorState>>();
        let mut s = state.lock().unwrap_or_else(|p| p.into_inner());
        s.mode = mode;
        s.child = child;
        s.consecutive_failures = 0;
    }

    wait_for_ready(app).await;
    tracing::info!("backend supervisor: restart complete");
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
    matches!(s.mode, SupervisionMode::Failed | SupervisionMode::RefusedAdoption(_))
        || s.consecutive_failures >= STRIKES_BEFORE_ERROR
}

/// True when the supervisor refused to adopt the process on port 3939. Used to
/// suppress all health probing (R-4.7) and to drive the refusal banner.
fn is_refused_adoption<R: Runtime>(app: &AppHandle<R>) -> bool {
    let Some(state) = app.try_state::<Mutex<SupervisorState>>() else {
        return false;
    };
    let s = state.lock().unwrap_or_else(|p| p.into_inner());
    matches!(s.mode, SupervisionMode::RefusedAdoption(_))
}

/// The banner cause string when adoption was refused, else `None`. Drives the
/// tray "Why?" item and the re-emit on click (R-6.1).
pub(crate) fn refused_adoption_cause<R: Runtime>(app: &AppHandle<R>) -> Option<&'static str> {
    let state = app.try_state::<Mutex<SupervisorState>>()?;
    let s = state.lock().unwrap_or_else(|p| p.into_inner());
    match s.mode {
        SupervisionMode::RefusedAdoption(o) => handshake_refusal_cause(o),
        _ => None,
    }
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

/// Build the health-check client with the per-launch runtime token as a default
/// header. The health endpoint (`/api/me`) is auth-gated (Runtime Trust
/// Handshake): without `X-Squirrel-Token` the backend returns 401, which the
/// loop reads as "unhealthy" — pinning the tray icon to Error and eventually
/// the "Backend unavailable" degraded state even when the backend is fine.
fn build_client(token: &str) -> Option<reqwest::Client> {
    let mut headers = reqwest::header::HeaderMap::new();
    match reqwest::header::HeaderValue::from_str(token) {
        Ok(val) => {
            headers.insert("X-Squirrel-Token", val);
        }
        Err(e) => tracing::warn!(error = %e, "health client: runtime token not a valid header value"),
    }
    reqwest::Client::builder()
        .timeout(HEALTH_REQ_TIMEOUT)
        .default_headers(headers)
        .build()
        .ok()
}

async fn probe_health(client: &reqwest::Client) -> bool {
    let health_url = format!("http://127.0.0.1:{BACKEND_PORT}/api/me");
    match client.get(&health_url).send().await {
        Ok(r) => r.status().is_success(),
        Err(_) => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── Self-reclaim eligibility (R-4.11/R-4.12) ────────────────────────────

    #[test]
    fn self_reclaim_eligibility_only_token_mismatch_and_timeout() {
        // Token mismatch / wedged → our own orphan may hold the port → reclaim.
        assert!(refusal_is_self_reclaimable(HandshakeOutcome::Refused401));
        assert!(refusal_is_self_reclaimable(HandshakeOutcome::RefusedUnknown));
        assert!(refusal_is_self_reclaimable(HandshakeOutcome::RefusedTimeout));
        // Deliberate dev backend and a bad launchd-token file keep their banners.
        assert!(!refusal_is_self_reclaimable(HandshakeOutcome::RefusedDev));
        assert!(!refusal_is_self_reclaimable(HandshakeOutcome::RefusedLaunchdToken));
        // Adopted is not a refusal at all.
        assert!(!refusal_is_self_reclaimable(HandshakeOutcome::Adopted));
    }

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

    // ── Adoption handshake classification (R-4.2..R-4.6) ─────────────────────

    const TKN: &str = "abc123";

    fn resp(status_line: &str, body: &str) -> Vec<u8> {
        format!("{status_line}\r\nContent-Type: application/json\r\n\r\n{body}").into_bytes()
    }

    #[test]
    fn classify_200_matching_echo_is_adopted() {
        let raw = resp("HTTP/1.0 200 OK", &format!("{{\"token_echo\": \"{TKN}\"}}"));
        assert_eq!(classify_handshake_response(&raw, TKN, false), HandshakeOutcome::Adopted);
    }

    #[test]
    fn classify_200_mismatched_echo_is_refused_unknown() {
        let raw = resp("HTTP/1.0 200 OK", "{\"token_echo\": \"deadbeef\"}");
        assert_eq!(classify_handshake_response(&raw, TKN, false), HandshakeOutcome::RefusedUnknown);
    }

    #[test]
    fn classify_200_dev_mode_is_refused_dev() {
        let raw = resp("HTTP/1.0 200 OK", "{\"mode\": \"dev\"}");
        assert_eq!(classify_handshake_response(&raw, TKN, false), HandshakeOutcome::RefusedDev);
    }

    #[test]
    fn classify_200_dev_mode_is_adopted_when_dev_backend_allowed() {
        // Dev builds (SQUIRREL_ALLOW_DEV_BACKEND) adopt make dev-local's
        // unauthenticated live backend instead of refusing it.
        let raw = resp("HTTP/1.0 200 OK", "{\"mode\": \"dev\"}");
        assert_eq!(classify_handshake_response(&raw, TKN, true), HandshakeOutcome::Adopted);
    }

    #[test]
    fn classify_401_is_refused_401() {
        let raw = resp("HTTP/1.0 401 Unauthorized", "");
        assert_eq!(classify_handshake_response(&raw, TKN, false), HandshakeOutcome::Refused401);
    }

    #[test]
    fn classify_200_unrecognized_body_is_refused_unknown() {
        let raw = resp("HTTP/1.0 200 OK", "{\"hello\": \"world\"}");
        assert_eq!(classify_handshake_response(&raw, TKN, false), HandshakeOutcome::RefusedUnknown);
    }

    #[test]
    fn classify_garbage_without_header_split_is_refused_unknown() {
        let raw = b"not even http".to_vec();
        assert_eq!(classify_handshake_response(&raw, TKN, false), HandshakeOutcome::RefusedUnknown);
    }

    #[test]
    fn ct_eq_matches_only_identical_bytes() {
        assert!(ct_eq(b"deadbeef", b"deadbeef"));
        assert!(!ct_eq(b"deadbeef", b"deadbeee"));
        assert!(!ct_eq(b"short", b"longer"));
    }

    #[test]
    fn extract_token_echo_pulls_the_value() {
        assert_eq!(
            extract_token_echo("{\"token_echo\": \"cafe\"}").as_deref(),
            Some("cafe")
        );
        assert_eq!(extract_token_echo("{\"mode\": \"dev\"}"), None);
    }

    #[test]
    fn refused_adoption_mode_is_degraded() {
        let mut s = SupervisorState::new();
        s.mode = SupervisionMode::RefusedAdoption(HandshakeOutcome::Refused401);
        assert!(is_degraded_state(&s));
    }

    // ── Refusal-cause mapping (R-4.3..R-4.6) ─────────────────────────────────

    #[test]
    fn refusal_cause_maps_each_outcome() {
        assert_eq!(handshake_refusal_cause(HandshakeOutcome::RefusedDev), Some("DevModeDetected"));
        assert_eq!(handshake_refusal_cause(HandshakeOutcome::Refused401), Some("UnknownProcess"));
        assert_eq!(
            handshake_refusal_cause(HandshakeOutcome::RefusedUnknown),
            Some("UnknownProcess")
        );
        assert_eq!(handshake_refusal_cause(HandshakeOutcome::RefusedTimeout), Some("NotResponding"));
        assert_eq!(
            handshake_refusal_cause(HandshakeOutcome::RefusedLaunchdToken),
            Some("LaunchdTokenInvalid")
        );
        assert_eq!(handshake_refusal_cause(HandshakeOutcome::Adopted), None);
    }

    // ── launchd-token reading (R-5.4, R-5.5) ─────────────────────────────────

    #[cfg(unix)]
    fn write_mode(path: &std::path::Path, content: &str, mode: u32) {
        use std::os::unix::fs::PermissionsExt;
        std::fs::write(path, content).unwrap();
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(mode)).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn launchd_token_absent_is_ok_none() {
        let dir = std::env::temp_dir().join(format!("sq-lt-absent-{}", std::process::id()));
        let path = dir.join("launchd-token");
        let _ = std::fs::remove_dir_all(&dir);
        assert_eq!(read_launchd_token_at(&path), Ok(None));
    }

    #[cfg(unix)]
    #[test]
    fn launchd_token_valid_is_ok_some() {
        let dir = std::env::temp_dir().join(format!("sq-lt-valid-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("launchd-token");
        let tok = "a".repeat(64);
        write_mode(&path, &format!("{tok}\n"), 0o600); // trailing newline tolerated
        assert_eq!(read_launchd_token_at(&path), Ok(Some(tok)));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[cfg(unix)]
    #[test]
    fn launchd_token_bad_mode_is_err() {
        let dir = std::env::temp_dir().join(format!("sq-lt-mode-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("launchd-token");
        write_mode(&path, &"a".repeat(64), 0o644);
        assert_eq!(read_launchd_token_at(&path), Err(LaunchdTokenError::BadMode));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[cfg(unix)]
    #[test]
    fn launchd_token_malformed_is_err() {
        let dir = std::env::temp_dir().join(format!("sq-lt-bad-{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        let path = dir.join("launchd-token");
        write_mode(&path, "not-hex-and-too-short", 0o600);
        assert_eq!(read_launchd_token_at(&path), Err(LaunchdTokenError::Malformed));
        let _ = std::fs::remove_dir_all(&dir);
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
