// Phase 2 shared /api/home fetch. FocusWidget and DeadlinesWidget both
// consume it, so we deduplicate the network call (LLD D2: per-widget
// independence preserved, this is fetch-dedup, not coupling).
//
// Re-fetches when `triggerKey` changes — the parent rebumps it whenever
// useBackend() transitions to online (R-1.6).

import { useEffect, useRef, useState } from "react";
import { api, type HomePayload } from "../api/client";

export interface HomeState {
  data: HomePayload | null;
  loading: boolean;
  error: string | null;
  lastFetchedAt: number | null;
}

const INITIAL: HomeState = {
  data: null,
  loading: false,
  error: null,
  lastFetchedAt: null,
};

export function useHome(triggerKey: number): HomeState {
  const [state, setState] = useState<HomeState>(INITIAL);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    api
      .home()
      .then((data) => {
        if (!mountedRef.current) return;
        setState({
          data,
          loading: false,
          error: null,
          lastFetchedAt: Date.now(),
        });
      })
      .catch((err) => {
        if (!mountedRef.current) return;
        const msg = err instanceof Error ? err.message : String(err);
        setState((prev) => ({
          data: prev.data, // keep last-good for R-2.9 dimmed rendering
          loading: false,
          error: msg,
          lastFetchedAt: prev.lastFetchedAt,
        }));
      });
    return () => {
      mountedRef.current = false;
    };
  }, [triggerKey]);

  return state;
}
