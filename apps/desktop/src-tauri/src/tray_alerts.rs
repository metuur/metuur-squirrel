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
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{AppHandle, Manager, Runtime};

const BACKEND_ORIGIN: &str = "http://127.0.0.1:3939";
const BACKEND_HOME: &str = "http://127.0.0.1:3939/api/home";
const POLL_INTERVAL: Duration = Duration::from_secs(30);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(3);
const MAX_ALERTS: usize = 3;
const NOTIF_INTERVAL: Duration = Duration::from_secs(120);
const SLEEP_THRESHOLD: Duration = Duration::from_secs(15);
const ITEM_COOLDOWN: Duration = Duration::from_secs(3600);
const MAX_DIALOGS_PER_DAY: u32 = 8;

pub(crate) struct TauriNotificationState {
    last_notified: HashMap<String, Instant>,
    dialogs_today: u32,
    dialogs_date: String,
    last_check_at: Instant,
    last_poll_at: Instant,
    pending_clicks: HashMap<i32, String>,
    next_id: i32,
}

impl TauriNotificationState {
    pub(crate) fn new() -> Self {
        Self {
            last_notified: HashMap::new(),
            dialogs_today: 0,
            dialogs_date: String::new(),
            last_check_at: Instant::now(),
            last_poll_at: Instant::now(),
            pending_clicks: HashMap::new(),
            next_id: 0,
        }
    }
}

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

/// Mirror of /api/reminders — approaching and active reminder items.
#[derive(Debug, Clone, Deserialize)]
pub struct ReminderAlert {
    pub id: String,
    pub title: String,
    pub reminder_date: String,
    pub proyecto: Option<String>,
}

impl ReminderAlert {
    pub fn menu_label(&self) -> String {
        format!("📅 {} · {}", self.reminder_date, self.id)
    }
}

#[derive(Debug, Deserialize)]
struct RemindersResponse {
    approaching: Vec<ReminderAlert>,
    active: Vec<ReminderAlert>,
}

#[derive(Debug, Deserialize)]
struct HomeResponse {
    pressing: Vec<Alert>,
}

/// UTC date as YYYY-MM-DD without adding a dependency on chrono.
fn today_date_string() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs() as i64;
    // Gregorian calendar from Julian Day Number (Hinnant algorithm, UTC).
    let z = secs / 86400 + 719468;
    let era = (if z >= 0 { z } else { z - 146096 }) / 146097;
    let doe = (z - era * 146097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{:04}-{:02}-{:02}", y, m, d)
}

async fn fetch_reminders(client: &reqwest::Client) -> Result<RemindersResponse, reqwest::Error> {
    client
        .get("http://127.0.0.1:3939/api/reminders")
        .timeout(REQUEST_TIMEOUT)
        .send()
        .await?
        .error_for_status()?
        .json::<RemindersResponse>()
        .await
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

// R-3.1–R-3.6: Apply all guards and return at most 3 qualifying candidates.
// Mutates `state` for date rollover only; does NOT update last_check_at.
fn select_candidates<'a>(state: &mut TauriNotificationState, alerts: &'a [Alert]) -> Vec<&'a Alert> {
    // R-1.2: interval guard
    if state.last_check_at.elapsed() < NOTIF_INTERVAL {
        return vec![];
    }

    // R-3.2: date rollover
    let today = today_date_string();
    if state.dialogs_date != today {
        state.dialogs_today = 0;
        state.dialogs_date = today;
    }

    // R-3.3: daily cap
    if state.dialogs_today >= MAX_DIALOGS_PER_DAY {
        return vec![];
    }

    // R-3.5, R-3.6: per-item cooldown + cap at 3
    alerts
        .iter()
        .filter(|a| {
            state
                .last_notified
                .get(&a.id)
                .map_or(true, |t| t.elapsed() >= ITEM_COOLDOWN)
        })
        .take(3)
        .collect()
}

// Selects reminder_active candidates that pass per-item cooldown.
// Called after select_candidates (which owns the interval guard and date rollover).
fn select_reminder_candidates<'a>(
    state: &TauriNotificationState,
    reminders: &'a [ReminderAlert],
) -> Vec<&'a ReminderAlert> {
    if state.last_check_at.elapsed() < NOTIF_INTERVAL {
        return vec![];
    }
    if state.dialogs_today >= MAX_DIALOGS_PER_DAY {
        return vec![];
    }
    reminders
        .iter()
        .filter(|r| {
            state
                .last_notified
                .get(&r.id)
                .map_or(true, |t| t.elapsed() >= ITEM_COOLDOWN)
        })
        .take(3)
        .collect()
}

