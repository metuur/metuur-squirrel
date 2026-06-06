// True when this is a local/dev run rather than the installed app.
// Two independent signals, OR'd:
//   - import.meta.env.DEV  → served by the vite dev server (`tauri dev`)
//   - GET /api/me { dev }  → backend running without token auth (covers a
//     bundled dev .app that points at a dev backend)

import { useEffect, useState } from "react";
import { api } from "../api/client";

export function useDevFlag(): boolean {
  const [backendDev, setBackendDev] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((me) => {
        if (!cancelled) setBackendDev(!!me.dev);
      })
      .catch(() => {
        // backend offline / 503 during onboarding → ignore, fall back to vite flag
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return import.meta.env.DEV || backendDev;
}
