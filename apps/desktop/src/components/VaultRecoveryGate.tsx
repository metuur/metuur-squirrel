// Watches /api/me for a vault-recovery signal and, when present, takes over the
// popup with the VaultRecovery overlay. Unlike OnboardingGate (gated on the
// first-run "done" flag), this fires whenever the *configured* vault becomes
// unusable — e.g. the folder was moved or emptied after setup — so a returning
// user gets a guided fix instead of a backend-offline banner.
import { useCallback, useEffect, useState } from "react";
import { api, asVaultRecovery, type VaultRecoveryPayload } from "../api/client";
import { VaultRecovery } from "./VaultRecovery";

export function VaultRecoveryGate() {
  const [info, setInfo] = useState<VaultRecoveryPayload | null>(null);

  const probe = useCallback(async () => {
    try {
      await api.me();
      return null; // vault is healthy
    } catch (e) {
      // Only vault-recovery codes belong to this gate. Transport/401/offline
      // errors are handled by BackendStatusBanner / HandshakeBanner — leaving
      // info null here yields to them.
      return asVaultRecovery(e);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    probe().then((r) => {
      if (!cancelled) setInfo(r);
    });
    return () => {
      cancelled = true;
    };
  }, [probe]);

  // Called after the user takes a recovery action (set up / generate / migrate).
  // Re-probe: if the vault is healthy now, reload so every widget re-initialises
  // against it; otherwise update to the (possibly different) recovery state.
  const onRecovered = useCallback(async () => {
    const r = await probe();
    if (!r) {
      window.location.reload();
      return;
    }
    setInfo(r);
  }, [probe]);

  if (!info) return null;
  return <VaultRecovery info={info} onRecovered={onRecovered} />;
}
