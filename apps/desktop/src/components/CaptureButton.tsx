// Phase 2 CaptureButton — primary "+ Add a note" affordance. Style mirrors
// the web UI top-bar button (bg-primary, white text, rounded, font-semibold).
// EARS R-3.1 (visible), R-3.2 (offline-disable), R-3.3 (click → modal).

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
        className={`mx-4 mt-3 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg transition-colors ${
          disabled
            ? "bg-slate-200 text-slate-400 cursor-not-allowed dark:bg-slate-700 dark:text-slate-500"
            : "bg-primary text-white hover:bg-primary-dark"
        }`}
      >
        <span aria-hidden className="text-base leading-none">+</span>
        Add a note
      </button>
      <CaptureModal open={open} onClose={() => setOpen(false)} />
    </>
  );
}
