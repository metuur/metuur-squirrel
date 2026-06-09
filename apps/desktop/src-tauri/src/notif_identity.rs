//! First-launch notification-identity bootstrap (notification-icon-branding
//! R-1.1–R-1.5).
//!
//! macOS only honors `terminal-notifier -sender com.metuur.squirrel` after the
//! bundle has emitted ≥1 notification through `UNUserNotificationCenter` with
//! permission granted. This one-shot, run from the `lib::run()` setup hook,
//! warms that identity exactly once and records completion with the
//! `~/.squirrel/.notif_identity` sentinel.

use tauri::plugin::PermissionState;
use tauri::{AppHandle, Runtime};
use tauri_plugin_notification::NotificationExt;

/// Absolute path of the bootstrap sentinel. Presence ⇒ bootstrap completed.
fn sentinel_path() -> std::path::PathBuf {
    crate::logging::squirrel_dir().join(".notif_identity")
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

    // R-1.3: sentinel present ⇒ no permission query, no emit, no recreate.
    if sentinel.exists() {
        return;
    }

    // R-1.1: query permission; request it only when the OS hasn't decided yet.
    let state = match app.notification().permission_state() {
        Ok(s) => s,
        Err(e) => {
            tracing::warn!(error = %e, "notif-identity: permission_state query failed; retry next launch");
            return;
        }
    };
    let state = match state {
        PermissionState::Prompt | PermissionState::PromptWithRationale => {
            match app.notification().request_permission() {
                Ok(s) => s,
                Err(e) => {
                    tracing::warn!(error = %e, "notif-identity: request_permission failed; retry next launch");
                    return;
                }
            }
        }
        other => other,
    };

    // R-1.4: denied/not granted ⇒ WARN, no emit, no sentinel, retry next launch.
    if state != PermissionState::Granted {
        tracing::warn!(?state, "notif-identity: permission not granted; bootstrap deferred to next launch");
        return;
    }

    // R-1.2: emit exactly one banner to register the source with
    // UNUserNotificationCenter; create the sentinel only after a clean dispatch.
    match app
        .notification()
        .builder()
        .title("Squirrel")
        .body("Notifications are on 🐿️")
        .show()
    {
        Ok(_) => match std::fs::File::create(&sentinel) {
            Ok(_) => tracing::info!(
                sentinel = %sentinel.display(),
                "notif-identity: bootstrap emit sent; sentinel created"
            ),
            Err(e) => tracing::warn!(
                error = %e,
                "notif-identity: emit sent but sentinel write failed; re-emit next launch"
            ),
        },
        Err(e) => {
            tracing::warn!(error = %e, "notif-identity: bootstrap emit failed; no sentinel, retry next launch");
        }
    }
}
