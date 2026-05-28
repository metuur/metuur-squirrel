// Phase 2 CaptureButton — opens the CaptureModal.
// EARS R-3.1 (always visible), R-3.2 (disabled when offline with tooltip),
// R-3.3 (click → open modal).

import { useState } from "react";
import { CaptureModal } from "./CaptureModal";

interface Props {
  online: boolean;
}

export function CaptureButton({ online }: Props) {
  const [open, setOpen] = useState(false);
  const disabled = !online;

  return (
    <>
      <button
        type="button"
        onClick={() => !disabled && setOpen(true)}
        disabled={disabled}
        title={disabled ? "Backend offline — capture will fail" : undefined}
        style={{
          background: disabled ? "#334155" : "#2563eb",
          border: "none",
          color: "white",
          padding: "10px 14px",
          fontSize: 13,
          fontWeight: 600,
          cursor: disabled ? "not-allowed" : "pointer",
          opacity: disabled ? 0.55 : 1,
          width: "100%",
          fontFamily: "system-ui, sans-serif",
        }}
      >
        + Capture
      </button>
      <CaptureModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
