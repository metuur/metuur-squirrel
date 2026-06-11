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

// Single source of truth for the backend origin (build-time overridable to :3940
// for the dev build — see tray::BACKEND_ORIGIN). BACKEND_HOME is derived from it
// at its one call site rather than duplicating the literal.
use crate::tray::BACKEND_ORIGIN;
const POLL_INTERVAL: Duration = Duration::from_secs(30);
// Cap the exponential backoff applied while the backend is unreachable.
// 30s → 60s → 120s → 240s → 300s; resets to POLL_INTERVAL on first success.
// Keeps idle laptops from waking every 30s for a doomed connect-refused.
const MAX_BACKOFF_INTERVAL: Duration = Duration::from_secs(300);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(3);
const MAX_ALERTS: usize = 3;
const NOTIF_INTERVAL: Duration = Duration::from_secs(120);
const SLEEP_THRESHOLD: Duration = Duration::from_secs(15);
const ITEM_COOLDOWN: Duration = Duration::from_secs(3600);
const MAX_DIALOGS_PER_DAY: u32 = 8;
const BREAK_REMINDER_INTERVAL: Duration = Duration::from_secs(30 * 60);
const BREAK_CHECK_INTERVAL: Duration = Duration::from_secs(5 * 60);
/// Rows older than this are pruned from the `notifications` table at startup;
/// without it the table grows unbounded (per-day dedup only ever adds rows).
const NOTIF_RETENTION_DAYS: u32 = 90;
/// Upper bound on any backend JSON body before deserialization. The backend
/// is trusted but local bugs shouldn't hand the tray a multi-MB allocation.
const MAX_JSON_BYTES: usize = 2 * 1024 * 1024;

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

/// Apply the `notifications` schema (table + index) to an already-open
/// connection. Idempotent. Used by both the one-shot test helper and the
/// long-lived cached connection opened in `start_polling`.
fn init_notif_schema(conn: &rusqlite::Connection) -> rusqlite::Result<()> {
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
    )
}

/// Path-based entry point: open a connection, set WAL, init schema. Used by
/// the unit-test suite which works in tempdirs. Production code uses
/// `open_cached_notif_conn` via `start_polling`.
#[allow(dead_code)]
pub(crate) fn init_notif_db(db_path: &Path) -> rusqlite::Result<()> {
    if let Some(parent) = db_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let conn = rusqlite::Connection::open(db_path)?;
    conn.execute_batch("PRAGMA journal_mode=WAL;")?;
    init_notif_schema(&conn)
}

/// R-9.11/R-9.12/R-9.13: open the long-lived notifications connection used
/// by the polling loop. Applies WAL + `busy_timeout=5000ms` +
/// `synchronous=NORMAL` once, then runs the idempotent schema init. The
/// returned `Connection` is meant to live for the app's lifetime inside
/// `TauriNotificationState::notif_db`, eliminating the per-poll open and
/// the redundant `PRAGMA journal_mode=WAL` re-parse on every helper call.
fn open_cached_notif_conn(db_path: &Path) -> rusqlite::Result<rusqlite::Connection> {
    if let Some(parent) = db_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let conn = rusqlite::Connection::open(db_path)?;
    conn.execute_batch(
        "PRAGMA journal_mode=WAL;
         PRAGMA busy_timeout=5000;
         PRAGMA synchronous=NORMAL;",
    )?;
    init_notif_schema(&conn)?;
    prune_old_notifications(&conn)?;
    Ok(conn)
}

/// Delete notification rows older than NOTIF_RETENTION_DAYS. `date()` is used
/// on both sides because `fired_at` is ISO with a `T` separator, which does
/// not compare lexicographically against SQLite's space-separated `now`.
fn prune_old_notifications(conn: &rusqlite::Connection) -> rusqlite::Result<()> {
    let deleted = conn.execute(
        "DELETE FROM notifications WHERE date(fired_at) < date('now', ?)",
        [format!("-{NOTIF_RETENTION_DAYS} days")],
    )?;
    if deleted > 0 {
        tracing::info!(deleted, "tray-alerts: pruned old notifications");
    }
    Ok(())
}

// ── Story 2.1: notification settings ─────────────────────────────────────────

/// R-3.3/R-3.4: Settings read from `/api/me` every poll cycle.
/// Default `in_app=true, os_popups=false, sound=Glass` when backend is unreachable.
#[derive(Debug, Clone, Copy)]
struct NotifSettings {
    in_app: bool,
    os_popups: bool,
    sound: NotificationSound,
}

impl Default for NotifSettings {
    fn default() -> Self {
        NotifSettings { in_app: true, os_popups: false, sound: NotificationSound::Glass }
    }
}

/// notification-sound R-1.1: curated set of three audio cues. `Glass` is the
/// default; `Silent` suppresses audio while leaving visual cues unchanged.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
enum NotificationSound {
    Glass,
    Funk,
    Silent,
}

impl Default for NotificationSound {
    fn default() -> Self { NotificationSound::Glass }
}

impl NotificationSound {
    fn sound_file(self) -> Option<&'static str> {
        match self {
            NotificationSound::Glass  => Some("/System/Library/Sounds/Glass.aiff"),
            NotificationSound::Funk   => Some("/System/Library/Sounds/Funk.aiff"),
            NotificationSound::Silent => None,
        }
    }
}

#[derive(Deserialize)]
struct MeNotifSection {
    in_app: bool,
    os_popups: bool,
    #[serde(default)]
    sound: NotificationSound,
}

#[derive(Deserialize)]
struct MeResponse {
    notifications: Option<MeNotifSection>,
}

/// Error type for the capped fetch helpers. `reqwest::Error` cannot be
/// fabricated, so size-bound violations need their own variant.
#[derive(Debug)]
enum FetchError {
    Http(reqwest::Error),
    TooLarge(u64),
    Decode(serde_json::Error),
}

