//! First-launch notification-identity bootstrap (notification-icon-branding
//! R-1.1–R-1.5).
//!
//! macOS only honors `terminal-notifier -sender com.metuur.squirrel` after the
//! bundle has emitted ≥1 notification through `UNUserNotificationCenter` with
//! permission granted. This one-shot, run from the `lib::run()` setup hook,
//! warms that identity exactly once and records completion with the
//! `~/.squirrel/.notif_identity` sentinel.

use std::path::Path;
use tauri::plugin::PermissionState;
use tauri::{AppHandle, Runtime};
use tauri_plugin_notification::NotificationExt;

/// Absolute path of the bootstrap sentinel. Presence ⇒ bootstrap completed.
fn sentinel_path() -> std::path::PathBuf {
    crate::logging::squirrel_dir().join(".notif_identity")
}

/// What the bootstrap does, derived purely from sentinel presence + permission
/// state. Split from IO so the gating logic (R-1.2/R-1.3/R-1.4) is unit-testable
/// without a Tauri runtime or a live notification center.
#[derive(Debug, PartialEq, Eq)]
enum Action {
    /// R-1.3: sentinel present — no permission query, no emit, no recreate.
    Skip,
    /// R-1.2: authorized — emit one banner, then create the sentinel.
    EmitAndMark,
    /// R-1.4: not granted — WARN, no emit, no sentinel; retried next launch.
    Defer,
}

/// Pure policy: sentinel presence wins (R-1.3); otherwise authorization gates
/// the emit (R-1.2 vs R-1.4). No IO, no side effects.
fn decide(sentinel_exists: bool, permission: PermissionState) -> Action {
    if sentinel_exists {
        Action::Skip
    } else if permission == PermissionState::Granted {
        Action::EmitAndMark
    } else {
        Action::Defer
    }
}

/// R-1.1: resolve the effective permission — query the current state, and
/// request it only when the OS hasn't decided yet (`Prompt`). Returns `None`
/// when the plugin query/request errors (logged at WARN; retried next launch).
fn resolve_permission<R: Runtime>(app: &AppHandle<R>) -> Option<PermissionState> {
    let state = match app.notification().permission_state() {
        Ok(s) => s,
        Err(e) => {
            tracing::warn!(error = %e, "notif-identity: permission_state query failed; retry next launch");
            return None;
        }
    };
    match state {
        PermissionState::Prompt | PermissionState::PromptWithRationale => {
            match app.notification().request_permission() {
                Ok(s) => Some(s),
                Err(e) => {
                    tracing::warn!(error = %e, "notif-identity: request_permission failed; retry next launch");
                    None
                }
            }
        }
        other => Some(other),
    }
}

/// R-1.2: create the sentinel marking bootstrap complete.
fn mark_complete(sentinel: &Path) -> std::io::Result<()> {
    std::fs::File::create(sentinel).map(|_| ())
}

/// R-1.1–R-1.4: permission-gated one-shot that registers `com.metuur.squirrel`
/// as a notification source. Best-effort — every failure is logged at WARN and
/// never blocks startup; idempotent across launches via the sentinel.
///
/// The sentinel is gated on permission *authorization*, not on `.show()`
/// returning `Ok`: `tauri-plugin-notification`'s `.show()` returns `Ok` even
/// when permission is denied, so an `Ok`-gated flag would be set on a denied
/// first launch and the identity would never warm.
pub fn bootstrap_once<R: Runtime>(app: &AppHandle<R>) {
    let sentinel = sentinel_path();

    // R-1.3: present ⇒ no-op, and crucially no permission query at all.
    if sentinel.exists() {
        return;
    }

    let permission = match resolve_permission(app) {
        Some(p) => p,
        None => return,
    };

    match decide(sentinel.exists(), permission) {
        Action::Skip => {}
        Action::Defer => {
            tracing::warn!(?permission, "notif-identity: permission not granted; deferred to next launch");
        }
        Action::EmitAndMark => {
            // R-1.2: emit exactly one banner to register the source, then create
            // the sentinel only after a clean dispatch.
            match app
                .notification()
                .builder()
                .title("Squirrel")
                .body("Notifications are on 🐿️")
                .show()
            {
                Ok(_) => match mark_complete(&sentinel) {
                    Ok(_) => tracing::info!(
                        sentinel = %sentinel.display(),
                        "notif-identity: bootstrap emit sent; sentinel created"
                    ),
                    Err(e) => tracing::warn!(
                        error = %e,
                        "notif-identity: emit sent but sentinel write failed; re-emit next launch"
                    ),
                },
                Err(e) => tracing::warn!(
                    error = %e,
                    "notif-identity: bootstrap emit failed; no sentinel, retry next launch"
                ),
            }
        }
    }
}

#[cfg(test)]
mod tests {
    //! R-6.3: authorized → emit + sentinel created; denied → no sentinel,
    //! retried next start; sentinel present → no-op. The live `.show()` /
    //! permission query needs a real `UNUserNotificationCenter`, so these tests
    //! exercise the deterministic gating seam (`decide` + the sentinel file
    //! effect); the actual on-screen emit is covered by manual smoke (R-6.4).
    use super::*;

    /// A unique temp sentinel path that does not exist yet.
    fn fresh_sentinel() -> std::path::PathBuf {
        let mut p = std::env::temp_dir();
        let nanos = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        p.push(format!(".notif_identity_test_{}_{}", std::process::id(), nanos));
        p
    }

    #[test]
    fn sentinel_present_is_noop_regardless_of_permission() {
        // R-1.3: once warmed, never re-query/emit/recreate — for any permission.
        for perm in [
            PermissionState::Granted,
            PermissionState::Denied,
            PermissionState::Prompt,
            PermissionState::PromptWithRationale,
        ] {
            assert_eq!(decide(true, perm), Action::Skip, "perm = {perm:?}");
        }
    }

    #[test]
    fn authorized_first_launch_emits_and_marks() {
        // R-1.2: sentinel absent + authorized → emit then create sentinel.
        assert_eq!(decide(false, PermissionState::Granted), Action::EmitAndMark);
    }

    #[test]
    fn denied_or_undetermined_first_launch_defers() {
        // R-1.4: anything not Granted → no emit, no sentinel, retry next launch.
        assert_eq!(decide(false, PermissionState::Denied), Action::Defer);
        assert_eq!(decide(false, PermissionState::Prompt), Action::Defer);
        assert_eq!(
            decide(false, PermissionState::PromptWithRationale),
            Action::Defer
        );
    }

    #[test]
    fn mark_complete_creates_sentinel_then_decision_flips_to_skip() {
        // R-1.2 → R-1.3: a fresh path proceeds; after mark_complete the same
        // path is treated as warmed (no-op) even under Denied.
        let sentinel = fresh_sentinel();
        assert!(!sentinel.exists());
        assert_eq!(decide(sentinel.exists(), PermissionState::Granted), Action::EmitAndMark);

        mark_complete(&sentinel).expect("create sentinel");
        assert!(sentinel.exists());
        assert_eq!(decide(sentinel.exists(), PermissionState::Denied), Action::Skip);

        let _ = std::fs::remove_file(&sentinel);
    }
}
