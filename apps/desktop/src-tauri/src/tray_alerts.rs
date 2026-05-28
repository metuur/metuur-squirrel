//! Phase 2 (post-Phase-1 supersede): background poller that keeps the tray
//! menu's "PRESSING NOW" section fresh.
//!
//! Polls `http://127.0.0.1:3939/api/home` every 30 seconds, takes the first
//! three entries from `pressing[]`, and asks `tray::update_alerts(...)` to
//! rebuild the menu. The user can click any of the three to open the v0.5
//! browser SPA at `/notes/<id>` (existing route, no popup detail view yet).
//!
//! Failure modes:
//! - Backend unreachable (Connection refused / DNS / timeout): clear alerts
//!   so the menu doesn't show stale data; log at debug; keep polling.
//! - Non-2xx HTTP: same.
//! - Slow response: 3s timeout per request, then treated as offline.

use serde::Deserialize;
use std::time::Duration;
use tauri::{AppHandle, Runtime};

const BACKEND_HOME: &str = "http://127.0.0.1:3939/api/home";
const POLL_INTERVAL: Duration = Duration::from_secs(30);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(3);
const MAX_ALERTS: usize = 3;

/// Mirror of /api/home.pressing[] — only the fields the tray label needs.
#[derive(Debug, Clone, Deserialize)]
pub struct Alert {
    pub id: String,
    #[allow(dead_code)] // kept for future label variants; not in current format
    pub title: String,
    pub is_overdue: bool,
    pub hours_left: Option<f64>,
    pub days_overdue: Option<i64>,
    pub urgency_label: Option<String>,
}

impl Alert {
    /// Short, single-line menu label. Example:
    ///   "43d overdue · CASA-CONTABILIDAD-TAXES-2025"
    ///   "3h left · SIDEPROJECT-FOO-001"
    pub fn menu_label(&self) -> String {
        let tail = if self.is_overdue {
            format!("{}d overdue", self.days_overdue.unwrap_or(0))
        } else if let Some(h) = self.hours_left {
            format!("{}h left", h.round() as i64)
        } else if let Some(lbl) = &self.urgency_label {
            lbl.clone()
        } else {
            "due".to_string()
        };
        format!("{} · {}", tail, self.id)
    }
}

#[derive(Debug, Deserialize)]
struct HomeResponse {
    pressing: Vec<Alert>,
}

async fn fetch_pressing(client: &reqwest::Client) -> Result<Vec<Alert>, reqwest::Error> {
    let resp = client
        .get(BACKEND_HOME)
        .timeout(REQUEST_TIMEOUT)
        .send()
        .await?
        .error_for_status()?
        .json::<HomeResponse>()
        .await?;
    Ok(resp.pressing.into_iter().take(MAX_ALERTS).collect())
}

/// Spawn the polling loop. Idempotent across module's lifecycle in the sense
/// that callers should only invoke this once (from `lib::run`'s setup).
pub fn start_polling<R: Runtime>(app: AppHandle<R>) {
    tauri::async_runtime::spawn(async move {
        let client = match reqwest::Client::builder()
            .timeout(REQUEST_TIMEOUT)
            .build()
        {
            Ok(c) => c,
            Err(e) => {
                tracing::error!(error = %e, "tray-alerts: failed to build HTTP client");
                return;
            }
        };

        loop {
            match fetch_pressing(&client).await {
                Ok(alerts) => {
                    if let Err(e) = crate::tray::update_alerts(&app, &alerts) {
                        tracing::warn!(error = %e, "tray-alerts: menu rebuild failed");
                    } else {
                        tracing::debug!(count = alerts.len(), "tray-alerts: refreshed");
                    }
                }
                Err(e) => {
                    tracing::debug!(error = %e, "tray-alerts: backend unreachable, clearing");
                    let _ = crate::tray::update_alerts(&app, &[]);
                }
            }
            tokio::time::sleep(POLL_INTERVAL).await;
        }
    });
}
