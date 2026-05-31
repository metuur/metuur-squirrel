// Phase 2: top banner shown whenever the backend is unreachable. EARS R-1.5.
//
// The copy is intentionally end-user oriented — the prior wording instructed
// the user to "run make backend-start in the squirrel monorepo", which only
// makes sense to someone with the source checkout. End users who install via
// the DMG have neither monorepo nor make. The Restart button calls
// tauri-plugin-process::relaunch() so the recovery path is actionable from
// inside the popup without a terminal.

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
      className="shrink-0 flex items-center justify-between gap-2 bg-red-50 dark:bg-red-900/30 border-b border-red-200 dark:border-red-900/50 text-red-800 dark:text-red-100 px-4 py-2 text-xs"
    >
      <span className="flex items-center gap-2">
        <span aria-hidden className="text-red-500 dark:text-red-300">⚠</span>
        <span>Backend offline. Trying to reconnect. If this persists, restart Squirrel.</span>
      </span>
      {isTauriContext() && (
        <button
          type="button"
          onClick={handleRestart}
          disabled={restarting}
          className="shrink-0 rounded border border-red-300 dark:border-red-700 bg-white/60 dark:bg-red-950/40 hover:bg-white dark:hover:bg-red-950/70 disabled:opacity-50 disabled:cursor-not-allowed px-2 py-0.5 text-[11px] font-medium text-red-800 dark:text-red-100"
        >
          {restarting ? "Restarting…" : "Restart"}
        </button>
      )}
    </div>
  );
}
