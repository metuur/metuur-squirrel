// Phase 2: top banner shown whenever the backend is unreachable. EARS R-1.5.
//
// Copy is end-user oriented — the prior wording instructed the user to "run
// make backend-start in the squirrel monorepo", which only makes sense to
// someone with the source checkout. End users who install via the DMG have
// neither monorepo nor make. The Restart button calls
// tauri-plugin-process::relaunch() so the recovery path is actionable from
// inside the popup without a terminal.
//
// Visual: paper-indigo critical palette — soft critical-bg, refined cardinal
// text, hairline divider to the header below. The Restart button is the
// design-system .btn recipe with critical tokens applied via the
// already-inherited text color.

import { useState } from "react";
import { relaunch } from "@tauri-apps/plugin-process";
import type { BackendStatus } from "../hooks/useBackend";

interface Props {
  status: BackendStatus;
}

// True when the popup runs inside the Tauri webview (production DMG or
// `pnpm tauri dev`). False for plain-browser dev (visiting localhost:5173).
// We only render the Restart button in Tauri because relaunch() is a no-op
// outside it.
function isTauriContext(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

const RESTART_BTN_STYLE: React.CSSProperties = {
  background: "rgba(200, 54, 42, 0.06)",
  borderColor: "rgba(200, 54, 42, 0.35)",
  color: "var(--color-critical)",
  boxShadow: "1px 1px 0 rgba(200, 54, 42, 0.25)",
  padding: "3px 9px",
  fontSize: 11,
};

export function BackendStatusBanner({ status }: Props) {
  const [restarting, setRestarting] = useState(false);
  if (status.online) return null;

  const handleRestart = async () => {
    setRestarting(true);
    try {
      await relaunch();
    } catch (err) {
      // relaunch() only resolves on failure; a successful relaunch terminates
      // the process before this code runs. Reset the spinner so the user can
      // retry instead of being stuck on "Restarting…".
      console.error("[BackendStatusBanner] relaunch failed:", err);
      setRestarting(false);
    }
  };

  return (
    <div
      role="status"
      className="shrink-0 flex items-center justify-between gap-2 bg-critical-bg text-critical px-4 py-2 text-xs"
      style={{ borderBottom: "1px solid rgba(200, 54, 42, 0.25)" }}
    >
      <span className="flex items-center gap-2">
        <span aria-hidden className="text-critical">⚠</span>
        <span>Backend offline. Trying to reconnect. If this persists, restart Squirrel.</span>
      </span>
      {isTauriContext() && (
        <button
          type="button"
          onClick={handleRestart}
          disabled={restarting}
          className="btn shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
          style={RESTART_BTN_STYLE}
        >
          {restarting ? "Restarting…" : "Restart"}
        </button>
      )}
    </div>
  );
}
