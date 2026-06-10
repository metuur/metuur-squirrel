fn main() {
    // The backend port/origin are baked in via `option_env!` (see
    // backend_supervisor::BACKEND_PORT, tray::BACKEND_ORIGIN). Declare the env
    // deps so cargo recompiles when toggling between the prod (:3939) and dev
    // (:3940) builds instead of embedding a stale port.
    println!("cargo:rerun-if-env-changed=SQUIRREL_BACKEND_PORT");
    println!("cargo:rerun-if-env-changed=SQUIRREL_BACKEND_ORIGIN");
    tauri_build::build()
}
