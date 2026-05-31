// Phase 2 CloseWindowButton — explicit close affordance in the popup footer.
// Calls window.hide() directly (Phase 1 R-1.4 says X button hides; this
// button matches that semantic — the app process keeps running, click the
// SQ tray icon to bring the popup back).

import { getCurrentWindow } from "@tauri-apps/api/window";

export function CloseWindowButton() {
  const handleClick = () => {
    void getCurrentWindow()
      .hide()
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
