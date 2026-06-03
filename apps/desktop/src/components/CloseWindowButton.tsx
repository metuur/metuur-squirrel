// Phase 2 CloseWindowButton — explicit close affordance in the popup footer.
// Calls window.close() so the Rust CloseRequested handler runs, which
// prevents destruction, hides the window, and switches to Accessory mode
// (removes Dock icon / Cmd+Tab entry). Same path as the native macOS X button.

import { getCurrentWindow } from "@tauri-apps/api/window";

export function CloseWindowButton() {
  const handleClick = () => {
    void getCurrentWindow()
      .close()
      .catch(() => {
        /* not in Tauri (e.g. plain browser dev) — no-op */
      });
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      title="Hide window (click the SQ tray icon to bring it back)"
      className="btn"
    >
      <svg
        width="11"
        height="11"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        aria-hidden
      >
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </svg>
      Close
    </button>
  );
}
