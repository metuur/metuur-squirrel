// Phase 2 ParakeetWidget — renders /api/parakeet message verbatim.
// Visual matches code.html lines 611-633 ("slipped past" callout):
// warm-paper-2 background, hairline border, gentle nudge tone.
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
      className={`mx-4 mt-2 mb-2 rounded-lg px-3 py-1.5 ${online ? "" : "opacity-50"}`}
      style={{
        background: "#FAF7F0",
        border: "1px solid #ECE6D6",
        boxShadow: "0 1px 0 rgba(0, 0, 0, 0.02)",
      }}
    >
      <p className="text-[11px] italic text-ink-2 leading-snug">{message}</p>
    </div>
  );
}
