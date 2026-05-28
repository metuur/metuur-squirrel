// Phase 2 OpenWebUIButton — launches the browser SPA via tauri-plugin-opener.
// EARS R-4.2 (in popup), R-4.3 (uses plugin-opener),
// R-4.4 (no pre-flight backend check).

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
      style={{
        background: "transparent",
        border: "1px solid #334155",
        color: "#cbd5e1",
        padding: "8px 14px",
        fontSize: 12,
        cursor: "pointer",
        margin: "10px 14px",
        borderRadius: 4,
        fontFamily: "system-ui, sans-serif",
      }}
    >
      Open Web UI ↗
    </button>
  );
}
