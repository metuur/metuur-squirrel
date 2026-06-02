//! Tray icon and menu. Implements R-1.2, R-2.1, R-2.2 (icon state machine
//! kept from Phase 1) and Phase 2 R-4.1 ("Open Web UI" item).
//!
//! Phase 2 supersedes Phase 1 R-2.5: the original menu had Background
//! Watcher / Settings / View Logs placeholders. With the real backend in
//! place those vestigial controls are gone; the menu is now action-only:
//!   Open Squirrel
//!   Open Web UI
//!   ─────────
//!   PRESSING NOW            (disabled header)
//!   <alert 1>               (dynamic, links to /notes/<id>)
//!   <alert 2>
//!   <alert 3>
//!   ─────────
//!   Quit Squirrel
//!
//! Alerts are populated by `tray_alerts::start_polling`. When the backend is
//! offline / has no pressing items, the section degrades to a single
//! disabled "No pressing items" entry.

use tauri::image::Image;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_opener::OpenerExt;

use crate::tray_alerts::{Alert, ReminderAlert};

pub const TRAY_ID: &str = "main";

/// Phase 2 (LLD D6, EARS R-1.1, R-4.3): the popup, the tray menu, and the
/// vite proxy all agree on this single backend origin.
pub const BACKEND_ORIGIN: &str = "http://127.0.0.1:3939";

/// Menu item IDs. The alert items use the `ALERT_PREFIX` so the menu-event
/// handler can detect them and extract the task id.
pub mod ids {
    pub const OPEN: &str = "open";
    pub const OPEN_WEB_UI: &str = "open_web_ui";
    pub const QUIT: &str = "quit";
    pub const ALERT_PREFIX: &str = "alert:";
    pub const PRESSING_HEADER: &str = "pressing_header";
    pub const NO_PRESSING: &str = "no_pressing";
    pub const RADAR_HEADER: &str = "radar_header";
    pub const REMINDER_HEADER: &str = "reminder_header";
    pub const REMINDER_PREFIX: &str = "reminder:";
    pub const VIEW_NOTIFICATIONS: &str = "view_notifications";
    /// Shown only when the backend_supervisor refused adoption (Runtime Trust
    /// Handshake, R-6.1). Opens the dashboard and re-emits the refusal cause so
    /// the blocking banner renders with recovery instructions.
    pub const WHY: &str = "why_blocked";
    /// Replaces NO_PRESSING when the backend_supervisor reports the
    /// backend as degraded (Failed mode or 3+ consecutive health-check
    /// failures), so the user sees the actual failure instead of the
    /// misleading "No pressing items" empty state.
    pub const BACKEND_ERROR: &str = "backend_error";
}

#[derive(Copy, Clone, Debug, Eq, PartialEq)]
#[allow(dead_code)] // Notification/Processing/Error retained for Phase 3+
pub enum IconState {
    Normal,
    Notification,
    Processing,
    Error,
}

const ICON_NORMAL: &[u8] = include_bytes!("../icons/tray/normal@2x.png");
const ICON_NOTIFICATION: &[u8] = include_bytes!("../icons/tray/notification@2x.png");
const ICON_PROCESSING: &[u8] = include_bytes!("../icons/tray/processing@2x.png");
const ICON_ERROR: &[u8] = include_bytes!("../icons/tray/error@2x.png");

pub fn icon_bytes(state: IconState) -> &'static [u8] {
    match state {
        IconState::Normal => ICON_NORMAL,
        IconState::Notification => ICON_NOTIFICATION,
        IconState::Processing => ICON_PROCESSING,
        IconState::Error => ICON_ERROR,
    }
}

fn load_image(state: IconState) -> tauri::Result<Image<'static>> {
    Image::from_bytes(icon_bytes(state))
}