// R-1.1 + R-4.3: called every tick from `start_polling`. Sends at most 3 native banners
// (pressing + reminder_active combined) when guards pass, then updates `last_check_at`.
// R-4.4: reminder_approaching items are NOT passed here — tray only.
fn check_notifications<R: Runtime>(app: &AppHandle<R>, alerts: &[Alert], reminder_active: &[ReminderAlert]) {
    use tauri_plugin_notification::NotificationExt;

    let state_ref = app.state::<Mutex<TauriNotificationState>>();

    // Phase 1: pressing candidates (owns interval guard + date rollover)
    let candidates: Vec<Alert> = {
        let mut state = state_ref.lock().unwrap();
        select_candidates(&mut state, alerts)
            .into_iter()
            .cloned()
            .collect()
    };

    // Phase 1b: reminder_active candidates (same NOTIF_INTERVAL / ITEM_COOLDOWN / daily cap)
    let reminder_cands: Vec<ReminderAlert> = {
        let state = state_ref.lock().unwrap();
        select_reminder_candidates(&state, reminder_active)
            .into_iter()
            .cloned()
            .collect()
    };

    // Phase 2: send pressing notifications
    for alert in &candidates {
        let (id, task_url) = {
            let mut state = state_ref.lock().unwrap();
            let id = state.next_id;
            state.next_id += 1;
            let url = format!("{}/notes/{}", BACKEND_ORIGIN, alert.id);
            state.pending_clicks.insert(id, url.clone());
            (id, url)
        };

        let title = format!("⏰ squirrel: {}", alert.id);
        let body = alert.menu_label();

        // extra data carries taskUrl so the React onAction handler can open it.
        let mut extra = std::collections::HashMap::new();
        extra.insert("taskUrl".to_string(), serde_json::json!(task_url));

        match app
            .notification()
            .builder()
            .id(id)
            .title(&title)
            .body(&body)
            .show()
        {
            Ok(_) => {
                let mut state = state_ref.lock().unwrap();
                state.last_notified.insert(alert.id.clone(), Instant::now());
                state.dialogs_today += 1;
                tracing::info!(project_id = %alert.id, notification_id = id, "notif-sent");
            }
            Err(e) => {
                tracing::warn!(error = %e, "notif-send-failed");
            }
        }
    }

    // Phase 3: send reminder_active notifications (R-4.3)
    for reminder in &reminder_cands {
        let result = {
            let mut state = state_ref.lock().unwrap();
            if state.dialogs_today >= MAX_DIALOGS_PER_DAY {
                None
            } else {
                let id = state.next_id;
                state.next_id += 1;
                let url = format!("{}/notes/{}", BACKEND_ORIGIN, reminder.id);
                state.pending_clicks.insert(id, url.clone());
                Some((id, url))
            }
        };
        let (id, _task_url) = match result {
            Some(t) => t,
            None => continue,
        };

        let title = format!("📅 squirrel: {}", reminder.id);
        let body = reminder.menu_label();

        match app
            .notification()
            .builder()
            .id(id)
            .title(&title)
            .body(&body)
            .show()
        {
            Ok(_) => {
                let mut state = state_ref.lock().unwrap();
                state.last_notified.insert(reminder.id.clone(), Instant::now());
                state.dialogs_today += 1;
                tracing::info!(reminder_id = %reminder.id, notification_id = id, "reminder-notif-sent");
            }
            Err(e) => {
                tracing::warn!(error = %e, "reminder-notif-send-failed");
            }
        }
    }

    // Phase 4: always update last_check_at after passing all guards (even if 0 candidates)
    state_ref.lock().unwrap().last_check_at = Instant::now();
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
                    let reminders = fetch_reminders(&client).await.unwrap_or_else(|_| RemindersResponse {
                        approaching: vec![],
                        active: vec![],
                    });
                    if let Err(e) = crate::tray::update_alerts(&app, &alerts, &reminders.approaching, &reminders.active) {
                        tracing::warn!(error = %e, "tray-alerts: menu rebuild failed");
                    } else {
                        tracing::debug!(count = alerts.len(), "tray-alerts: refreshed");
                    }
                    // R-1.1 + R-4.3: notify for pressing and reminder_active items
                    check_notifications(&app, &alerts, &reminders.active);
                }
                Err(e) => {
                    tracing::debug!(error = %e, "tray-alerts: backend unreachable, clearing");
                    let _ = crate::tray::update_alerts(&app, &[], &[], &[]);
                }
            }

            // R-2.1: record time before sleep for wake detection
            app.state::<Mutex<TauriNotificationState>>()
                .lock()
                .unwrap()
                .last_poll_at = Instant::now();

            tokio::time::sleep(POLL_INTERVAL).await;

            // R-2.2–R-2.4: detect sleep/wake and reset notification timer
            {
                let state_ref = app.state::<Mutex<TauriNotificationState>>();
                let mut state = state_ref.lock().unwrap();
                let actual_elapsed = state.last_poll_at.elapsed();
                if actual_elapsed > POLL_INTERVAL + SLEEP_THRESHOLD {
                    state.last_check_at = Instant::now();
                    tracing::info!(
                        actual_elapsed_secs = actual_elapsed.as_secs_f64(),
                        "notif-wake-detected"
                    );
                }
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_alert(id: &str) -> Alert {
        Alert {
            id: id.to_string(),
            title: id.to_string(),
            is_overdue: true,
            hours_left: None,
            days_overdue: Some(1),
            urgency_label: None,
        }
    }

    // (a) early-return when NOTIF_INTERVAL has not elapsed
    #[test]
    fn test_no_candidates_interval_not_elapsed() {
        let mut state = TauriNotificationState::new();
        // last_check_at defaults to Instant::now(), so elapsed < NOTIF_INTERVAL
        let alerts = vec![make_alert("A")];
        let result = select_candidates(&mut state, &alerts);
        assert!(result.is_empty());
    }

    // (b) daily cap of 8 blocks all candidates
    #[test]
    fn test_no_candidates_daily_cap_reached() {
        let mut state = TauriNotificationState::new();
        state.dialogs_today = MAX_DIALOGS_PER_DAY;
        state.dialogs_date = today_date_string();
        state.last_check_at = Instant::now() - NOTIF_INTERVAL - Duration::from_secs(1);
        let alerts = vec![make_alert("A")];
        let result = select_candidates(&mut state, &alerts);
        assert!(result.is_empty());
    }

    // (c) item notified within ITEM_COOLDOWN is excluded; others pass
    #[test]
    fn test_item_on_cooldown_excluded() {
        let mut state = TauriNotificationState::new();
        state.last_check_at = Instant::now() - NOTIF_INTERVAL - Duration::from_secs(1);
        state.dialogs_date = today_date_string();
        state.last_notified.insert("A".to_string(), Instant::now());
        let alerts = vec![make_alert("A"), make_alert("B")];
        let result = select_candidates(&mut state, &alerts);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].id, "B");
    }

    // (d) at most 3 candidates returned even when more are available
    #[test]
    fn test_at_most_3_candidates() {
        let mut state = TauriNotificationState::new();
        state.last_check_at = Instant::now() - NOTIF_INTERVAL - Duration::from_secs(1);
        state.dialogs_date = today_date_string();
        let alerts: Vec<Alert> = (0..5).map(|i| make_alert(&format!("item-{i}"))).collect();
        let result = select_candidates(&mut state, &alerts);
        assert_eq!(result.len(), 3);
    }

    fn make_reminder(id: &str) -> ReminderAlert {
        ReminderAlert {
            id: id.to_string(),
            title: id.to_string(),
            reminder_date: "2026-05-30".to_string(),
            proyecto: None,
        }
    }

    // (e) reminder on cooldown is excluded; others pass
    #[test]
    fn test_reminder_on_cooldown_excluded() {
        let mut state = TauriNotificationState::new();
        state.last_check_at = Instant::now() - NOTIF_INTERVAL - Duration::from_secs(1);
        state.dialogs_date = today_date_string();
        state.last_notified.insert("REM-A".to_string(), Instant::now());
        let reminders = vec![make_reminder("REM-A"), make_reminder("REM-B")];
        let result = select_reminder_candidates(&state, &reminders);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].id, "REM-B");
    }

    // (f) interval guard blocks reminder candidates
    #[test]
    fn test_reminder_blocked_by_interval_guard() {
        let state = TauriNotificationState::new();
        // last_check_at defaults to Instant::now() → elapsed < NOTIF_INTERVAL
        let reminders = vec![make_reminder("REM-A")];
        let result = select_reminder_candidates(&state, &reminders);
        assert!(result.is_empty());
    }
}
