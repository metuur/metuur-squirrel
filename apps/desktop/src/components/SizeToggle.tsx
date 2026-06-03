// Phase 2 SizeToggle — quick swap between full (800×620) and compact
// (380×620, menubar-popup feel). Adjustable from the popup header without
// hunting for window corners. State lives in the React tree; we ask the
// Tauri window for its current size on mount so the button reflects truth
// even if the user resized the window by dragging.

import { useEffect, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { LogicalSize } from "@tauri-apps/api/dpi";

const COMPACT = { width: 380, height: 620 };
const FULL = { width: 800, height: 620 };
const COMPACT_THRESHOLD = 500; // anything narrower than this is "compact"

export function SizeToggle() {
  const [isCompact, setIsCompact] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void getCurrentWindow()
      .outerSize()
      .then((s) => {
        if (!cancelled) setIsCompact(s.width < COMPACT_THRESHOLD);
      })
      .catch(() => {
        /* not in Tauri (e.g. plain browser dev) — leave default */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const toggle = async () => {
    const target = isCompact ? FULL : COMPACT;
    try {
      await getCurrentWindow().setSize(new LogicalSize(target.width, target.height));
      setIsCompact(!isCompact);
    } catch {
      /* not in Tauri — no-op */
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      title={isCompact ? "Expand to full size" : "Shrink to compact"}
      aria-label={isCompact ? "Expand" : "Compact"}
      className="icon-btn"
    >
      <svg
        width="19"
        height="19"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
      >
        <rect x="3.5" y="5.5" width="17" height="13" rx="1.5" />
        <line x1="3.5" y1="11" x2="20.5" y2="11" />
      </svg>
    </button>
  );
}