/// Build the menu from current alert state. Called from both `setup` (empty
/// alerts on startup) and `update_alerts` (after a poll).
fn build_menu<R: Runtime>(
    app: &AppHandle<R>,
    alerts: &[Alert],
    approaching: &[ReminderAlert],
    active: &[ReminderAlert],
    unread_count: u32,
) -> tauri::Result<Menu<R>> {
    let open_item = MenuItem::with_id(app, ids::OPEN, "Open Squirrel", true, None::<&str>)?;
    let open_web_ui_item =
        MenuItem::with_id(app, ids::OPEN_WEB_UI, "Open Web UI", true, None::<&str>)?;
    let sep_top = PredefinedMenuItem::separator(app)?;
    let pressing_header = MenuItem::with_id(
        app,
        ids::PRESSING_HEADER,
        "PRESSING NOW",
        false, // disabled — used as a section label
        None::<&str>,
    )?;
    let sep_bot = PredefinedMenuItem::separator(app)?;
    let quit_item = MenuItem::with_id(app, ids::QUIT, "Quit Squirrel", true, None::<&str>)?;

    // R-6.1: when adoption was refused, surface a "Why?" item near the top that
    // opens the dashboard with the refusal banner.
    let why_item = match crate::backend_supervisor::refused_adoption_cause(app) {
        Some(_) => Some(MenuItem::with_id(
            app,
            ids::WHY,
            "Why is Squirrel blocked?",
            true,
            None::<&str>,
        )?),
        None => None,
    };

    let mut items: Vec<&dyn tauri::menu::IsMenuItem<R>> = vec![
        &open_item,
        &open_web_ui_item,
        &sep_top,
        &pressing_header,
    ];
    if let Some(ref w) = why_item {
        items.insert(2, w); // between Open Web UI and the top separator
    }

    let alert_items: Vec<MenuItem<R>> = alerts
        .iter()
        .map(|a| {
            let id = format!("{}{}", ids::ALERT_PREFIX, a.id);
            MenuItem::with_id(app, id, a.menu_label(), true, None::<&str>)
        })
        .collect::<tauri::Result<Vec<_>>>()?;

    // When the backend is reachable, an empty alerts list means "you
    // really have nothing pressing". When the backend supervisor reports
    // degraded, an empty list is misleading — show the actual reason so
    // the user has somewhere to look (~/.squirrel/squirrel.log).
    let no_pressing = if alert_items.is_empty() {
        let (id, label) = if crate::backend_supervisor::is_degraded(app) {
            (ids::BACKEND_ERROR, "Backend unavailable — see ~/.squirrel/squirrel.log")
        } else {
            (ids::NO_PRESSING, "No pressing items")
        };
        Some(MenuItem::with_id(app, id, label, false, None::<&str>)?)
    } else {
        None
    };

    if let Some(np) = no_pressing.as_ref() {
        items.push(np);
    } else {
        for ai in alert_items.iter() {
            items.push(ai);
        }
    }

    // "On your radar" section (approaching reminders) — R-4.1
    let sep_radar = PredefinedMenuItem::separator(app)?;
    let radar_header = MenuItem::with_id(app, ids::RADAR_HEADER, "On your radar", false, None::<&str>)?;
    let radar_items: Vec<MenuItem<R>> = approaching
        .iter()
        .map(|r| {
            let id = format!("{}{}", ids::REMINDER_PREFIX, r.id);
            MenuItem::with_id(app, id, r.menu_label(), true, None::<&str>)
        })
        .collect::<tauri::Result<Vec<_>>>()?;

    // "Reminder due" section (active reminders) — R-4.2
    let sep_reminder = PredefinedMenuItem::separator(app)?;
    let reminder_header = MenuItem::with_id(app, ids::REMINDER_HEADER, "Reminder due", false, None::<&str>)?;
    let reminder_items: Vec<MenuItem<R>> = active
        .iter()
        .map(|r| {
            let id = format!("{}{}", ids::REMINDER_PREFIX, r.id);
            MenuItem::with_id(app, id, r.menu_label(), true, None::<&str>)
        })
        .collect::<tauri::Result<Vec<_>>>()?;

    if !approaching.is_empty() {
        items.push(&sep_radar);
        items.push(&radar_header);
        for ri in radar_items.iter() {
            items.push(ri);
        }
    }

    if !active.is_empty() {
        items.push(&sep_reminder);
        items.push(&reminder_header);
        for ri in reminder_items.iter() {
            items.push(ri);
        }
    }

    // "Notifications (N)" item — visible only when unread_count > 0 (R-8.1, R-8.2, R-8.3)
    let notif_item_opt: Option<MenuItem<R>> = if unread_count > 0 {
        Some(MenuItem::with_id(
            app,
            ids::VIEW_NOTIFICATIONS,
            format!("Notifications ({})", unread_count),
            true,
            None::<&str>,
        )?)
    } else {
        None
    };
    if let Some(ref ni) = notif_item_opt {
        items.push(ni);
    }

    items.push(&sep_bot);
    items.push(&quit_item);

    Menu::with_items(app, &items)
}

