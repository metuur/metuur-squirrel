import { useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { api } from "../api/client";

// R-4.1/R-4.3/R-4.4: open the *configured* vault in Obsidian. The vault name
// comes from /api/me, not a hardcoded value. When no vault is configured yet
// (e.g. /api/me 503s during first-run onboarding) the button is disabled
// rather than opening a non-existent vault.
export function OpenVaultButton() {
  const [vaultName, setVaultName] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((me) => {
        if (!cancelled) setVaultName(me.active_workspace?.name ?? null);
      })
      .catch(() => {
        // 503 (no vault yet) or backend offline → leave disabled. Never throw.
        if (!cancelled) setVaultName(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleClick = () => {
    if (!vaultName) return;
    void openUrl(`obsidian://open?vault=${encodeURIComponent(vaultName)}`);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="btn"
      disabled={!vaultName}
      title={vaultName ? `Open ${vaultName} in Obsidian` : "No vault configured yet"}
    >
      Open Vault
      <svg
        width="10"
        height="10"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        aria-hidden
      >
        <line x1="7" y1="17" x2="17" y2="7" />
        <polyline points="7 7 17 7 17 17" />
      </svg>
    </button>
  );
}
