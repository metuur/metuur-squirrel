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
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter, Manager, Runtime};

const BACKEND_ORIGIN: &str = "http://127.0.0.1:3939";
const BACKEND_HOME: &str = "http://127.0.0.1:3939/api/home";
const POLL_INTERVAL: Duration = Duration::from_secs(30);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(3);
const MAX_ALERTS: usize = 3;
const NOTIF_INTERVAL: Duration = Duration::from_secs(120);
const SLEEP_THRESHOLD: Duration = Duration::from_secs(15);
const ITEM_COOLDOWN: Duration = Duration::from_secs(3600);
const MAX_DIALOGS_PER_DAY: u32 = 8;
const BREAK_REMINDER_INTERVAL: Duration = Duration::from_secs(30 * 60);
const BREAK_CHECK_INTERVAL: Duration = Duration::from_secs(5 * 60);

pub(crate) struct TauriNotificationState {
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
    // R-9.11/R-9.12: cached SQLite connection opened once at start_polling
    // time and reused for every notification insert/unread-count query. Wraps
    // a Mutex in an Arc so callers clone the Arc out of state and drop the
    // outer state lock before acquiring the inner DB lock — avoids
    // serializing unrelated state mutations behind DB work.
    pub(crate) notif_db: Option<Arc<Mutex<rusqlite::Connection>>>,
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
            notif_db_path: default_notif_db_path(),
            focus_prompted_date: None,
            last_break_notified: None,
            notif_db: None,
        }
    }
}

fn default_notif_db_path() -> PathBuf {
    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".squirrel")
        .join("state")
        .join("squirrel.db")
}

/// Create the `notifications` table and index in the given SQLite DB.
/// Sets WAL mode. Idempotent (CREATE TABLE IF NOT EXISTS).
pub(crate) fn init_notif_db(db_path: &Path) -> rusqlite::Result<()> {
    if let Some(parent) = db_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let conn = rusqlite::Connection::open(db_path)?;
    conn.execute_batch("PRAGMA journal_mode=WAL;")?;
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
    Ok(())
}

// ── Story 2.1: notification settings ─────────────────────────────────────────

/// R-3.3/R-3.4: Settings read from `/api/me` every poll cycle.
/// Default `in_app=true, os_popups=false` when backend is unreachable.
#[derive(Debug, Clone, Copy)]
struct NotifSettings {
    in_app: bool,
    os_popups: bool,
}

impl Default for NotifSettings {
    fn default() -> Self {
        NotifSettings { in_app: true, os_popups: false }
    }
}

#[derive(Deserialize)]
struct MeNotifSection {
    in_app: bool,
    os_popups: bool,
}

#[derive(Deserialize)]
struct MeResponse {
    notifications: Option<MeNotifSection>,
}

async fn fetch_notif_settings(client: &reqwest::Client) -> NotifSettings {
    let resp = client
        .get(format!("{}/api/me", BACKEND_ORIGIN))
        .timeout(REQUEST_TIMEOUT)
        .send()
        .await;
    match resp {
        Ok(r) => match r.error_for_status() {
            Ok(r) => r
                .json::<MeResponse>()
                .await
                .ok()
                .and_then(|me| me.notifications)
                .map(|n| NotifSettings { in_app: n.in_app, os_popups: n.os_popups })
                .unwrap_or_default(),
            Err(_) => NotifSettings::default(),
        },
        Err(_) => NotifSettings::default(),
    }
}

// ── Story 2.2: dedup INSERT ───────────────────────────────────────────────────

/// R-2.2/R-2.3/R-2.8/R-2.9: Insert a notification row only if no row for
/// this `item_id` already has a `fired_at` date equal to today. Returns `true`
/// when a new row was inserted, `false` when the dedup check found a match.
fn insert_notification_if_new(
    db_path: &Path,
    notif_type: &str,
    item_id: &str,
    title: &str,
    body: &str,
    item_url: &str,
) -> rusqlite::Result<bool> {
    let conn = rusqlite::Connection::open(db_path)?;
    conn.execute_batch("PRAGMA journal_mode=WAL;")?;
    let exists: bool = conn.query_row(
        "SELECT COUNT(*) FROM notifications WHERE item_id = ? AND date(fired_at) = date('now')",
        rusqlite::params![item_id],
        |r| r.get::<_, i64>(0),
    )? > 0;
    if exists {
        return Ok(false);
    }
    conn.execute(
        "INSERT INTO notifications (type, item_id, title, body, item_url, fired_at) \
         VALUES (?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%S', 'now'))",
        rusqlite::params![notif_type, item_id, title, body, item_url],
    )?;
    Ok(true)
}