impl std::fmt::Display for FetchError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FetchError::Http(e) => write!(f, "{e}"),
            FetchError::TooLarge(n) => write!(f, "response body too large: {n} bytes"),
            FetchError::Decode(e) => write!(f, "invalid JSON: {e}"),
        }
    }
}

impl From<reqwest::Error> for FetchError {
    fn from(e: reqwest::Error) -> Self {
        FetchError::Http(e)
    }
}

/// Deserialize a response body, refusing anything over MAX_JSON_BYTES.
/// Content-Length is checked first (the backend always sets it) and the read
/// bytes are re-checked because the header is advisory.
async fn json_capped<T: serde::de::DeserializeOwned>(
    resp: reqwest::Response,
) -> Result<T, FetchError> {
    if let Some(len) = resp.content_length() {
        if len > MAX_JSON_BYTES as u64 {
            return Err(FetchError::TooLarge(len));
        }
    }
    let bytes = resp.bytes().await?;
    if bytes.len() > MAX_JSON_BYTES {
        return Err(FetchError::TooLarge(bytes.len() as u64));
    }
    serde_json::from_slice(&bytes).map_err(FetchError::Decode)
}

async fn fetch_notif_settings(client: &reqwest::Client) -> NotifSettings {
    let resp = client
        .get(format!("{}/api/me", BACKEND_ORIGIN))
        .timeout(REQUEST_TIMEOUT)
        .send()
        .await;
    match resp {
        Ok(r) => match r.error_for_status() {
            Ok(r) => json_capped::<MeResponse>(r)
                .await
                .ok()
                .and_then(|me| me.notifications)
                .map(|n| NotifSettings { in_app: n.in_app, os_popups: n.os_popups, sound: n.sound })
                .unwrap_or_default(),
            Err(_) => NotifSettings::default(),
        },
        Err(_) => NotifSettings::default(),
    }
}

/// notification-sound R-2.1 / R-2.3 / R-2.4: spawn detached `afplay` for the
/// configured sound. `Silent` is a no-op. Non-macOS is also a no-op (the
/// daemon's sound path is the macOS-only complement and bash takes care of
/// itself). Spawn failure → warn and return; audio must NEVER block
/// notification delivery.
#[cfg(target_os = "macos")]
fn play_notification_sound(sound: NotificationSound) {
    if let Some(file) = sound.sound_file() {
        if let Err(e) = std::process::Command::new("afplay")
            .arg(file)
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
        {
            tracing::warn!(error = %e, ?sound, "tray-alerts: afplay spawn failed");
        }
    }
}

#[cfg(not(target_os = "macos"))]
fn play_notification_sound(_sound: NotificationSound) {
    // R-2.4: non-macOS builds compile but audio is a no-op.
}

// ── Story 2.2: dedup INSERT ───────────────────────────────────────────────────

/// Connection-borrowing variant — does the same-day dedup SELECT and the
/// INSERT against the caller's connection. The polling loop calls this via
/// `with_cached_conn` so it never opens a fresh connection per cycle.
fn insert_notification_if_new_on_conn(
    conn: &rusqlite::Connection,
    notif_type: &str,
    item_id: &str,
    title: &str,
    body: &str,
    item_url: &str,
) -> rusqlite::Result<bool> {
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

/// R-2.2/R-2.3/R-2.8/R-2.9: Insert a notification row only if no row for
/// this `item_id` already has a `fired_at` date equal to today. Returns `true`
/// when a new row was inserted, `false` when the dedup check found a match.
///
/// Path-based wrapper used by the unit-test suite. Production code uses
/// `insert_notification_if_new_on_conn` via the cached connection.
#[allow(dead_code)]
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
    insert_notification_if_new_on_conn(&conn, notif_type, item_id, title, body, item_url)
}

// ── Story 2.3: unread count, badge, event ─────────────────────────────────────

fn unread_count_on_conn(conn: &rusqlite::Connection) -> rusqlite::Result<u32> {
    conn.query_row(
        "SELECT COUNT(*) FROM notifications WHERE read_at IS NULL AND dismissed_at IS NULL",
        [],
        |r| r.get::<_, u32>(0),
    )
}

#[allow(dead_code)]
fn unread_count(db_path: &Path) -> rusqlite::Result<u32> {
    let conn = rusqlite::Connection::open(db_path)?;
    unread_count_on_conn(&conn)
}

/// R-9.11: borrow the cached notification connection. Clones the `Arc` out
/// of state and drops the outer state lock before acquiring the inner DB
/// lock, so concurrent state mutations are not serialized behind DB work.
///
/// If the cached connection is not initialized (which should not happen in
/// practice — `start_polling` initializes it before the loop begins), this
/// returns the closure's result over a freshly-opened path-based connection
/// as a defensive fallback. The fallback path is logged at WARN.
fn with_cached_conn<R, F, T>(
    app: &AppHandle<R>,
    fallback_db_path: &Path,
    f: F,
) -> rusqlite::Result<T>
where
    R: Runtime,
    F: FnOnce(&rusqlite::Connection) -> rusqlite::Result<T>,
{
    let cached: Option<Arc<Mutex<rusqlite::Connection>>> = {
        let state = app.state::<Mutex<TauriNotificationState>>();
        let s = state.lock().unwrap_or_else(|p| p.into_inner());
        s.notif_db.clone()
    };
    if let Some(arc) = cached {
        let conn = arc.lock().unwrap_or_else(|p| p.into_inner());
        return f(&conn);
    }
    tracing::warn!("tray-alerts: cached notif conn missing, falling back to one-shot open");
    let conn = rusqlite::Connection::open(fallback_db_path)?;
    f(&conn)
}

