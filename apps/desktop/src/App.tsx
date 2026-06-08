// Phase 2 popup root. Owns the capture-modal state so both the main
// "+ Add a note" button and the per-task "+ note" buttons in
// DeadlinesWidget can open it with the right project pre-selected.

import { useEffect, useMemo, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { useBackend } from "./hooks/useBackend";
import { useHome } from "./hooks/useHome";
import { useFocusSession } from "./hooks/useFocusSession";
import { useDeepLink } from "./hooks/useDeepLink";
import { useNotifications } from "./hooks/useNotifications";
import { openWebUrl } from "./api/client";
import { BackendStatusBanner } from "./components/BackendStatusBanner";
import { HandshakeBanner } from "./components/HandshakeBanner";
import { FocusWidget } from "./components/FocusWidget";
import { FocusPickerModal } from "./components/FocusPickerModal";
import { FocusSwitchModal } from "./components/FocusSwitchModal";
import { DeadlinesWidget } from "./components/DeadlinesWidget";
import { ParakeetWidget } from "./components/ParakeetWidget";
import { CaptureButton } from "./components/CaptureButton";
import { CaptureModal } from "./components/CaptureModal";
import { JournalModal } from "./components/JournalModal";
import { NotificationCenter } from "./components/NotificationCenter";
import { OpenWebUIButton } from "./components/OpenWebUIButton";
import { OpenVaultButton } from "./components/OpenVaultButton";
import { CloseWindowButton } from "./components/CloseWindowButton";
import { SizeToggle } from "./components/SizeToggle";
import { AppCredit } from "./components/AppCredit";
import { HowToModal } from "./components/HowToModal";
import { OnboardingGate } from "./components/OnboardingGate";
import { QuickTaskCaptureModal } from "./components/QuickTaskCaptureModal";
import { QuickTaskWidget } from "./components/QuickTaskWidget";
import { QuickTaskPopover } from "./components/QuickTaskPopover";
import { useQuickTaskCapture } from "./hooks/useQuickTaskCapture";
import { useDevFlag } from "./hooks/useDevFlag";
import { api, type ManualPick } from "./api/client";

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
  const isDev = useDevFlag();

  useEffect(() => {
    if (!deepLink) return;
    if (!status.online) return;
    const id = deepLink.taskId ?? deepLink.projectId;
    openWebUrl(`/notes/${id}`).catch((err) => {
      console.error("[App] deep-link openWebUrl failed:", err);
    });
  }, [deepLink?.key, status.online]); // eslint-disable-line react-hooks/exhaustive-deps

  const [homeBump, setHomeBump] = useState(0);
  // R-1.6: re-fetch widgets each time backend transitions to online.
  // homeBump forces a refetch after a manual-focus mutation (R-5.6) and
  // also drives a 5s focus-sync poll so changes made in the Web UI (or
  // external editor) land here without the user reopening the popup.
  const triggerKey = (status.lastOnlineAt ?? 0) + homeBump;
  const home = useHome(triggerKey);
  // Open work session + derived HH:MM timer (no background process; see hook).
  const focusSession = useFocusSession(triggerKey);

  // Poll /api/home every 5s while the popup is visible and backend is online,
  // so manual_focus stays in sync with the Web UI / vault edits.
  useEffect(() => {
    if (!status.online) return;
    const tick = () => {
      if (document.visibilityState !== "visible") return;
      setHomeBump((n) => n + 1);
    };
    const id = window.setInterval(tick, 5000);
    const onVisible = () => {
      if (document.visibilityState === "visible") setHomeBump((n) => n + 1);
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [status.online]);
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
  const [quickTasksOpen, setQuickTasksOpen] = useState(false);
  const [howToOpen, setHowToOpen] = useState(false);
  const [captureOpen, setCaptureOpen] = useState(false);
  const [journalOpen, setJournalOpen] = useState(false);

  // The tray "How to use Squirrel" item shows the window and emits this
  // event; open the overlay in response. Mirrors HandshakeBanner's listen
  // pattern so the guide appears even if the tray fired before mount.
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    listen("show-how-to", () => setHowToOpen(true)).then((fn) => {
      if (cancelled) fn();
      else unlisten = fn;
    });
    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  // Tray "Mind Journal — check in" → open the in-app journal modal (R-4.4).
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    listen("show-journal", () => setJournalOpen(true)).then((fn) => {
      if (cancelled) fn();
      else unlisten = fn;
    });
    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);
  const [captureInitialSlug, setCaptureInitialSlug] = useState<string | null>(null);
  const [focusModalSlot, setFocusModalSlot] = useState<"today" | "week" | null>(null);
  // The pick the user tried to switch to while a session was open (drives the
  // friendly "Change task?" confirm). `switchBusy` covers the in-flight checkout.
  const [switchPromptPick, setSwitchPromptPick] = useState<ManualPick | null>(null);
  const [switchBusy, setSwitchBusy] = useState(false);

  // Quick Task capture: Ctrl+Cmd+Q / tray "Add Quick Task" emit
  // `quick-task-capture-open`; refetch home after a successful add.
  const quickTaskCapture = useQuickTaskCapture(() => setHomeBump((n) => n + 1));

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

  // Estimate↔actual reconciliation: persist a time estimate on the focused
  // intent (minutes), or clear it (minutes === null). Best-effort; refetch home.
  const handleSetEstimate = async (
    projectSlug: string,
    intentSlug: string,
    minutes: number | null,
  ) => {
    try {
      await api.setEstimate(
        minutes === null
          ? { project_slug: projectSlug, intent_slug: intentSlug, clear: true }
          : { project_slug: projectSlug, intent_slug: intentSlug, minutes },
      );
      setHomeBump((n) => n + 1);
    } catch {
      // Best-effort — leave the existing value in place.
    }
  };

  // Check in to a focus pick. Only one open session is allowed vault-wide, so if
  // a session is already open for a *different* intent we show a friendly confirm
  // and require an explicit check-out first — never auto-close it (R-4.2..R-4.4).
  const handleCheckin = async (pick: ManualPick) => {
    const matches = (p?: ManualPick | null) =>
      !!p && p.project_slug === pick.project_slug && p.intent_slug === pick.intent_slug;
    const open = focusSession.session;
    const openIsThisPick =
      !!open &&
      open.project_slug === pick.project_slug &&
      open.intent_slug === pick.intent_slug;
    if (openIsThisPick) return; // already checked in here
    if (open) {
      // Friendly in-app confirm — require an explicit check-out first.
      setSwitchPromptPick(pick);
      return;
    }
    const mf = homeWithOverride.data?.manual_focus;
    const slot: "today" | "today_pm" | "week" = matches(mf?.today)
      ? "today"
      : matches(mf?.today_pm)
        ? "today_pm"
        : "week";
    try {
      await api.focusCheckin({
        project_slug: pick.project_slug,
        intent_slug: pick.intent_slug,
        slot,
      });
      setHomeBump((n) => n + 1);
      focusSession.refetch();
    } catch {
      // Best-effort.
    }
  };

  // Check out the open session; backend banks the segment into time_invested.
  const handleCheckout = async () => {
    try {
      await api.focusCheckout();
      setHomeBump((n) => n + 1);
      focusSession.refetch();
    } catch {
      // Best-effort.
    }
  };

  // "Check out current task" from the switch confirm. Closes the open session,
  // then dismisses the dialog — no auto-check-in; the user re-taps Check in.
  const handleSwitchCheckout = async () => {
    setSwitchBusy(true);
    try {
      await api.focusCheckout();
      setHomeBump((n) => n + 1);
      focusSession.refetch();
      setSwitchPromptPick(null);
    } catch {
      // Best-effort — leave the dialog open so the user can retry.
    } finally {
      setSwitchBusy(false);
    }
  };

  // Human title for the currently open session, looked up from the manual-focus
  // picks; falls back to the intent slug.
  const openSessionTitle = (() => {
    const open = focusSession.session;
    if (!open) return null;
    const mf = homeWithOverride.data?.manual_focus;
    const match = [mf?.today, mf?.today_pm, mf?.week].find(
      (p) =>
        p &&
        p.project_slug === open.project_slug &&
        p.intent_slug === open.intent_slug,
    );
    return match ? match.next_action || match.intent_title : open.intent_slug;
  })();

  const projects = home.data?.projects ?? [];
  const focusSlug = home.data?.focus?.slug ?? null;

  return (
    <main className="h-screen flex flex-col overflow-hidden">
      {/* First-run onboarding overlay (yields to HandshakeBanner, R-1.3). */}
      <OnboardingGate />
      {/* R-6.2: window-blocking overlay above all content on refused adoption. */}
      <HandshakeBanner />
      <BackendStatusBanner status={status} />

      {/* Sticky header — never scrolls out of view */}
      <header className="flex items-center justify-between px-4 py-3 bg-surface border-b border-hairline shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <img
            src="/squirrel-logo.svg"
            alt=""
            aria-hidden
            className="h-8 w-8 shrink-0"
          />
          <div className="flex items-baseline gap-2.5 min-w-0">
            <span className="title text-[16px]" style={{ letterSpacing: "-0.02em" }}>
              Squirrel
            </span>
            {isDev && (
              <span
                title="Local dev build — not the installed app"
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.06em",
                  padding: "1px 5px",
                  borderRadius: 4,
                  background: "var(--warn-bg, #f59e0b22)",
                  color: "var(--warn, #b45309)",
                  border: "1px solid var(--warn, #b4530955)",
                }}
              >
                DEV
              </span>
            )}
            <span className="eyebrow">Today</span>
            <span className="text-[12px] text-ink-4">·</span>
            <span
              className="tabular text-[12.5px] text-ink-3 truncate"
              style={{ fontWeight: 500, letterSpacing: "-0.005em" }}
            >
              {formatToday()}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setQuickTasksOpen((v) => !v)}
            aria-label="Quick Tasks"
            title="Quick Tasks (⌃⌘Q to capture)"
            className="icon-btn"
          >
            {/* lightning bolt — lucide "zap" */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z" />
            </svg>
            {(home.data?.quick_tasks?.active_count ?? 0) > 0 && (
              <span
                className="notif-badge tabular"
                style={{ top: -3, right: -3 }}
                aria-label={`${home.data?.quick_tasks?.active_count} quick tasks`}
              >
                {home.data?.quick_tasks?.active_count}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setHowToOpen(true)}
            aria-label="How to use Squirrel"
            title="How to use Squirrel"
            className="icon-btn"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </button>
          <button
            type="button"
            onClick={() => setJournalOpen(true)}
            aria-label="Mind Journal"
            title="Mind Journal"
            className="icon-btn"
          >
            {/* brain icon — mirrors public/brain.svg (lucide brain) */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 18V5" />
              <path d="M15 13a4.17 4.17 0 0 1-3-4 4.17 4.17 0 0 1-3 4" />
              <path d="M17.598 6.5A3 3 0 1 0 12 5a3 3 0 1 0-5.598 1.5" />
              <path d="M17.997 5.125a4 4 0 0 1 2.526 5.77" />
              <path d="M18 18a4 4 0 0 0 2-7.464" />
              <path d="M19.967 17.483A4 4 0 1 1 12 18a4 4 0 1 1-7.967-.517" />
              <path d="M6 18a4 4 0 0 1-2-7.464" />
              <path d="M6.003 5.125a4 4 0 0 0-2.526 5.77" />
            </svg>
            {home.data?.journal?.due && (
              <span
                className="notif-badge"
                style={{ top: -2, right: -2, minWidth: 8, height: 8, padding: 0 }}
                aria-label="Check-in due"
              />
            )}
          </button>
          <button
            type="button"
            onClick={() => setNotifOpen((v) => !v)}
            aria-label="Notifications"
            className="icon-btn"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            {notifications.unreadCount > 0 && (
              <span
                className="notif-badge tabular"
                style={{ top: -3, right: -3 }}
              >
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
          session={focusSession.session}
          elapsedMinutes={focusSession.elapsedMinutes}
          onPick={status.online ? setFocusModalSlot : undefined}
          onClear={status.online ? handleClearFocus : undefined}
          onSetEstimate={status.online ? handleSetEstimate : undefined}
          onCheckin={status.online ? handleCheckin : undefined}
          onCheckout={status.online ? handleCheckout : undefined}
        />
        <DeadlinesWidget
          home={home}
          online={status.online}
          projects={projects}
          onAddNote={openCapture}
          scrollTarget={deepLink}
        />
        <QuickTaskWidget
          online={status.online}
          refreshSignal={triggerKey}
          onAdd={quickTaskCapture.openCapture}
        />
        <ParakeetWidget triggerKey={triggerKey} online={status.online} />
      </div>

      {/* Sticky footer — never scrolls out of view */}
      <footer className="flex items-center justify-between gap-2 flex-wrap px-4 py-3 bg-surface-2 border-t border-hairline-2 shrink-0">
        <CaptureButton online={status.online} onClick={() => openCapture(null)} />
        <div className="flex items-center gap-2">
          <OpenWebUIButton />
          <OpenVaultButton />
          <CloseWindowButton />
        </div>
      </footer>

      {/* Gentle credit + global-shortcut strip */}
      <AppCredit />

      <HowToModal open={howToOpen} onClose={() => setHowToOpen(false)} />

      <FocusSwitchModal
        open={switchPromptPick !== null}
        currentTitle={openSessionTitle}
        nextTitle={
          switchPromptPick
            ? switchPromptPick.next_action || switchPromptPick.intent_title
            : null
        }
        busy={switchBusy}
        onCheckoutCurrent={handleSwitchCheckout}
        onCancel={() => setSwitchPromptPick(null)}
      />

      <QuickTaskPopover
        open={quickTasksOpen}
        onClose={() => setQuickTasksOpen(false)}
        online={status.online}
        refreshSignal={triggerKey}
        onAdd={() => {
          setQuickTasksOpen(false);
          quickTaskCapture.openCapture();
        }}
      />

      <QuickTaskCaptureModal
        open={quickTaskCapture.open}
        error={quickTaskCapture.error}
        busy={quickTaskCapture.busy}
        onSubmit={quickTaskCapture.submit}
        onClose={quickTaskCapture.close}
      />

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

      <JournalModal
        open={journalOpen}
        onClose={() => setJournalOpen(false)}
        onLogged={() => setHomeBump((n) => n + 1)}
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
