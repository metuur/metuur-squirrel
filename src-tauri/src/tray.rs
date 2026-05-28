//! Tray icon and menu. Implements R-1.2, R-2.1, R-2.2, R-2.5.
//!
//! The four state PNGs are embedded at compile time via `include_bytes!` so the
//! tray works without runtime path resolution and without an extra Tauri
//! resource-dir setup step. Production loads `@2x.png` (32x32) and lets macOS
//! downscale for the 1x menu bar; using the larger asset keeps the silhouette
//! crisp at Retina densities.

use tauri::image::Image;
use tauri::menu::{CheckMenuItem, Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Runtime};

pub const TRAY_ID: &str = "main";

/// Menu item IDs. Kept here so menu-event handlers can match without stringly-
/// typed magic scattered across modules.
pub mod ids {
    pub const OPEN: &str = "open";
    pub const WATCHER: &str = "watcher";
    pub const SETTINGS: &str = "settings";
    pub const LOGS: &str = "logs";
    pub const QUIT: &str = "quit";
}

#[derive(Copy, Clone, Debug, Eq, PartialEq)]
#[allow(dead_code)] // Notification/Processing/Error are exercised by Stories 2.4-2.9, 3.2, 4.5
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

pub fn setup<R: Runtime>(app: &AppHandle<R>) -> tauri::Result<()> {
    let open_item = MenuItem::with_id(app, ids::OPEN, "Open Squirrel", true, None::<&str>)?;
    let watcher_item = CheckMenuItem::with_id(
        app,
        ids::WATCHER,
        "Background Watcher",
        true,
        true, // checked by default — R-3.5 defaults watcher On
        None::<&str>,
    )?;
    // Settings is enabled but its handler is intentionally a no-op in Phase 1
    // (R-2.10). Keeping it enabled — rather than disabled/grayed — matches the
    // story's verify ("click does nothing, no crash").
    let settings_item = MenuItem::with_id(app, ids::SETTINGS, "Settings", true, None::<&str>)?;
    let logs_item = MenuItem::with_id(app, ids::LOGS, "View Logs", true, None::<&str>)?;
    let quit_item = MenuItem::with_id(app, ids::QUIT, "Quit Squirrel", true, None::<&str>)?;

    // Order matters: R-2.5 fixes the menu item sequence.
    let menu = Menu::with_items(
        app,
        &[
            &open_item,
            &watcher_item,
            &settings_item,
            &logs_item,
            &quit_item,
        ],
    )?;

    let _tray = TrayIconBuilder::with_id(TRAY_ID)
        .icon(load_image(IconState::Normal)?)
        .icon_as_template(true) // macOS template image — system tints per appearance
        .menu(&menu)
        .on_menu_event(|app, event| match event.id().as_ref() {
            ids::QUIT => {
                tracing::info!("tray: quit requested");
                app.exit(0);
            }
            other => {
                // Other handlers land in later stories (1.4 quit polish, 2.5
                // open, 2.6 logs, 2.7-2.9 watcher toggle). For Story 2.2 they
                // just log so we can see clicks in the log file.
                tracing::info!(menu_item = other, "tray menu clicked (handler pending)");
            }
        })
        .build(app)?;

    tracing::info!("tray icon installed");
    Ok(())
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
            // PNG magic: 89 50 4E 47 0D 0A 1A 0A
            assert_eq!(
                &bytes[..8],
                &[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A],
                "{s:?} must be a PNG"
            );
        }
    }

    #[test]
    fn each_state_has_distinct_bytes() {
        // Mirror of the integration test, but checked against the embedded
        // bytes — guarantees we did not accidentally include the same file
        // four times.
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
}