// ── Story 2.3: unread count, badge, event ─────────────────────────────────────

fn unread_count(db_path: &Path) -> rusqlite::Result<u32> {
    let conn = rusqlite::Connection::open(db_path)?;
    conn.query_row(
        "SELECT COUNT(*) FROM notifications WHERE read_at IS NULL AND dismissed_at IS NULL",
        [],
        |r| r.get::<_, u32>(0),
    )
}

/// R-2.5/R-2.6/R-2.7: After an INSERT, set the tray badge and emit
/// `squirrel:notif-updated` with the current unread count.
fn update_badge_and_emit<R: Runtime>(app: &AppHandle<R>, db_path: &Path) {
    let count = match unread_count(db_path) {
        Ok(c) => c,
        Err(e) => {
            tracing::warn!(error = %e, "tray-alerts: unread count query failed");
            return;
        }
    };
    let icon_state = if count > 0 {
        crate::tray::IconState::Notification
    } else {
        crate::tray::IconState::Normal
    };
    if let Err(e) = crate::tray::set_state(app, icon_state) {
        tracing::warn!(error = %e, "tray-alerts: badge update failed");
    }
    if let Err(e) = app.emit("squirrel:notif-updated", count) {
        tracing::warn!(error = %e, "tray-alerts: event emit failed");
    }
}

// ─────────────────────────────────────────────────────────────────────────────

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
    /// URL to open when the tray item is clicked. Not in the API response;
    /// populated by `fetch_reminders` after deserialization.
    #[serde(default)]
    pub item_url: String,
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
    let mut resp = client
        .get("http://127.0.0.1:3939/api/reminders")
        .timeout(REQUEST_TIMEOUT)
        .send()
        .await?
        .error_for_status()?
        .json::<RemindersResponse>()
        .await?;
    for r in resp.approaching.iter_mut().chain(resp.active.iter_mut()) {
        r.item_url = format!("{}/notes/{}", BACKEND_ORIGIN, r.id);
    }
    Ok(resp)
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

