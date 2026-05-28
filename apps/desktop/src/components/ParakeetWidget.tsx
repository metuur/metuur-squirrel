// Phase 2 ParakeetWidget — renders /api/parakeet message verbatim.
// Style: small italic callout in amber/yellow surface to match the web
// UI's tone-of-voice for the parakeet line.
// EARS R-2.7, R-2.8, R-2.9.

import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

interface Props {
  triggerKey: number;
  online: boolean;
}

export function ParakeetWidget({ triggerKey, online }: Props) {
  const [message, setMessage] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    api
      .parakeet()
      .then((p) => {
        if (mountedRef.current) setMessage(p.message);
      })
      .catch(() => {
        // R-2.9: keep last-good on transient error.
      });
    return () => {
      mountedRef.current = false;
    };
  }, [triggerKey]);

  // R-2.8: empty/whitespace-only message → render zero pixels.
  if (!message || message.trim() === "") return null;

  return (
    <div
      className={`mx-4 mt-2 mb-2 rounded-lg border border-amber-200 dark:border-amber-700/40 bg-amber-50 dark:bg-amber-900/20 px-3 py-1.5 ${
        online ? "" : "opacity-50"
      }`}
    >
      <p className="text-[11px] italic text-amber-800 dark:text-amber-200 leading-snug">{message}</p>
    </div>
  );
}
