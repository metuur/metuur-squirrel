mod deep_link;
mod logging;
mod tray;
mod tray_alerts;

use std::sync::Mutex;
use tauri::Manager;

/// Holds the last parsed deep-link payload so the frontend can drain it on
/// mount. Needed because on cold launch Rust fires the URL event before React
/// registers its listener, causing the event to be silently dropped.
pub(crate) struct PendingDeepLink(pub(crate) Mutex<Option<deep_link::FocusProjectPayload>>);

#[tauri::command]
fn drain_pending_deep_link(
    state: tauri::State<PendingDeepLink>,
) -> Option<deep_link::FocusProjectPayload> {
    state.0.lock().unwrap().take()
}

// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // R-1.1: create ~/.squirrel/ before anything else writes inside it.
    logging::ensure_squirrel_dir().expect("create ~/.squirrel/");
    let _log_guard = logging::init();
    tracing::info!(
        version = env!("CARGO_PKG_VERSION"),
        "squirrel starting"
    );

    let mut builder = tauri::Builder::default();

    #[cfg(desktop)]
    {
        builder = builder
            .plugin(tauri_plugin_single_instance::init(|_app, _args, _cwd| {
                // Wired in Story 1.1: focus the existing main window when a second
                // instance launches. For Story 0.2 the plugin is registered only to
                // prove it compiles and links.
            }))
            .plugin(tauri_plugin_autostart::init(
                tauri_plugin_autostart::MacosLauncher::LaunchAgent,
                None,
            ))
            .plugin(tauri_plugin_global_shortcut::Builder::new().build());
    }

    builder
        .manage(PendingDeepLink(Mutex::new(None)))
        .manage(Mutex::new(tray_alerts::TauriNotificationState::new()))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_deep_link::init())
        .setup(|app| {
            // R-1.7 / LLD D9: lock macOS activation policy to Accessory so the app
            // never gets a Dock icon, never gets an app menu in the top menu bar,
            // and never appears in Cmd+Tab — regardless of window visibility.
            // Runtime equivalent of Info.plist LSUIElement=true.
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Accessory);

            #[cfg(desktop)]
            tray::setup(app.handle())?;

            // Phase 2: start the tray-alerts background poller. Every 30s
            // it fetches /api/home and rebuilds the tray's PRESSING NOW
            // section. Backend offline → menu shows "No pressing items".
            #[cfg(desktop)]
            tray_alerts::start_polling(app.handle().clone());

            // Register Cmd+Shift+S global shortcut so the user can summon Squirrel
            // from any app. Registration failure (e.g. hotkey held by another process)
            // is a warning, not a crash — the app must stay alive regardless.
            #[cfg(desktop)]
            {
                use tauri_plugin_global_shortcut::GlobalShortcutExt;
                if let Err(e) = app.handle().global_shortcut().on_shortcut(
                    "CmdOrCtrl+Shift+S",
                    |app, _shortcut, event| {
                        use tauri_plugin_global_shortcut::ShortcutState;
                        if event.state == ShortcutState::Pressed {
                            tray::show_main_window(app);
                        }
                    },
                ) {
                    tracing::warn!(
                        error = %e,
                        "global shortcut Cmd+Shift+S could not be registered (held by another app?)"
                    );
                } else {
                    tracing::info!("global shortcut Cmd+Shift+S registered");
                }
            }

            // R-4.1: wire deep-link URL handler (story 3.3).
            #[cfg(desktop)]
            {
                use tauri_plugin_deep_link::DeepLinkExt;
                let handle = app.handle().clone();
                app.handle().deep_link().on_open_url(move |event| {
                    for url in event.urls() {
                        deep_link::handle(&handle, &url);
                    }
                });
            }

            Ok(())
        })
        // R-1.4 / Story 1.2: closing the main window must hide it, not quit
        // the app. The tray menu's Quit item is the only normal exit path.
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "main" {
                    api.prevent_close();
                    if let Err(e) = window.hide() {
                        tracing::warn!(error = %e, "failed to hide main window");
                    } else {
                        // Revert to Accessory so the app disappears from Cmd+Tab
                        // and the Dock while the window is hidden.
                        #[cfg(target_os = "macos")]
                        if let Err(e) = window
                            .app_handle()
                            .set_activation_policy(tauri::ActivationPolicy::Accessory)
                        {
                            tracing::warn!(
                                error = %e,
                                "failed to set activation policy to Accessory on hide"
                            );
                        }
                        tracing::info!("main window close intercepted; hidden");
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![greet, drain_pending_deep_link])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
