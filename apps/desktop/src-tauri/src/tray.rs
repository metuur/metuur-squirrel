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

use crate::tray_alerts::Alert;

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
fn build_menu<R: Runtime>(app: &AppHandle<R>, alerts: &[Alert]) -> tauri::Result<Menu<R>> {
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

    let mut items: Vec<&dyn tauri::menu::IsMenuItem<R>> = vec![
        &open_item,
        &open_web_ui_item,
        &sep_top,
        &pressing_header,
    ];

    let alert_items: Vec<MenuItem<R>> = alerts
        .iter()
        .map(|a| {
            let id = format!("{}{}", ids::ALERT_PREFIX, a.id);
            MenuItem::with_id(app, id, a.menu_label(), true, None::<&str>)
        })
        .collect::<tauri::Result<Vec<_>>>()?;

    let no_pressing = if alert_items.is_empty() {
        Some(MenuItem::with_id(
            app,
            ids::NO_PRESSING,
            "No pressing items",
            false,
            None::<&str>,
        )?)
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

    items.push(&sep_bot);
    items.push(&quit_item);

    Menu::with_items(app, &items)
}

pub fn setup<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    let menu = build_menu(app, &[])?;

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
                ids::PRESSING_HEADER | ids::NO_PRESSING => {
                    // Disabled items; menu-event still fires on some platforms.
                }
                other if other.starts_with(ids::ALERT_PREFIX) => {
                    let task_id = &other[ids::ALERT_PREFIX.len()..];
                    let url = format!("{}/notes/{}", BACKEND_ORIGIN, task_id);
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
pub fn update_alerts<R: Runtime>(app: &AppHandle<R>, alerts: &[Alert]) -> tauri::Result<()> {
    let menu = build_menu(app, alerts)?;
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
        if let Err(e) = window.show() {
            tracing::warn!(error = %e, "failed to show main window");
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
}
