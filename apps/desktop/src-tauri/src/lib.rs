mod backend_supervisor;
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

/// Per-launch shared-secret token (Runtime Trust Handshake, R-1.1/R-1.2). Held
/// in process memory only — never written to disk by the Tauri runtime. Passed
/// to the spawned sidecar via `--token` (R-1.3) and used to authenticate the
/// adoption probe against a backend already on port 3939 (Unit 4).
pub(crate) struct RuntimeToken(pub(crate) String);

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

/// Apply the squirrel dock icon via NSApplication.
/// Must be called from the main thread; re-apply after every activation-policy
/// change because macOS resets the dock icon when the policy switches.
#[cfg(target_os = "macos")]
pub(crate) fn set_dock_icon() {
    use objc2::{AllocAnyThread, MainThreadMarker};
    use objc2_app_kit::{NSApplication, NSImage};
    use objc2_foundation::NSData;

    const ICON: &[u8] = include_bytes!("../icons/icon.png");
    // SAFETY: caller is responsible for ensuring main-thread context.
    let mtm = unsafe { MainThreadMarker::new_unchecked() };
    let ns_app = NSApplication::sharedApplication(mtm);
    let data = NSData::with_bytes(ICON);
    if let Some(img) = NSImage::initWithData(NSImage::alloc(), &data) {
        unsafe { ns_app.setApplicationIconImage(Some(&*img)) };
    }
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
        .manage(Mutex::new(backend_supervisor::SupervisorState::new()))
        // R-1.1: mint the per-launch runtime token before any supervisor code
        // runs, so spawn_or_adopt can read it from managed state.
        .manage(RuntimeToken(backend_supervisor::mint_runtime_token()))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            // R-1.7 / LLD D9: lock macOS activation policy to Accessory so the app
            // never gets a Dock icon, never gets an app menu in the top menu bar,
            // and never appears in Cmd+Tab — regardless of window visibility.
            // Runtime equivalent of Info.plist LSUIElement=true.
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Accessory);

            // SAFETY: setup() fires on the main thread.
            #[cfg(target_os = "macos")]
            set_dock_icon();

            #[cfg(desktop)]
            tray::setup(app.handle())?;

            // R-9.1/R-9.2/R-9.6: decide backend lifecycle BEFORE the tray
            // poller starts. spawn_or_adopt picks Managed (we spawned the
            // sidecar) or Adopted (something else owns port 3939) or
            // Failed (sidecar binary unavailable and nothing on 3939).
            // Then run startup health-check + long-running health loop in
            // separate spawned tasks so the setup hook returns quickly.
            #[cfg(desktop)]
            {
                let handle = app.handle().clone();
                let (mode, child) = backend_supervisor::spawn_or_adopt(&handle);
                {
                    use std::sync::Mutex as StdMutex;
                    let state = handle.state::<StdMutex<backend_supervisor::SupervisorState>>();
                    let mut s = state.lock().unwrap();
                    s.mode = mode;
                    s.child = child;
                }
                // Detached: wait up to ~10s for /api/me to respond, flip
                // tray icon to Normal on success / Error on timeout.
                let startup_handle = handle.clone();
                tauri::async_runtime::spawn(async move {
                    backend_supervisor::wait_for_ready(&startup_handle).await;
                });
                // Detached: long-running 30s health check that recovers
                // Managed-mode backends from crash and surfaces persistent
                // failure as an Error icon.
                let loop_handle = handle.clone();
                tauri::async_runtime::spawn(async move {
                    backend_supervisor::run_health_loop(loop_handle).await;
                });
            }

            // Phase 2: start the tray-alerts background poller. Every 30s
            // it fetches /api/home and rebuilds the tray's PRESSING NOW
            // section. Backend offline → menu shows "No pressing items".
            #[cfg(desktop)]
            tray_alerts::start_polling(app.handle().clone());

            // Register Ctrl+Cmd+S global shortcut so the user can summon Squirrel
            // from any app. Registration failure (e.g. hotkey held by another process)
            // is a warning, not a crash — the app must stay alive regardless.
            #[cfg(desktop)]
            {
                use tauri_plugin_global_shortcut::GlobalShortcutExt;
                if let Err(e) = app.handle().global_shortcut().on_shortcut(
                    "Ctrl+Cmd+S",
                    |app, _shortcut, event| {
                        use tauri_plugin_global_shortcut::ShortcutState;
                        if event.state == ShortcutState::Pressed {
                            tray::show_main_window(app);
                        }
                    },
                ) {
                    tracing::warn!(
                        error = %e,
                        "global shortcut Ctrl+Cmd+S could not be registered (held by another app?)"
                    );
                } else {
                    tracing::info!("global shortcut Ctrl+Cmd+S registered");
                }

                // R-1.1 / R-1.6: Ctrl+Cmd+Q captures a Quick Task from anywhere —
                // show the window and emit so the React capture modal opens. Soft
                // failure (hotkey held elsewhere): the tray/web surfaces still work.
                use tauri::Emitter;
                if let Err(e) = app.handle().global_shortcut().on_shortcut(
                    "Ctrl+Cmd+Q",
                    |app, _shortcut, event| {
                        use tauri_plugin_global_shortcut::ShortcutState;
                        if event.state == ShortcutState::Pressed {
                            tray::show_main_window(app);
                            if let Err(e) = app.emit("quick-task-capture-open", ()) {
                                tracing::warn!(error = %e, "failed to emit quick-task-capture-open");
                            }
                        }
                    },
                ) {
                    tracing::warn!(
                        error = %e,
                        "global shortcut Ctrl+Cmd+Q could not be registered (held by another app?)"
                    );
                } else {
                    tracing::info!("global shortcut Ctrl+Cmd+Q registered");
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
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            match event {
                // External quit attempts (Cmd+Q, Dock right-click → Quit, etc.).
                // We redirect them to the same hide+Accessory behaviour as the
                // window X button so the app continues running as a tray app.
                // The only real exit path is the tray "Quit Squirrel" item,
                // which calls app.exit(0) directly and fires Exit, not this.
                tauri::RunEvent::ExitRequested { api, .. } => {
                    api.prevent_exit();
                    if let Some(window) = app.get_webview_window("main") {
                        if window.is_visible().unwrap_or(false) {
                            if let Err(e) = window.hide() {
                                tracing::warn!(error = %e, "ExitRequested: failed to hide window");
                            } else {
                                #[cfg(target_os = "macos")]
                                if let Err(e) = app
                                    .set_activation_policy(tauri::ActivationPolicy::Accessory)
                                {
                                    tracing::warn!(
                                        error = %e,
                                        "ExitRequested: failed to set Accessory policy"
                                    );
                                }
                                tracing::info!("ExitRequested intercepted; window hidden");
                            }
                        }
                    }
                }
                // R-9.3: kill the Managed backend child on a real exit (only
                // reached when app.exit(0) is called from the tray "Quit" item).
                tauri::RunEvent::Exit => {
                    backend_supervisor::shutdown(app);
                }
                _ => {}
            }
        });
}
