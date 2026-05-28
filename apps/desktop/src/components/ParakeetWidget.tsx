// Phase 2 ParakeetWidget — renders /api/parakeet message verbatim.
// EARS R-2.7 (render), R-2.8 (empty → 0px), R-2.9 (dimmed when offline).

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
        // Keep last-good on error (R-2.9). Do not clear.
      });
    return () => {
      mountedRef.current = false;
    };
  }, [triggerKey]);

  // R-2.8: empty/whitespace-only message → render zero pixels.
  if (!message || message.trim() === "") return null;

  return (
    <section
      style={{
        padding: "10px 14px",
        borderBottom: "1px solid #1f2937",
        opacity: online ? 1 : 0.5,
        fontFamily: "system-ui, sans-serif",
        fontSize: 12,
        color: "#fde68a",
        fontStyle: "italic",
      }}
    >
      {message}
    </section>
  );
}
