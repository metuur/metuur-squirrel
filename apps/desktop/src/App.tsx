// Phase 2 popup root. Full mount per EARS R-2.1:
// BackendStatusBanner, FocusWidget, DeadlinesWidget, ParakeetWidget,
// CaptureButton, OpenWebUIButton — wrapped in a chrome that echoes the
// web UI's top-bar (squirrel logo word + dashboard label).

import { useBackend } from "./hooks/useBackend";
import { useHome } from "./hooks/useHome";
import { BackendStatusBanner } from "./components/BackendStatusBanner";
import { FocusWidget } from "./components/FocusWidget";
import { DeadlinesWidget } from "./components/DeadlinesWidget";
import { ParakeetWidget } from "./components/ParakeetWidget";
import { CaptureButton } from "./components/CaptureButton";
import { OpenWebUIButton } from "./components/OpenWebUIButton";

export default function App() {
  const status = useBackend();
  // R-1.6: re-fetch widgets each time backend transitions to online.
  const triggerKey = status.lastOnlineAt ?? 0;
  const home = useHome(triggerKey);

  return (
    <main className="min-h-screen bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 flex flex-col">
      <BackendStatusBanner status={status} />

      {/* Top chrome — mirrors the web UI's brand row */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/50">
        <div className="flex items-center gap-2">
          <span aria-hidden className="text-lg">🐿️</span>
          <span className="font-bold text-sm text-slate-900 dark:text-slate-100">Squirrel</span>
        </div>
        <span className="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500">
          Today
        </span>
      </header>

      <FocusWidget home={home} online={status.online} />
      <DeadlinesWidget home={home} online={status.online} />
      <ParakeetWidget triggerKey={triggerKey} online={status.online} />

      <div className="flex-1" />

      <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-900/40">
        <CaptureButton online={status.online} />
        <OpenWebUIButton />
      </div>
    </main>
  );
}
