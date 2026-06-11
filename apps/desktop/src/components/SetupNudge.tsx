// Post-install/update setup nudge.
// After onboarding is complete (first run is handled by the OnboardingWizard),
// this re-shows the RecommendedSetup card once per app version change — i.e.
// after each install or update — so reminders/login-at-launch keep working.
// Dismissing ("Got it") records the current version (setupNudge.ack). Yields to
// the handshake banner, mirroring OnboardingGate.

import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { getVersion } from "@tauri-apps/api/app";
import { isOnboardingDone } from "../lib/onboarding";
import { shouldShowSetupNudge, ackSetupNudge } from "../lib/setupNudge";
import { RecommendedSetup } from "./RecommendedSetup";

export function SetupNudge() {
  const [show, setShow] = useState(false);
  const [version, setVersion] = useState<string | null>(null);
  const [handshakeActive, setHandshakeActive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        // Only after onboarding (first run owns setup via the wizard) AND only
        // when the running version differs from the last acknowledged one.
        const [done, changed] = await Promise.all([
          isOnboardingDone(),
          shouldShowSetupNudge(),
        ]);
        if (!cancelled && done && changed) setShow(true);
      } catch {
        // Never nag on error.
      }
    })();
    getVersion()
      .then((v) => !cancelled && setVersion(v))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Yield to the handshake banner (mirrors OnboardingGate, R-1.3). Query on
  // mount as well as listening, since the one-shot startup event is not replayed
  // and may fire before this listener registers.
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    invoke<string | null>("handshake_state")
      .then((c) => {
        if (!cancelled && c) setHandshakeActive(true);
      })
      .catch(() => {});
    listen("handshake-refused", () => setHandshakeActive(true)).then((fn) => {
      if (cancelled) fn();
      else unlisten = fn;
    });
    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  const dismiss = async () => {
    await ackSetupNudge();
    setShow(false);
  };

  if (!show || handshakeActive) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Squirrel setup check"
      className="fixed inset-0 z-40 flex items-center justify-center bg-surface"
    >
      <div className="w-full max-w-md px-6 py-7 flex flex-col gap-5">
        <header className="flex items-center gap-3">
          <img src="/squirrel-logo.svg" alt="" aria-hidden className="h-8 w-8" />
          <span className="title text-[16px]">Squirrel</span>
        </header>
        <section className="flex flex-col gap-4">
          <h1 className="title text-[18px]">Squirrel is up to date</h1>
          {version && <p className="text-ink-4 tabular text-[11px]">Version {version}</p>}
          <p className="text-ink-3 text-[13px]">
            A quick check so reminders and launch-at-login keep working after this
            update:
          </p>
          <RecommendedSetup />
          <div className="flex justify-end">
            <button type="button" className="btn" onClick={() => void dismiss()}>
              Got it
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