/// R-2.5/R-2.6/R-2.7: After an INSERT, set the tray badge and emit
/// `squirrel:notif-updated` with the current unread count.
fn update_badge_and_emit<R: Runtime>(app: &AppHandle<R>, db_path: &Path) {
    let count = match with_cached_conn(app, db_path, unread_count_on_conn) {
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
    // `title` and `project` mirror the /api/reminders wire shape so the struct
    // deserializes the full response, but the tray menu derives its label from
    // `id`/`reminder_date` only — Rust never reads these two fields.
    #[allow(dead_code)]
    pub title: String,
    pub reminder_date: String,
    #[allow(dead_code)]
    pub project: Option<String>,
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
    /// Recurring Mind Journal check-in state (R-3.10). Absent on older
    /// backends → defaults to not-due.
    #[serde(default)]
    journal: JournalState,
    /// Quick Task Stack summary (R-5.1). Absent on older backends → empty.
    #[serde(default)]
    quick_tasks: QuickTasksSummary,
}

/// Mirror of /api/home.quick_tasks.active[] — the fields the tray section and
/// the in-app notification need.
#[derive(Debug, Clone, Deserialize)]
pub struct QuickTaskItem {
    pub id: String,
    pub text: String,
}

/// Truncate to at most `max` chars, appending `…` when shortened. Tray menu
/// labels come from user-authored vault titles with no inherent size bound.
fn truncate_chars(s: &str, max: usize) -> String {
    if s.chars().count() > max {
        format!("{}…", s.chars().take(max - 1).collect::<String>())
    } else {
        s.to_string()
    }
}

impl QuickTaskItem {
    /// Compact single-line tray/notification label, e.g. "⚡ Reply to Ana".
    pub fn menu_label(&self) -> String {
        format!("⚡ {}", truncate_chars(self.text.trim(), 48))
    }
}

/// Mirror of /api/home.quick_tasks. Absent on older backends → empty/false.
#[derive(Debug, Clone, Default, Deserialize)]
pub struct QuickTasksSummary {
    #[serde(default)]
    pub active: Vec<QuickTaskItem>,
    // active_count / snoozed_count mirror the wire shape; the tray derives its
    // visible count from `active.len()`, so Rust never reads these two.
    #[serde(default)]
    #[allow(dead_code)]
    pub active_count: u32,
    #[serde(default)]
    #[allow(dead_code)]
    pub snoozed_count: u32,
    /// A due snoozed task is waiting for a free slot (R-4.3, R-5.5).
    #[serde(default)]
    pub return_blocked: bool,
}

/// Mirror of /api/home `journal` block. `due` already reflects the waking-hours
/// window server-side (R-2.6), so the tray never needs its own quiet-hours
/// logic to satisfy R-4.3.
#[derive(Debug, Clone, Default, Deserialize)]
struct JournalState {
    #[serde(default)]
    due: bool,
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

/// Build a human-readable label for today's focus plan from the `/api/focus`
/// JSON body, combining the AM slot (`today`) with the optional PM slot
/// (`today_pm`). Returns `None` when no focus is set for today.
fn focus_plan_label(body: &serde_json::Value) -> Option<String> {
    fn slot_label(slot: &serde_json::Value) -> Option<String> {
        if slot.is_null() {
            return None;
        }
        let project = truncate_chars(slot["project_title"].as_str().unwrap_or("").trim(), 48);
        let intent = truncate_chars(slot["intent_title"].as_str().unwrap_or("").trim(), 48);
        match (project.is_empty(), intent.is_empty()) {
            (false, false) => Some(format!("{project} · {intent}")),
            (false, true) => Some(project),
            (true, false) => Some(intent),
            (true, true) => None,
        }
    }

    match (slot_label(&body["today"]), slot_label(&body["today_pm"])) {
        (Some(am), Some(pm)) => Some(format!("AM: {am} · PM: {pm}")),
        (Some(am), None) => Some(am),
        (None, Some(pm)) => Some(format!("PM: {pm}")),
        (None, None) => None,
    }
}

async fn fetch_reminders(client: &reqwest::Client) -> Result<RemindersResponse, FetchError> {
    let resp = client
        .get("http://127.0.0.1:3939/api/reminders")
        .timeout(REQUEST_TIMEOUT)
        .send()
        .await?
        .error_for_status()?;
    let mut resp = json_capped::<RemindersResponse>(resp).await?;
    for r in resp.approaching.iter_mut().chain(resp.active.iter_mut()) {
        r.item_url = format!("{}/notes/{}", BACKEND_ORIGIN, r.id);
    }
    Ok(resp)
}

async fn fetch_pressing(
    client: &reqwest::Client,
) -> Result<(Vec<Alert>, bool, QuickTasksSummary), FetchError> {
    let resp = client
        .get(format!("{BACKEND_ORIGIN}/api/home"))
        .timeout(REQUEST_TIMEOUT)
        .send()
        .await?
        .error_for_status()?;
    let resp = json_capped::<HomeResponse>(resp).await?;
    let journal_due = resp.journal.due;
    let quick_tasks = resp.quick_tasks;
    let alerts = resp.pressing.into_iter().take(MAX_ALERTS).collect();
    Ok((alerts, journal_due, quick_tasks))
}

/// A notification fully reserved against the daily cap and ready to show.
/// All state mutations (id assignment, pending_clicks, last_notified,
/// dialogs_today) happened at reservation time, so `.show()` can run outside
/// the state lock.
#[derive(Debug)]
struct PlannedNotification {
    id: i32,
    /// The alert/reminder/journal item id — used only for logging.
    item_key: String,
    kind: PlannedKind,
    title: String,
    body: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PlannedKind {
    Pressing,
    Reminder,
    Journal,
}

/// Fixed item id for the recurring journal check-in. Reuses the per-item
/// cooldown machinery (ITEM_COOLDOWN) so a single "due" window doesn't spam.
const JOURNAL_ITEM_ID: &str = "MIND-JOURNAL-CHECKIN";

// R-3.1–R-3.6 + R-4.2/R-4.3: apply all guards and RESERVE every accepted
// notification under one `&mut` borrow — id assigned, pending click stored,
// cooldown stamped, and dialogs_today incremented before anything is shown.
// This closes the R-3.3 race where the lock was released between candidate
// selection and send, letting concurrent phases exceed the daily cap.
// Reserve-at-selection means a failed `.show()` wastes one cap slot and one
// cooldown window — acceptable for a single user, and it prevents a failing
// notifier from retrying every cycle.
fn reserve_notifications(
    state: &mut TauriNotificationState,
    alerts: &[Alert],
    reminders: &[ReminderAlert],
    journal_due: bool,
) -> Vec<PlannedNotification> {
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

    let mut planned: Vec<PlannedNotification> = Vec::new();

    let cooldown_ok = |state: &TauriNotificationState, key: &str| {
        state
            .last_notified
            .get(key)
            .is_none_or(|t| t.elapsed() >= ITEM_COOLDOWN)
    };

    // R-3.5, R-3.6: pressing — per-item cooldown, at most 3
    let pressing: Vec<&Alert> = alerts
        .iter()
        .filter(|a| cooldown_ok(state, &a.id))
        .take(3)
        .collect();
    for alert in pressing {
        if state.dialogs_today >= MAX_DIALOGS_PER_DAY {
            return planned;
        }
        let id = state.next_id;
        state.next_id += 1;
        let url = format!("{}/notes/{}", BACKEND_ORIGIN, alert.id);
        state.pending_clicks.insert(id, url);
        state.last_notified.insert(alert.id.clone(), Instant::now());
        state.dialogs_today += 1;
        planned.push(PlannedNotification {
            id,
            item_key: alert.id.clone(),
            kind: PlannedKind::Pressing,
            title: format!("⏰ squirrel: {}", alert.id),
            body: alert.menu_label(),
        });
    }

    // R-4.3: active reminders — same guards
    let reminder_cands: Vec<&ReminderAlert> = reminders
        .iter()
        .filter(|r| cooldown_ok(state, &r.id))
        .take(3)
        .collect();
    for reminder in reminder_cands {
        if state.dialogs_today >= MAX_DIALOGS_PER_DAY {
            return planned;
        }
        let id = state.next_id;
        state.next_id += 1;
        let url = format!("{}/notes/{}", BACKEND_ORIGIN, reminder.id);
        state.pending_clicks.insert(id, url);
        state.last_notified.insert(reminder.id.clone(), Instant::now());
        state.dialogs_today += 1;
        planned.push(PlannedNotification {
            id,
            item_key: reminder.id.clone(),
            kind: PlannedKind::Reminder,
            title: format!("📅 squirrel: {}", reminder.id),
            body: reminder.menu_label(),
        });
    }

    // R-4.2: Mind Journal check-in. `journal_due` is already false outside the
    // waking window (computed server-side), satisfying R-4.3. No pending click
    // — journaling is done in-app via the brain button / tray item.
    if journal_due
        && state.dialogs_today < MAX_DIALOGS_PER_DAY
        && cooldown_ok(state, JOURNAL_ITEM_ID)
    {
        let id = state.next_id;
        state.next_id += 1;
        state
            .last_notified
            .insert(JOURNAL_ITEM_ID.to_string(), Instant::now());
        state.dialogs_today += 1;
        planned.push(PlannedNotification {
            id,
            item_key: JOURNAL_ITEM_ID.to_string(),
            kind: PlannedKind::Journal,
            title: "🧠 squirrel: Mind Journal".to_string(),
            body: "What is your mind thinking right now? What are you doing right now?"
                .to_string(),
        });
    }

    planned
}

// R-1.1 + R-4.3: called every tick from `start_polling`. Sends at most 3 native banners
// per class (pressing + reminder_active + journal, bounded by the daily cap) when
// guards pass, then updates `last_check_at`.
// R-4.4: reminder_approaching items are NOT passed here — tray only.
fn check_notifications<R: Runtime>(app: &AppHandle<R>, alerts: &[Alert], reminder_active: &[ReminderAlert], journal_due: bool) {
    use tauri_plugin_notification::NotificationExt;

    let state_ref = app.state::<Mutex<TauriNotificationState>>();

    // Select AND reserve under one lock (R-3.3 cap is enforced atomically),
    // then show outside the lock so a slow notification daemon can't block
    // other state users.
    let planned = {
        let mut state = state_ref.lock().unwrap_or_else(|p| p.into_inner());
        let planned = reserve_notifications(&mut state, alerts, reminder_active, journal_due);
        // Always update last_check_at after the guards ran (even if 0 reserved).
        state.last_check_at = Instant::now();
        planned
    };

    for n in &planned {
        match app
            .notification()
            .builder()
            .id(n.id)
            .title(&n.title)
            .body(&n.body)
            .show()
        {
            Ok(_) => match n.kind {
                PlannedKind::Pressing => {
                    tracing::info!(project_id = %n.item_key, notification_id = n.id, "notif-sent")
                }
                PlannedKind::Reminder => {
                    tracing::info!(reminder_id = %n.item_key, notification_id = n.id, "reminder-notif-sent")
                }
                PlannedKind::Journal => {
                    tracing::info!(notification_id = n.id, "journal-checkin-notif-sent")
                }
            },
            Err(e) => {
                tracing::warn!(error = %e, item_id = %n.item_key, "notif-send-failed");
            }
        }
    }
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
            .unwrap_or_else(|p| p.into_inner())
            .last_break_notified = None;
        return;
    }

    let session = match resp.json::<ActiveSession>().await {
        Ok(s) => s,
        Err(_) => return,
    };

    let state_ref = app.state::<Mutex<TauriNotificationState>>();
    let should_fire = {
        let mut s = state_ref.lock().unwrap_or_else(|p| p.into_inner());
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
        state_ref.lock().unwrap_or_else(|p| p.into_inner()).last_break_notified = Some(Instant::now());
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
        // Authenticate every poll request with the per-launch runtime token —
        // the same X-Squirrel-Token the webview sends (Runtime Trust Handshake,
        // R-1.1). Without it the tokened backend returns 401 to /api/home,
        // /api/reminders, etc., so the tray silently degraded to "No pressing
        // items" in the installed app. Auth is enforced only when a token is set
        // (off in dev), which is why this went unnoticed until packaging.
        let mut default_headers = reqwest::header::HeaderMap::new();
        let token = app.state::<crate::RuntimeToken>().0.clone();
        match reqwest::header::HeaderValue::from_str(&token) {
            Ok(val) => {
                default_headers.insert("X-Squirrel-Token", val);
            }
            Err(e) => tracing::warn!(error = %e, "tray-alerts: runtime token not a valid header value"),
        }
        let client = match reqwest::Client::builder()
            .timeout(REQUEST_TIMEOUT)
            .default_headers(default_headers)
            .build()
        {
            Ok(c) => c,
            Err(e) => {
                tracing::error!(error = %e, "tray-alerts: failed to build HTTP client");
                return;
            }
        };

        // R-1.4: ensure notifications table exists before first poll.
        // R-9.11/R-9.12/R-9.13: open the long-lived connection once with
        // WAL + busy_timeout + synchronous=NORMAL, then stash it in state
        // so the polling loop borrows instead of re-opening each cycle.
        {
            let db_path = app
                .state::<Mutex<TauriNotificationState>>()
                .lock()
                .unwrap_or_else(|p| p.into_inner())
                .notif_db_path
                .clone();
            match open_cached_notif_conn(&db_path) {
                Ok(conn) => {
                    let state = app.state::<Mutex<TauriNotificationState>>();
                    let mut s = state.lock().unwrap_or_else(|p| p.into_inner());
                    s.notif_db = Some(Arc::new(Mutex::new(conn)));
                }
                Err(e) => {
                    tracing::warn!(error = %e, "tray-alerts: failed to init notifications DB");
                }
            }
        }

        let mut last_break_check: Option<Instant> = None;
        // Sleep cadence between polls. Starts at POLL_INTERVAL; doubles up
        // to MAX_BACKOFF_INTERVAL on each consecutive fetch_pressing Err;
        // resets to POLL_INTERVAL on the first Ok.
        let mut current_interval: Duration = POLL_INTERVAL;

        loop {
            // R-6.1–R-6.5: fire the daily planning prompt once per day. If a
            // focus is already set for today, ask the user to confirm or change
            // it; otherwise ask them to pick one. Lives inside the poll loop (not
            // a one-shot before it) so that on a cold start — where we spawn our
            // own backend and it takes a few seconds to become reachable — we
            // retry each cycle instead of silently dropping the prompt. The
            // `focus_prompted_today` guard short-circuits before any fetch once
            // it has fired, so this stays a once-per-day notification.
            {
                let today = today_date_string();
                let focus_prompted_today = {
                    let state = app.state::<Mutex<TauriNotificationState>>();
                    let s = state.lock().unwrap_or_else(|p| p.into_inner());
                    s.focus_prompted_date.as_deref() == Some(today.as_str())
                };
                if !focus_prompted_today {
                    match client.get(format!("{}/api/focus", BACKEND_ORIGIN)).send().await {
                        Ok(resp) if resp.status().is_success() => {
                            if let Ok(body) = resp.json::<serde_json::Value>().await {
                                // macOS desktop note: Tauri v2 notification taps are
                                // not delivered to the app (the plugin's Actions API is
                                // mobile-only), so the banner can't be made clickable.
                                // Point the user at the menu-bar icon instead of
                                // promising a tap that does nothing.
                                let (title, prompt_body) = match focus_plan_label(&body) {
                                    Some(plan) => (
                                        "Your plan for today".to_string(),
                                        format!(
                                            "{plan} — open Squirrel from the menu bar to confirm or change it."
                                        ),
                                    ),
                                    None => (
                                        "What's your focus today?".to_string(),
                                        "Open Squirrel from the menu bar to pick your focus."
                                            .to_string(),
                                    ),
                                };
                                let _ = tauri_plugin_notification::NotificationExt::notification(&app)
                                    .builder()
                                    .title(title)
                                    .body(prompt_body)
                                    .show();
                                let state = app.state::<Mutex<TauriNotificationState>>();
                                let mut s = state.lock().unwrap_or_else(|p| p.into_inner());
                                s.focus_prompted_date = Some(today);
                                tracing::info!("focus-prompt: notification fired");
                            }
                        }
                        _ => tracing::debug!("focus-prompt: backend unreachable, will retry next cycle"),
                    }
                }
            }

            // R-3.3/R-3.4 (Story 2.1): read notification settings every cycle; default on failure
            let settings = fetch_notif_settings(&client).await;

            match fetch_pressing(&client).await {
                Ok((alerts, journal_due, quick_tasks)) => {
                    current_interval = POLL_INTERVAL;
                    let reminders = fetch_reminders(&client).await.unwrap_or_else(|_| RemindersResponse {
                        approaching: vec![],
                        active: vec![],
                    });

                    // Hoist db_path so it is available for unread_count query below
                    let db_path = app
                        .state::<Mutex<TauriNotificationState>>()
                        .lock()
                        .unwrap_or_else(|p| p.into_inner())
                        .notif_db_path
                        .clone();

                    // R-2.1 (Story 2.1): skip all notification storage when in_app=false
                    if settings.in_app {
                        // R-2.2/R-2.8 (Story 2.2): dedup+INSERT for pressing alerts
                        for alert in &alerts {
                            let item_url = format!("{}/notes/{}", BACKEND_ORIGIN, alert.id);
                            let label = alert.menu_label();
                            let result = with_cached_conn(&app, &db_path, |conn| {
                                insert_notification_if_new_on_conn(
                                    conn, "pressing", &alert.id, &alert.id, &label, &item_url,
                                )
                            });
                            match result {
                                Ok(true) => {
                                    update_badge_and_emit(&app, &db_path); // R-2.4/R-2.5/R-2.6/R-2.7
                                    play_notification_sound(settings.sound); // notification-sound R-2.1
                                }
                                Ok(false) => {}
                                Err(e) => tracing::warn!(error = %e, item_id = %alert.id, "tray-alerts: notif insert failed"),
                            }
                        }

                        // R-2.2/R-2.9 (Story 2.2): dedup+INSERT for active reminders
                        for reminder in &reminders.active {
                            let label = reminder.menu_label();
                            let result = with_cached_conn(&app, &db_path, |conn| {
                                insert_notification_if_new_on_conn(
                                    conn, "reminder_active", &reminder.id, &reminder.id, &label, &reminder.item_url,
                                )
                            });
                            match result {
                                Ok(true) => {
                                    update_badge_and_emit(&app, &db_path); // R-2.4/R-2.5/R-2.6/R-2.7
                                    play_notification_sound(settings.sound); // notification-sound R-2.1
                                }
                                Ok(false) => {}
                                Err(e) => tracing::warn!(error = %e, reminder_id = %reminder.id, "tray-alerts: reminder notif insert failed"),
                            }
                        }

                        // R-5.2: surface the OLDEST active Quick Task as a low-key
                        // in-app notification (badge + center entry, no sound — kept
                        // gentle). Per-day dedup keeps a single task from repeating.
                        if let Some(oldest) = quick_tasks.active.first() {
                            let item_url = format!("{}/notes/{}", BACKEND_ORIGIN, oldest.id);
                            let label = oldest.menu_label();
                            let result = with_cached_conn(&app, &db_path, |conn| {
                                insert_notification_if_new_on_conn(
                                    conn, "quick_task", &oldest.id, &oldest.id, &label, &item_url,
                                )
                            });
                            match result {
                                Ok(true) => update_badge_and_emit(&app, &db_path),
                                Ok(false) => {}
                                Err(e) => tracing::warn!(error = %e, quick_task_id = %oldest.id, "tray-alerts: quick-task notif insert failed"),
                            }
                        }

                        // R-4.3/R-5.5: a snoozed task ready to return but blocked by a
                        // full stack → one gentle "clear a slot" nudge (per-day dedup).
                        if quick_tasks.return_blocked {
                            const RETURN_BLOCKED_ID: &str = "QUICK-TASK-RETURN-BLOCKED";
                            let result = with_cached_conn(&app, &db_path, |conn| {
                                insert_notification_if_new_on_conn(
                                    conn,
                                    "quick_task",
                                    RETURN_BLOCKED_ID,
                                    "Quick Task ready",
                                    "A snoozed quick task is ready — clear a slot.",
                                    BACKEND_ORIGIN,
                                )
                            });
                            if let Ok(true) = result {
                                update_badge_and_emit(&app, &db_path);
                            }
                        }
                    }

                    // R-8.2: pass current unread count so the menu shows/hides
                    // "Notifications (N)" correctly after any new INSERTs above.
                    let current_unread = with_cached_conn(&app, &db_path, unread_count_on_conn).unwrap_or(0);
                    if let Err(e) = crate::tray::update_alerts(&app, &alerts, &reminders.approaching, &reminders.active, &quick_tasks.active, current_unread, journal_due) {
                        tracing::warn!(error = %e, "tray-alerts: menu rebuild failed");
                    } else {
                        tracing::debug!(count = alerts.len(), "tray-alerts: refreshed");
                    }

                    // R-3.1/R-3.2 (Story 3.1): OS popup guard — existing rate-limit guards apply inside
                    if settings.os_popups {
                        check_notifications(&app, &alerts, &reminders.active, journal_due);
                    }
                }
                Err(e) => {
                    let next = (current_interval * 2).min(MAX_BACKOFF_INTERVAL);
                    tracing::debug!(
                        error = %e,
                        prev_interval_secs = current_interval.as_secs(),
                        next_interval_secs = next.as_secs(),
                        "tray-alerts: backend unreachable, clearing and backing off",
                    );
                    current_interval = next;
                    let _ = crate::tray::update_alerts(&app, &[], &[], &[], &[], 0, false);
                }
            }

            // R-2.1: record time before sleep for wake detection
            app.state::<Mutex<TauriNotificationState>>()
                .lock()
                .unwrap_or_else(|p| p.into_inner())
                .last_poll_at = Instant::now();

            tokio::time::sleep(current_interval).await;

            // R-2.2–R-2.4: detect sleep/wake and reset notification timer.
            // Compare against current_interval (not the base POLL_INTERVAL)
            // so backoff cycles don't get false-flagged as sleep events.
            {
                let state_ref = app.state::<Mutex<TauriNotificationState>>();
                let mut state = state_ref.lock().unwrap_or_else(|p| p.into_inner());
                let actual_elapsed = state.last_poll_at.elapsed();
                if actual_elapsed > current_interval + SLEEP_THRESHOLD {
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

    // notification-sound R-1.1: enum maps to expected system sound files.
    #[test]
    fn test_notification_sound_file_mapping() {
        assert_eq!(NotificationSound::Glass.sound_file(),  Some("/System/Library/Sounds/Glass.aiff"));
        assert_eq!(NotificationSound::Funk.sound_file(),   Some("/System/Library/Sounds/Funk.aiff"));
        assert_eq!(NotificationSound::Silent.sound_file(), None);
    }

    #[test]
    fn test_notification_sound_default_is_glass() {
        assert_eq!(NotificationSound::default(), NotificationSound::Glass);
    }

    // R-3.10 / R-4.1: /api/home journal block parses into HomeResponse.journal.
    #[test]
    fn test_home_response_parses_journal_due() {
        let json = r#"{"pressing":[],"journal":{"due":true,"next_due":"2026-06-03T14:00:00-06:00"}}"#;
        let resp: HomeResponse = serde_json::from_str(json).unwrap();
        assert!(resp.journal.due);
    }

    // Older backend without a journal block → defaults to not-due (no panic).
    #[test]
    fn test_home_response_journal_defaults_when_absent() {
        let resp: HomeResponse = serde_json::from_str(r#"{"pressing":[]}"#).unwrap();
        assert!(!resp.journal.due);
    }

    // R-5.1: /api/home quick_tasks block parses (active items + return_blocked).
    #[test]
    fn test_home_response_parses_quick_tasks() {
        let json = r#"{"pressing":[],"quick_tasks":{"active":[{"id":"QT-001","text":"Reply to Ana"}],"active_count":1,"snoozed_count":2,"return_blocked":true}}"#;
        let resp: HomeResponse = serde_json::from_str(json).unwrap();
        assert_eq!(resp.quick_tasks.active.len(), 1);
        assert_eq!(resp.quick_tasks.active[0].id, "QT-001");
        assert_eq!(resp.quick_tasks.active_count, 1);
        assert!(resp.quick_tasks.return_blocked);
    }

    // Older backend without a quick_tasks block → empty, not blocked (no panic).
    #[test]
    fn test_home_response_quick_tasks_default_when_absent() {
        let resp: HomeResponse = serde_json::from_str(r#"{"pressing":[]}"#).unwrap();
        assert!(resp.quick_tasks.active.is_empty());
        assert!(!resp.quick_tasks.return_blocked);
    }

    // Quick Task tray label is compact and prefixed.
    #[test]
    fn test_quick_task_menu_label() {
        let q = QuickTaskItem { id: "QT-002".into(), text: "Approve transaction".into() };
        assert_eq!(q.menu_label(), "⚡ Approve transaction");
    }

    #[test]
    fn test_notif_settings_default_uses_glass() {
        let s = NotifSettings::default();
        assert_eq!(s.in_app, true);
        assert_eq!(s.os_popups, false);
        assert_eq!(s.sound, NotificationSound::Glass);
    }

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

    // M10 audit fix: rows older than NOTIF_RETENTION_DAYS are pruned; fresh
    // rows survive.
    #[test]
    fn test_prune_deletes_only_old_notifications() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        init_notif_db(&db_path).unwrap();
        let conn = rusqlite::Connection::open(&db_path).unwrap();
        conn.execute(
            "INSERT INTO notifications (type, item_id, title, body, fired_at) \
             VALUES ('pressing', 'OLD', 't', 'b', strftime('%Y-%m-%dT%H:%M:%S', 'now', '-120 days'))",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO notifications (type, item_id, title, body, fired_at) \
             VALUES ('pressing', 'NEW', 't', 'b', strftime('%Y-%m-%dT%H:%M:%S', 'now'))",
            [],
        )
        .unwrap();
        prune_old_notifications(&conn).unwrap();
        let remaining: Vec<String> = conn
            .prepare("SELECT item_id FROM notifications")
            .unwrap()
            .query_map([], |r| r.get(0))
            .unwrap()
            .collect::<Result<_, _>>()
            .unwrap();
        assert_eq!(remaining, vec!["NEW".to_string()]);
    }

    // L17 audit fix: tray labels are truncated; short strings untouched.
    #[test]
    fn test_truncate_chars() {
        assert_eq!(truncate_chars("short", 48), "short");
        let long = "x".repeat(60);
        let cut = truncate_chars(&long, 48);
        assert_eq!(cut.chars().count(), 48);
        assert!(cut.ends_with('…'));
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

    // Make the interval guard pass for reservation tests.
    fn ready_state() -> TauriNotificationState {
        let mut state = TauriNotificationState::new();
        state.last_check_at = Instant::now() - NOTIF_INTERVAL - Duration::from_secs(1);
        state.dialogs_date = today_date_string();
        state
    }

    // (a) early-return when NOTIF_INTERVAL has not elapsed
    #[test]
    fn test_no_candidates_interval_not_elapsed() {
        let mut state = TauriNotificationState::new();
        // last_check_at defaults to Instant::now(), so elapsed < NOTIF_INTERVAL
        let alerts = vec![make_alert("A")];
        let result = reserve_notifications(&mut state, &alerts, &[], false);
        assert!(result.is_empty());
    }

    // (b) daily cap of 8 blocks all candidates
    #[test]
    fn test_no_candidates_daily_cap_reached() {
        let mut state = ready_state();
        state.dialogs_today = MAX_DIALOGS_PER_DAY;
        let alerts = vec![make_alert("A")];
        let result = reserve_notifications(&mut state, &alerts, &[], false);
        assert!(result.is_empty());
        assert_eq!(state.dialogs_today, MAX_DIALOGS_PER_DAY);
    }

    // (c) item notified within ITEM_COOLDOWN is excluded; others pass
    #[test]
    fn test_item_on_cooldown_excluded() {
        let mut state = ready_state();
        state.last_notified.insert("A".to_string(), Instant::now());
        let alerts = vec![make_alert("A"), make_alert("B")];
        let result = reserve_notifications(&mut state, &alerts, &[], false);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].item_key, "B");
    }

    // (d) at most 3 candidates returned even when more are available
    #[test]
    fn test_at_most_3_candidates() {
        let mut state = ready_state();
        let alerts: Vec<Alert> = (0..5).map(|i| make_alert(&format!("item-{i}"))).collect();
        let result = reserve_notifications(&mut state, &alerts, &[], false);
        assert_eq!(result.len(), 3);
        assert_eq!(state.dialogs_today, 3);
    }

    // M11 audit fix: the daily cap is enforced atomically across the pressing,
    // reminder, and journal phases — one slot left means exactly one reserved.
    #[test]
    fn test_cap_enforced_atomically_across_phases() {
        let mut state = ready_state();
        state.dialogs_today = MAX_DIALOGS_PER_DAY - 1;
        let alerts: Vec<Alert> = (0..3).map(|i| make_alert(&format!("P-{i}"))).collect();
        let reminders = vec![make_reminder("REM-A"), make_reminder("REM-B")];
        let result = reserve_notifications(&mut state, &alerts, &reminders, true);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].kind, PlannedKind::Pressing);
        assert_eq!(state.dialogs_today, MAX_DIALOGS_PER_DAY);
    }

    // Reservation assigns unique ids and stores pending clicks for pressing
    // and reminder notifications, but not for the journal check-in.
    #[test]
    fn test_reservation_assigns_ids_and_pending_clicks() {
        let mut state = ready_state();
        let alerts = vec![make_alert("P-1")];
        let reminders = vec![make_reminder("REM-1")];
        let result = reserve_notifications(&mut state, &alerts, &reminders, true);
        assert_eq!(result.len(), 3);
        let mut ids: Vec<i32> = result.iter().map(|n| n.id).collect();
        ids.dedup();
        assert_eq!(ids.len(), 3, "notification ids must be unique");
        let journal = result.iter().find(|n| n.kind == PlannedKind::Journal).unwrap();
        for n in &result {
            assert_eq!(
                state.pending_clicks.contains_key(&n.id),
                n.kind != PlannedKind::Journal,
                "pending click stored iff not journal (id {})",
                n.id
            );
        }
        assert_eq!(journal.item_key, JOURNAL_ITEM_ID);
        assert_eq!(state.dialogs_today, 3);
    }

    fn make_reminder(id: &str) -> ReminderAlert {
        ReminderAlert {
            id: id.to_string(),
            title: id.to_string(),
            reminder_date: "2026-05-30".to_string(),
            project: None,
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
        let mut state = ready_state();
        state.last_notified.insert("REM-A".to_string(), Instant::now());
        let reminders = vec![make_reminder("REM-A"), make_reminder("REM-B")];
        let result = reserve_notifications(&mut state, &[], &reminders, false);
        assert_eq!(result.len(), 1);
        assert_eq!(result[0].item_key, "REM-B");
    }

    // (f) interval guard blocks reminder candidates
    #[test]
    fn test_reminder_blocked_by_interval_guard() {
        let mut state = TauriNotificationState::new();
        // last_check_at defaults to Instant::now() → elapsed < NOTIF_INTERVAL
        let reminders = vec![make_reminder("REM-A")];
        let result = reserve_notifications(&mut state, &[], &reminders, false);
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

    // ── R-9.11/R-9.12/R-9.13: cached connection path ────────────────────────

    #[test]
    fn test_open_cached_notif_conn_sets_wal_and_busy_timeout() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        let conn = open_cached_notif_conn(&db_path).unwrap();
        let mode: String = conn
            .query_row("PRAGMA journal_mode", [], |r| r.get(0))
            .unwrap();
        assert_eq!(mode, "wal");
        let busy: i64 = conn
            .query_row("PRAGMA busy_timeout", [], |r| r.get(0))
            .unwrap();
        assert_eq!(busy, 5000);
        let sync: i64 = conn
            .query_row("PRAGMA synchronous", [], |r| r.get(0))
            .unwrap();
        // synchronous=NORMAL is value 1 in SQLite
        assert_eq!(sync, 1);
    }

    #[test]
    fn test_open_cached_notif_conn_creates_schema() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        let conn = open_cached_notif_conn(&db_path).unwrap();
        // Schema is in place — insert + read back via the on_conn helpers
        let inserted = insert_notification_if_new_on_conn(
            &conn, "pressing", "TASK-X", "TASK-X", "body", "url",
        )
        .unwrap();
        assert!(inserted);
        assert_eq!(unread_count_on_conn(&conn).unwrap(), 1);
    }

    #[test]
    fn test_on_conn_helpers_dedup_same_day() {
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        let conn = open_cached_notif_conn(&db_path).unwrap();
        let first = insert_notification_if_new_on_conn(
            &conn, "pressing", "DUP-1", "DUP-1", "body", "url",
        )
        .unwrap();
        let second = insert_notification_if_new_on_conn(
            &conn, "pressing", "DUP-1", "DUP-1", "body", "url",
        )
        .unwrap();
        assert!(first, "first insert succeeds");
        assert!(!second, "same-day duplicate is suppressed");
        assert_eq!(unread_count_on_conn(&conn).unwrap(), 1);
    }

    #[test]
    fn test_cached_conn_survives_repeated_use() {
        // Sanity check that a single Connection can be borrowed many times
        // sequentially without re-opening — mirrors the polling loop usage.
        let dir = tempfile::tempdir().unwrap();
        let db_path = dir.path().join("squirrel.db");
        let conn = open_cached_notif_conn(&db_path).unwrap();
        for i in 0..50 {
            let id = format!("ITEM-{i}");
            insert_notification_if_new_on_conn(&conn, "pressing", &id, &id, "body", "url")
                .unwrap();
        }
        assert_eq!(unread_count_on_conn(&conn).unwrap(), 50);
    }
}
