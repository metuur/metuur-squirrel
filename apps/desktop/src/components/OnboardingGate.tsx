// First-run gate (in-app-vault-onboarding Unit 1).
// Renders the OnboardingWizard as a blocking overlay when onboarding has not
// been completed — UNLESS the backend-trust handshake banner is active, which
// takes precedence (R-1.3). Renders nothing once onboarding is done (R-1.2) or
// while the flag is still loading (avoids a wizard flash before we know).

import { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import { isOnboardingDone } from "../lib/onboarding";
import { OnboardingWizard } from "./OnboardingWizard";

export function OnboardingGate() {
  // null = still reading the flag; false = show wizard; true = done.
  const [done, setDone] = useState<boolean | null>(null);
  const [handshakeActive, setHandshakeActive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    isOnboardingDone()
      .then((d) => {
        if (!cancelled) setDone(d);
      })
      .catch(() => {
        // R-1.6: unreadable flag → fail toward showing the wizard.
        if (!cancelled) setDone(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // R-1.3: mirror the handshake-refused event so the wizard yields to the
  // (always-mounted) HandshakeBanner. The refusal is terminal, so once set we
  // keep the wizard suppressed for the process lifetime.
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    // Query on mount as well as listening: the one-shot startup event can fire
    // before this listener registers (Tauri does not replay), which would let
    // the wizard run and fire API calls at a backend the app already refused —
    // surfacing a confusing "Load failed" instead of the recovery banner.
    invoke<string | null>("handshake_state")
      .then((c) => {
        if (!cancelled && c) setHandshakeActive(true);
      })
      .catch(() => {
        // Non-Tauri host — nothing to yield to.
      });
    listen("handshake-refused", () => setHandshakeActive(true)).then((fn) => {
      if (cancelled) fn();
      else unlisten = fn;
    });
    return () => {
      cancelled = true;
      if (unlisten) unlisten();
    };
  }, []);

  if (done !== false) return null; // done === true (R-1.2) or still loading
  if (handshakeActive) return null; // R-1.3 precedence

  return <OnboardingWizard onComplete={() => setDone(true)} />;
}
