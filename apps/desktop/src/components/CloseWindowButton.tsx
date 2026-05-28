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
      className="inline-flex items-center gap-1 px-3 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 bg-transparent border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
    >
      <span aria-hidden>×</span>
      Close
    </button>
  );
}
