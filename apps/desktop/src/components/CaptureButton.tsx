// Phase 2 CaptureButton — primary "+ Add a note" affordance.
// EARS R-3.1 (visible), R-3.2 (offline-disable), R-3.3 (click → modal).
// Now also forwards the project list + focus slug to the modal so the
// user can route the note to a specific project.

import { useState } from "react";
import { CaptureModal } from "./CaptureModal";
import type { ProjectListItem } from "../api/client";

interface Props {
  online: boolean;
  projects: ProjectListItem[];
  focusSlug: string | null;
}

export function CaptureButton({ online, projects, focusSlug }: Props) {
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
      <CaptureModal
        open={open}
        onClose={() => setOpen(false)}
        projects={projects}
        focusSlug={focusSlug}
      />
    </>
  );
}