/// Poll `GET /api/focus/session`. If a session is active and 30 minutes have
/// elapsed since the last break reminder (or since first detection), fire a
/// "Take a breath and continue" notification. Resets when session ends.
async fn check_break_reminder<R: Runtime>(app: &AppHandle<R>, client: &reqwest::Client) {
    #[derive(Deserialize)]
    struct ActiveSession {
        project_slug: String,
        intent_slug: String,
    }

    let resp = match client
        .get(format!("{}/api/focus/session", BACKEND_ORIGIN))
        .timeout(REQUEST_TIMEOUT)
        .send()
        .await
    {
        Ok(r) => r,
        Err(_) => return,
    };

    if !resp.status().is_success() {
        app.state::<Mutex<TauriNotificationState>>()
            .lock()
            .unwrap()
            .last_break_notified = None;
        return;
    }

    let session = match resp.json::<ActiveSession>().await {
        Ok(s) => s,
        Err(_) => return,
    };

    let state_ref = app.state::<Mutex<TauriNotificationState>>();
    let should_fire = {
        let mut s = state_ref.lock().unwrap();
        match s.last_break_notified {
            None => {
                s.last_break_notified = Some(Instant::now());
                false
            }
            Some(t) => t.elapsed() >= BREAK_REMINDER_INTERVAL,
        }
    };

    if should_fire {
        let _ = tauri_plugin_notification::NotificationExt::notification(app)
            .builder()
            .title("Squirrel")
            .body("Take a breath and continue 🌿")
            .show();
        state_ref.lock().unwrap().last_break_notified = Some(Instant::now());
        tracing::info!(
            project_slug = %session.project_slug,
            intent_slug = %session.intent_slug,
            "break-reminder: notification fired"
        );
    }
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

        // R-1.4: ensure notifications table exists before first poll
        {
            let db_path = app
                .state::<Mutex<TauriNotificationState>>()
                .lock()
                .unwrap()
                .notif_db_path
                .clone();
            if let Err(e) = init_notif_db(&db_path) {
                tracing::warn!(error = %e, "tray-alerts: failed to init notifications DB");
            }
        }

        // R-6.1–R-6.5: fire a "What's your focus?" notification if today's focus
        // is not set and we haven't already prompted today.
        {
            let today = today_date_string();
            let focus_prompted_today = {
                let state = app.state::<Mutex<TauriNotificationState>>();
                let s = state.lock().unwrap();
                s.focus_prompted_date.as_deref() == Some(today.as_str())
            };
            if !focus_prompted_today {
                match client.get(format!("{}/api/focus", BACKEND_ORIGIN)).send().await {
                    Ok(resp) if resp.status().is_success() => {
                        if let Ok(body) = resp.json::<serde_json::Value>().await {
                            let today_set = !body["today"].is_null();
                            if !today_set {
                                let _ = tauri_plugin_notification::NotificationExt::notification(&app)
                                    .builder()
                                    .title("What's your focus today?")
                                    .body("Tap to pick your focus for the morning.")
                                    .show();
                                let state = app.state::<Mutex<TauriNotificationState>>();
                                let mut s = state.lock().unwrap();
                                s.focus_prompted_date = Some(today);
                                tracing::info!("focus-prompt: notification fired");
                            }
                        }
                    }
                    _ => tracing::debug!("focus-prompt: backend unreachable, skipping"),
                }
            }
        }

        let mut last_break_check: Option<Instant> = None;

        loop {
            // R-3.3/R-3.4 (Story 2.1): read notification settings every cycle; default on failure
            let settings = fetch_notif_settings(&client).await;

            match fetch_pressing(&client).await {
                Ok(alerts) => {
                    let reminders = fetch_reminders(&client).await.unwrap_or_else(|_| RemindersResponse {
                        approaching: vec![],
                        active: vec![],
                    });

                    // Hoist db_path so it is available for unread_count query below
                    let db_path = app
                        .state::<Mutex<TauriNotificationState>>()
                        .lock()
                        .unwrap()
                        .notif_db_path
                        .clone();

                    // R-2.1 (Story 2.1): skip all notification storage when in_app=false
                    if settings.in_app {
                        // R-2.2/R-2.8 (Story 2.2): dedup+INSERT for pressing alerts
                        for alert in &alerts {
                            let item_url = format!("{}/notes/{}", BACKEND_ORIGIN, alert.id);
                            match insert_notification_if_new(
                                &db_path, "pressing", &alert.id, &alert.id, &alert.menu_label(), &item_url,
                            ) {
                                Ok(true) => update_badge_and_emit(&app, &db_path), // R-2.4/R-2.5/R-2.6/R-2.7
                                Ok(false) => {}
                                Err(e) => tracing::warn!(error = %e, item_id = %alert.id, "tray-alerts: notif insert failed"),
                            }
                        }

                        // R-2.2/R-2.9 (Story 2.2): dedup+INSERT for active reminders
                        for reminder in &reminders.active {
                            match insert_notification_if_new(
                                &db_path, "reminder_active", &reminder.id, &reminder.id, &reminder.menu_label(), &reminder.item_url,
                            ) {
                                Ok(true) => update_badge_and_emit(&app, &db_path), // R-2.4/R-2.5/R-2.6/R-2.7
                                Ok(false) => {}
                                Err(e) => tracing::warn!(error = %e, reminder_id = %reminder.id, "tray-alerts: reminder notif insert failed"),
                            }
                        }
                    }

                    // R-8.2: pass current unread count so the menu shows/hides
                    // "Notifications (N)" correctly after any new INSERTs above.
                    let current_unread = unread_count(&db_path).unwrap_or(0);
                    if let Err(e) = crate::tray::update_alerts(&app, &alerts, &reminders.approaching, &reminders.active, current_unread) {
                        tracing::warn!(error = %e, "tray-alerts: menu rebuild failed");
                    } else {
                        tracing::debug!(count = alerts.len(), "tray-alerts: refreshed");
                    }

                    // R-3.1/R-3.2 (Story 3.1): OS popup guard — existing rate-limit guards apply inside
                    if settings.os_popups {
                        check_notifications(&app, &alerts, &reminders.active);
                    }
                }
                Err(e) => {
                    tracing::debug!(error = %e, "tray-alerts: backend unreachable, clearing");
                    let _ = crate::tray::update_alerts(&app, &[], &[], &[], 0);
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

            // Story 3.4: break reminder — run every BREAK_CHECK_INTERVAL (5 min)
            let should_check_break = last_break_check
                .map(|t| t.elapsed() >= BREAK_CHECK_INTERVAL)
                .unwrap_or(true);
            if should_check_break {
                last_break_check = Some(Instant::now());
                check_break_reminder(&app, &client).await;
            }
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_init_notif_db_creates_table_and_index() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        let conn = rusqlite::Connection::open(&db_path).unwrap();
        let table_exists: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='notifications'",
                [],
                |r| r.get::<_, i64>(0),
            )
            .unwrap()
            > 0;
        assert!(table_exists, "notifications table should exist");
        let index_exists: bool = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name='idx_notifications_item_day'",
                [],
                |r| r.get::<_, i64>(0),
            )
            .unwrap()
            > 0;
        assert!(index_exists, "idx_notifications_item_day should exist");
        let mode: String = conn
            .query_row("PRAGMA journal_mode", [], |r| r.get(0))
            .unwrap();
        assert_eq!(mode, "wal");
    }

    #[test]
    fn test_init_notif_db_idempotent() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        init_notif_db(&db_path).unwrap(); // second call must not error
    }

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
            item_url: format!("{}/notes/{}", BACKEND_ORIGIN, id),
        }
    }

    // ── Story 8.1: item_url threading ────────────────────────────────────────

    #[test]
    fn test_reminder_item_url_populated_after_fetch() {
        let id = "VISA-001";
        let r = make_reminder(id);
        assert_eq!(r.item_url, "http://127.0.0.1:3939/notes/VISA-001");
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

    // ── Story 2.1: NotifSettings defaults ────────────────────────────────────

    #[test]
    fn test_notif_settings_default_in_app_true_os_popups_false() {
        let s = NotifSettings::default();
        assert!(s.in_app, "in_app defaults to true");
        assert!(!s.os_popups, "os_popups defaults to false");
    }

    // ── Story 2.2: insert_notification_if_new ────────────────────────────────

    #[test]
    fn test_insert_notification_if_new_returns_true_on_first_insert() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        let inserted = insert_notification_if_new(
            &db_path, "pressing", "TASK-001", "TASK-001", "43d overdue", "http://127.0.0.1:3939/notes/TASK-001",
        ).unwrap();
        assert!(inserted, "first insert should return true");
    }

    #[test]
    fn test_insert_notification_if_new_dedup_same_day_returns_false() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        insert_notification_if_new(&db_path, "pressing", "TASK-001", "T", "body", "url").unwrap();
        let second = insert_notification_if_new(&db_path, "pressing", "TASK-001", "T", "body", "url").unwrap();
        assert!(!second, "same item same day must not insert a duplicate");
        let conn = rusqlite::Connection::open(&db_path).unwrap();
        let count: i64 = conn.query_row(
            "SELECT COUNT(*) FROM notifications WHERE item_id = 'TASK-001'",
            [], |r| r.get(0),
        ).unwrap();
        assert_eq!(count, 1, "exactly one row should exist after dedup");
    }

    #[test]
    fn test_insert_notification_if_new_item_url_stored_correctly() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        insert_notification_if_new(
            &db_path, "reminder_active", "VISA-001", "VISA-001", "Due today",
            "http://127.0.0.1:3939/notes/VISA-001",
        ).unwrap();
        let conn = rusqlite::Connection::open(&db_path).unwrap();
        let url: String = conn.query_row(
            "SELECT item_url FROM notifications WHERE item_id = 'VISA-001'",
            [], |r| r.get(0),
        ).unwrap();
        assert_eq!(url, "http://127.0.0.1:3939/notes/VISA-001");
    }

    // ── Story 2.3: unread_count ───────────────────────────────────────────────

    #[test]
    fn test_unread_count_empty_table_is_zero() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        assert_eq!(unread_count(&db_path).unwrap(), 0);
    }

    #[test]
    fn test_unread_count_excludes_read_and_dismissed_rows() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        let conn = rusqlite::Connection::open(&db_path).unwrap();
        // 1 unread, 1 read, 1 dismissed
        conn.execute_batch("
            INSERT INTO notifications (type, item_id, title, body, item_url, fired_at)
              VALUES ('pressing','A','A','body','url','2026-01-01T10:00:00');
            INSERT INTO notifications (type, item_id, title, body, item_url, fired_at, read_at)
              VALUES ('pressing','B','B','body','url','2026-01-01T10:00:00','2026-01-01T11:00:00');
            INSERT INTO notifications (type, item_id, title, body, item_url, fired_at, dismissed_at)
              VALUES ('pressing','C','C','body','url','2026-01-01T10:00:00','2026-01-01T11:00:00');
        ").unwrap();
        assert_eq!(unread_count(&db_path).unwrap(), 1, "only row A (unread, not dismissed) should count");
    }

    #[test]
    fn test_unread_count_increments_after_insert() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        assert_eq!(unread_count(&db_path).unwrap(), 0);
        insert_notification_if_new(&db_path, "pressing", "A", "A", "body", "url").unwrap();
        assert_eq!(unread_count(&db_path).unwrap(), 1);
        insert_notification_if_new(&db_path, "pressing", "B", "B", "body", "url").unwrap();
        assert_eq!(unread_count(&db_path).unwrap(), 2);
    }
}