pub fn setup<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    let menu = build_menu(app, &[], &[], &[], 0)?;

    let _tray = TrayIconBuilder::with_id(TRAY_ID)
        .icon(load_image(IconState::Normal)?)
        .icon_as_template(true) // macOS template image — system tints per appearance
        .menu(&menu)
        .on_menu_event(|app, event| {
            let id = event.id().as_ref();
            match id {
                ids::OPEN => show_main_window(app),
                ids::OPEN_WEB_UI => open_url(app, BACKEND_ORIGIN),
                ids::QUIT => {
                    tracing::info!("tray: quit requested");
                    app.exit(0);
                }
                ids::VIEW_NOTIFICATIONS => show_main_window(app),
                ids::WHY => {
                    // R-6.1: open the dashboard, then re-emit the refusal cause
                    // so the banner renders even if the React listener wasn't
                    // mounted when the original event fired at startup.
                    show_main_window(app);
                    crate::backend_supervisor::notify_refusal(app);
                }
                ids::PRESSING_HEADER
                | ids::NO_PRESSING
                | ids::BACKEND_ERROR
                | ids::RADAR_HEADER
                | ids::REMINDER_HEADER => {
                    // Disabled items; menu-event still fires on some platforms.
                }
                other if other.starts_with(ids::ALERT_PREFIX) => {
                    let task_id = &other[ids::ALERT_PREFIX.len()..];
                    let url = format!("{}/notes/{}", BACKEND_ORIGIN, task_id);
                    open_url(app, &url);
                }
                other if other.starts_with(ids::REMINDER_PREFIX) => {
                    let reminder_id = &other[ids::REMINDER_PREFIX.len()..];
                    let url = format!("{}/notes/{}", BACKEND_ORIGIN, reminder_id);
                    open_url(app, &url);
                }
                other => {
                    tracing::info!(menu_item = other, "tray menu clicked (unhandled)");
                }
            }
        })
        .build(app)?;

    tracing::info!("tray icon installed");
    Ok(())
}

/// Rebuild the menu with a fresh set of alert items. Called by the
/// `tray_alerts` background poller every 30 seconds.
pub fn update_alerts<R: Runtime>(
    app: &AppHandle<R>,
    alerts: &[Alert],
    approaching: &[ReminderAlert],
    active: &[ReminderAlert],
    unread_count: u32,
) -> tauri::Result<()> {
    let menu = build_menu(app, alerts, approaching, active, unread_count)?;
    if let Some(tray) = app.tray_by_id(TRAY_ID) {
        tray.set_menu(Some(menu))?;
    }
    Ok(())
}

fn open_url<R: Runtime>(app: &AppHandle<R>, url: &str) {
    if let Err(e) = app.opener().open_url(url, None::<&str>) {
        tracing::warn!(error = %e, url, "tray: failed to open url");
    } else {
        tracing::info!(url, "tray: opened url");
    }
}

/// Switch the tray icon to a different state. Story 2.4 exposes this through
/// a Tauri command so the dashboard can drive it; here it lives as a plain
/// helper so unit tests can verify the lookup without spinning up Tauri.
#[allow(dead_code)] // first caller arrives in Story 2.4
pub fn set_state<R: Runtime>(app: &AppHandle<R>, state: IconState) -> tauri::Result<()> {
    if let Some(tray) = app.tray_by_id(TRAY_ID) {
        tray.set_icon(Some(load_image(state)?))?;
        tracing::info!(?state, "tray icon state changed");
    }
    Ok(())
}

