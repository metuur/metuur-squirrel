// Phase 2 backend liveness probe. Polls /api/me every 10s and exposes a
// stable status the popup widgets read.
//
// Contract (EARS R-1.2 → R-1.7):
//   - First /api/me call within 500ms of mount
//   - Re-poll every 10s while mounted
//   - 2xx → online; non-2xx / network error / >3s timeout → offline
//   - Never start, restart, or stop the backend process

import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

const POLL_INTERVAL_MS = 10_000;

export interface BackendStatus {
  online: boolean;
  lastOnlineAt: number | null;
  lastError: string | null;
}

export function useBackend(): BackendStatus {
  const [state, setState] = useState<BackendStatus>({
    online: false,
    lastOnlineAt: null,
    lastError: null,
  });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const probe = async () => {
      try {
        await api.me();
        if (!mountedRef.current) return;
        setState({
          online: true,
          lastOnlineAt: Date.now(),
          lastError: null,
        });
      } catch (err) {
        if (!mountedRef.current) return;
        const msg = err instanceof Error ? err.message : String(err);
        setState((prev) => ({
          online: false,
          lastOnlineAt: prev.lastOnlineAt,
          lastError: msg,
        }));
      } finally {
        if (mountedRef.current) {
          timer = setTimeout(probe, POLL_INTERVAL_MS);
        }
      }
    };

    // R-1.2: first call within 500ms (immediate is well under 500ms)
    void probe();

    return () => {
      mountedRef.current = false;
      if (timer !== null) clearTimeout(timer);
    };
  }, []);

  return state;
}
