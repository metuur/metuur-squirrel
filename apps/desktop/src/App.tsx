// Phase 2 popup root. Owns the capture-modal state so both the main
// "+ Add a note" button and the per-task "+ note" buttons in
// DeadlinesWidget can open it with the right project pre-selected.

import { useEffect, useMemo, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { useBackend } from "./hooks/useBackend";
import { useHome } from "./hooks/useHome";
import { useDeepLink } from "./hooks/useDeepLink";
import { useNotifications } from "./hooks/useNotifications";
import { BACKEND_ORIGIN } from "./api/client";
import { BackendStatusBanner } from "./components/BackendStatusBanner";
import { FocusWidget } from "./components/FocusWidget";
import { FocusPickerModal } from "./components/FocusPickerModal";
import { DeadlinesWidget } from "./components/DeadlinesWidget";
import { ParakeetWidget } from "./components/ParakeetWidget";
import { CaptureButton } from "./components/CaptureButton";
import { CaptureModal } from "./components/CaptureModal";
import { NotificationCenter } from "./components/NotificationCenter";
import { OpenWebUIButton } from "./components/OpenWebUIButton";
import { CloseWindowButton } from "./components/CloseWindowButton";
import { SizeToggle } from "./components/SizeToggle";
import { api } from "./api/client";

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
  const deepLink = useDeepLink();
  const notifications = useNotifications();

  useEffect(() => {
    if (!deepLink) return;
    if (!status.online) return;
    const id = deepLink.taskId ?? deepLink.projectId;
    openUrl(`${BACKEND_ORIGIN}/notes/${id}`).catch((err) => {
      console.error("[App] deep-link openUrl failed:", err);
    });
  }, [deepLink?.key, status.online]); // eslint-disable-line react-hooks/exhaustive-deps

  const [homeBump, setHomeBump] = useState(0);
  // R-1.6: re-fetch widgets each time backend transitions to online.
  // homeBump forces a refetch after a manual-focus mutation (R-5.6).
  const triggerKey = (status.lastOnlineAt ?? 0) + homeBump;
  const home = useHome(triggerKey);
  // Optimistic focus state: applied immediately from the API response so the
  // widget reflects the new pick without waiting for the next full home refetch.
  const [focusOverride, setFocusOverride] = useState<import("./api/client").ManualFocusPayload | null>(null);

  // Merge override into home state; clear it once the background refetch lands.
  const homeWithOverride = useMemo(() => {
    if (!focusOverride || !home.data) return home;
    return { ...home, data: { ...home.data, manual_focus: focusOverride } };
  }, [home, focusOverride]);

  // Clear override as soon as a fresh refetch provides its own manual_focus.
  useEffect(() => {
    if (focusOverride && home.data && !home.loading) setFocusOverride(null);
  }, [home.data, home.loading]); // eslint-disable-line react-hooks/exhaustive-deps

  const [notifOpen, setNotifOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [captureInitialSlug, setCaptureInitialSlug] = useState<string | null>(null);
  const [focusModalSlot, setFocusModalSlot] = useState<"today" | "week" | null>(null);

  const openCapture = (initialSlug: string | null) => {
    setCaptureInitialSlug(initialSlug);
    setCaptureOpen(true);
  };

  const handleClearFocus = async (slot: "today" | "week") => {
    try {
      if (slot === "today") {
        // clear both AM and PM slots together
        await Promise.all([
          api.focusSet("today", { clear: true }),
          api.focusSet("today_pm", { clear: true }),
        ]);
      } else {
        await api.focusSet(slot, { clear: true });
      }
      setHomeBump((n) => n + 1);
    } catch {
      // Best-effort.
    }
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
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setNotifOpen((v) => !v)}
            aria-label="Notifications"
            className="relative p-1 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            {notifications.unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[14px] h-[14px] px-[3px] bg-amber-400 text-white text-[8px] font-bold rounded-full leading-none">
                {notifications.unreadCount}
              </span>
            )}
          </button>
          <SizeToggle />
        </div>
      </header>

      {/* Scrollable middle — takes all remaining vertical space; the only
          area that overflows. Widgets get their natural height; the cards
          inside DeadlinesWidget scroll vertically when the list grows. */}
      <div className="flex-1 overflow-y-auto pb-2">
        <FocusWidget
          home={homeWithOverride}
          online={status.online}
          onPick={status.online ? setFocusModalSlot : undefined}
          onClear={status.online ? handleClearFocus : undefined}
        />
        <DeadlinesWidget
          home={home}
          online={status.online}
          projects={projects}
          onAddNote={openCapture}
          scrollTarget={deepLink}
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

      <NotificationCenter
        notifications={notifications}
        open={notifOpen}
        onClose={() => setNotifOpen(false)}
      />

      <CaptureModal
        open={captureOpen}
        onClose={() => setCaptureOpen(false)}
        projects={projects}
        focusSlug={focusSlug}
        initialSlug={captureInitialSlug}
      />

      {focusModalSlot && (
        <FocusPickerModal
          slot={focusModalSlot}
          projects={projects}
          currentAmPick={home.data?.manual_focus?.today ?? null}
          currentPmPick={home.data?.manual_focus?.today_pm ?? null}
          onClose={() => setFocusModalSlot(null)}
          onPicked={(result) => {
            setFocusOverride(result);
            setHomeBump((n) => n + 1);
            setFocusModalSlot(null);
          }}
        />
      )}
    </main>
  );
}