/// Bring the main window back from a hidden state, focus it, and clear the
/// tray's notification badge. Shared between the "Open Squirrel" menu item
/// and the notification-click handler.
pub fn show_main_window<R: Runtime>(app: &AppHandle<R>) {
    if let Some(window) = app.get_webview_window("main") {
        // Switch to Regular policy before show() so the app is already in Cmd+Tab
        // by the time the window becomes interactive.
        #[cfg(target_os = "macos")]
        if let Err(e) = app.set_activation_policy(tauri::ActivationPolicy::Regular) {
            tracing::warn!(error = %e, "failed to set activation policy to Regular");
        }
        // macOS resets the dock icon when activation policy changes; re-apply.
        #[cfg(target_os = "macos")]
        crate::set_dock_icon();
        if let Err(e) = window.show() {
            tracing::warn!(error = %e, "failed to show main window");
        }
        // Reset window level to normal — windows created while the app is in
        // Accessory mode may receive a floating NSWindowLevel on macOS. Switching
        // the activation policy to Regular does not retroactively lower it, so we
        // must do it explicitly each time the window is shown.
        if let Err(e) = window.set_always_on_top(false) {
            tracing::warn!(error = %e, "failed to reset window level on main window");
        }
        if let Err(e) = window.set_focus() {
            tracing::warn!(error = %e, "failed to focus main window");
        }
        if let Err(e) = set_state(app, IconState::Normal) {
            tracing::warn!(error = %e, "failed to reset tray icon");
        }
        tracing::info!("main window shown via tray/open");
    } else {
        tracing::warn!("show_main_window called but no 'main' window exists");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_icon_state_has_embedded_bytes() {
        for s in [
            IconState::Normal,
            IconState::Notification,
            IconState::Processing,
            IconState::Error,
        ] {
            let bytes = icon_bytes(s);
            assert!(!bytes.is_empty(), "{s:?} bytes must be non-empty");
            assert_eq!(
                &bytes[..8],
                &[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A],
                "{s:?} must be a PNG"
            );
        }
    }

    #[test]
    fn each_state_has_distinct_bytes() {
        let states = [
            IconState::Normal,
            IconState::Notification,
            IconState::Processing,
            IconState::Error,
        ];
        for i in 0..states.len() {
            for j in (i + 1)..states.len() {
                assert_ne!(
                    icon_bytes(states[i]),
                    icon_bytes(states[j]),
                    "{:?} and {:?} are byte-identical",
                    states[i],
                    states[j]
                );
            }
        }
    }

    #[test]
    fn alert_label_overdue() {
        let a = Alert {
            id: "FOO-001".into(),
            title: "FOO-001 — Something".into(),
            is_overdue: true,
            hours_left: None,
            days_overdue: Some(43),
            urgency_label: None,
        };
        assert_eq!(a.menu_label(), "43d overdue · FOO-001");
    }

    #[test]
    fn alert_label_hours_left() {
        let a = Alert {
            id: "BAR-002".into(),
            title: "BAR-002 — Soon".into(),
            is_overdue: false,
            hours_left: Some(5.4),
            days_overdue: None,
            urgency_label: None,
        };
        assert_eq!(a.menu_label(), "5h left · BAR-002");
    }

    // ── Story 8.1: reminder click handler ────────────────────────────────────

    #[test]
    fn reminder_prefix_click_derives_correct_url() {
        let item_id = format!("{}VISA-001", ids::REMINDER_PREFIX);
        let reminder_id = &item_id[ids::REMINDER_PREFIX.len()..];
        let url = format!("{}/notes/{}", BACKEND_ORIGIN, reminder_id);
        assert_eq!(url, "http://127.0.0.1:3939/notes/VISA-001");
    }

    // ── Story 8.2: VIEW_NOTIFICATIONS constant and label format ──────────────

    #[test]
    fn view_notifications_id_constant() {
        assert_eq!(ids::VIEW_NOTIFICATIONS, "view_notifications");
    }

    #[test]
    fn view_notifications_label_format() {
        assert_eq!(format!("Notifications ({})", 3u32), "Notifications (3)");
        assert_eq!(format!("Notifications ({})", 12u32), "Notifications (12)");
    }

    #[test]
    fn reminder_item_url_matches_note_pattern() {
        use crate::tray_alerts::ReminderAlert;
        let r = ReminderAlert {
            id: "VISA-001".into(),
            title: "Pay visa".into(),
            reminder_date: "2026-05-30".into(),
            project: None,
            item_url: format!("{}/notes/{}", BACKEND_ORIGIN, "VISA-001"),
        };
        assert_eq!(r.item_url, "http://127.0.0.1:3939/notes/VISA-001");
        // Confirm click handler would reconstruct the same URL
        let item_id = format!("{}{}", ids::REMINDER_PREFIX, r.id);
        let extracted_id = &item_id[ids::REMINDER_PREFIX.len()..];
        assert_eq!(
            format!("{}/notes/{}", BACKEND_ORIGIN, extracted_id),
            r.item_url
        );
    }
}
