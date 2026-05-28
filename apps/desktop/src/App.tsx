// Phase 2 popup root. Owns the capture-modal state so both the main
// "+ Add a note" button and the per-task "+ note" buttons in
// DeadlinesWidget can open it with the right project pre-selected.

import { useState } from "react";
import { useBackend } from "./hooks/useBackend";
import { useHome } from "./hooks/useHome";
import { BackendStatusBanner } from "./components/BackendStatusBanner";
import { FocusWidget } from "./components/FocusWidget";
import { DeadlinesWidget } from "./components/DeadlinesWidget";
import { ParakeetWidget } from "./components/ParakeetWidget";
import { CaptureButton } from "./components/CaptureButton";
import { CaptureModal } from "./components/CaptureModal";
import { OpenWebUIButton } from "./components/OpenWebUIButton";
import { CloseWindowButton } from "./components/CloseWindowButton";
import { SizeToggle } from "./components/SizeToggle";

// Computed once per render — popup is short-lived, so a midnight tick across
// open sessions isn't worth a setInterval.
function formatToday(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export default function App() {
  const status = useBackend();
  // R-1.6: re-fetch widgets each time backend transitions to online.
  const triggerKey = status.lastOnlineAt ?? 0;
  const home = useHome(triggerKey);

  const [captureOpen, setCaptureOpen] = useState(false);
  const [captureInitialSlug, setCaptureInitialSlug] = useState<string | null>(null);

  const openCapture = (initialSlug: string | null) => {
    setCaptureInitialSlug(initialSlug);
    setCaptureOpen(true);
  };

  const projects = home.data?.projects ?? [];
  const focusSlug = home.data?.focus?.slug ?? null;

  return (
    <main className="h-screen bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 flex flex-col overflow-hidden">
      <BackendStatusBanner status={status} />

      {/* Sticky header — never scrolls out of view */}
      <header className="flex items-center justify-between px-4 py-2 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50 shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <img
            src="/squirrel-logo.svg"
            alt=""
            aria-hidden
            className="h-8 w-8 shrink-0"
          />
          <span className="font-bold text-sm text-slate-900 dark:text-slate-100">Squirrel</span>
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 ml-2">
            Today
          </span>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
            · {formatToday()}
          </span>
        </div>
        <SizeToggle />
      </header>

      {/* Scrollable middle — takes all remaining vertical space; the only
          area that overflows. Widgets get their natural height; the cards
          inside DeadlinesWidget scroll vertically when the list grows. */}
      <div className="flex-1 overflow-y-auto pb-2">
        <FocusWidget home={home} online={status.online} />
        <DeadlinesWidget
          home={home}
          online={status.online}
          projects={projects}
          onAddNote={openCapture}
        />
        <ParakeetWidget triggerKey={triggerKey} online={status.online} />
      </div>

      {/* Sticky footer — never scrolls out of view */}
      <footer className="flex items-center justify-between gap-2 flex-wrap px-4 py-2 border-t border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-900/40 shrink-0">
        <CaptureButton online={status.online} onClick={() => openCapture(null)} />
        <div className="flex items-center gap-2">
          <OpenWebUIButton />
          <CloseWindowButton />
        </div>
      </footer>

      <CaptureModal
        open={captureOpen}
        onClose={() => setCaptureOpen(false)}
        projects={projects}
        focusSlug={focusSlug}
        initialSlug={captureInitialSlug}
      />
    </main>
  );
}
