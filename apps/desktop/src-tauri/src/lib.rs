mod logging;
mod tray;
mod tray_alerts;

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
            ));
    }

    builder
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_store::Builder::default().build())
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
                        tracing::info!("main window close intercepted; hidden");
                    }
                }
            }
        })
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
