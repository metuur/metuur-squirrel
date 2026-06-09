// Phase 2 OpenWebUIButton — secondary, ghost-style button. Sized to content;
// the parent footer handles layout + spacing.
// EARS R-4.2 (in popup), R-4.3 (uses plugin-opener), R-4.4 (no pre-flight).

import { openWebUrl } from "../api/client";

export function OpenWebUIButton() {
  const handleClick = () => {
    void openWebUrl();
  };

  return (
    <button type="button" onClick={handleClick} className="btn">
      Open Web UI
      <svg
        width="10"
        height="10"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        aria-hidden
      >
        <line x1="7" y1="17" x2="17" y2="7" />
        <polyline points="7 7 17 7 17 17" />
      </svg>
    </button>
  );
}
