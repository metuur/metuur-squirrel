// Open focus work-session + derived live timer. The timer is NOT a background
// process: `elapsedMinutes` is recomputed from the session's `checkin_at`
// (UTC ISO) against the computer's local clock (`Date.now()`). A 60s interval
// only drives re-render, and it runs ONLY while the popup document is visible —
// closing/hiding the window tears it down. On becoming visible again we refetch
// the session and recompute immediately, so the displayed value is correct with
// no up-to-59s lag on reopen.
//
// Mirrors useHome: generation-guarded fetch, re-fetch on `triggerKey`.

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type OpenSession } from "../api/client";

export interface FocusSessionState {
  session: OpenSession | null;
  elapsedMinutes: number; // live, derived from checkin_at
  loading: boolean;
  refetch: () => void;
}

// floor((now - checkin) / 60000), clamped to 0 for clock skew. Both operands are
// absolute epoch ms, so the result is timezone-correct on any machine.
export function deriveElapsedMinutes(session: OpenSession | null, nowMs: number): number {
  if (!session) return 0;
  const checkinMs = Date.parse(session.checkin_at);
  if (Number.isNaN(checkinMs)) return 0;
  return Math.max(0, Math.floor((nowMs - checkinMs) / 60000));
}

export function useFocusSession(triggerKey: number): FocusSessionState {
  const [session, setSession] = useState<OpenSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const generationRef = useRef(0);
  const [manualKey, setManualKey] = useState(0);

  const refetch = useCallback(() => setManualKey((n) => n + 1), []);

  // Fetch the open session on mount, on triggerKey change, and on manual refetch.
  useEffect(() => {
    const generation = ++generationRef.current;
    setLoading(true);
    api
      .focusSession()
      .then((s) => {
        if (generationRef.current !== generation) return;
        setSession(s);
        setNowMs(Date.now());
        setLoading(false);
      })
      .catch(() => {
        if (generationRef.current !== generation) return;
        // Best-effort: leave last-known session in place, stop the spinner.
        setLoading(false);
      });
  }, [triggerKey, manualKey]);

  // Visibility-aware minute tick. Only runs while the document is visible; on
  // becoming visible we refetch and recompute immediately.
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    const start = () => {
      if (interval !== null) return;
      setNowMs(Date.now());
      interval = setInterval(() => setNowMs(Date.now()), 60000);
    };
    const stop = () => {
      if (interval !== null) {
        clearInterval(interval);
        interval = null;
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === "visible") {
        refetch(); // pick up any session change that happened while hidden
        start();
      } else {
        stop();
      }
    };

    if (document.visibilityState === "visible") start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      stop();
    };
  }, [refetch]);

  return {
    session,
    elapsedMinutes: deriveElapsedMinutes(session, nowMs),
    loading,
    refetch,
  };
}
