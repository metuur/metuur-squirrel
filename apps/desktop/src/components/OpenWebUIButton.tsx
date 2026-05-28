// Phase 2 OpenWebUIButton — secondary, ghost-style button at the bottom
// of the popup. Click launches the v0.5 browser SPA via tauri-plugin-opener.
// EARS R-4.2 (in popup), R-4.3 (uses plugin-opener), R-4.4 (no pre-flight).

import { openUrl } from "@tauri-apps/plugin-opener";
import { BACKEND_ORIGIN } from "../api/client";

export function OpenWebUIButton() {
  const handleClick = () => {
    // Fire and forget. R-4.4: do not pre-check backend reachability.
    void openUrl(BACKEND_ORIGIN);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="mx-4 mt-2 mb-3 flex items-center justify-center gap-1 px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 bg-transparent border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
    >
      Open Web UI <span aria-hidden>↗</span>
    </button>
  );
}
