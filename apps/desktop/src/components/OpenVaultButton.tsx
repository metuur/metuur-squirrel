import { useEffect, useState } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { api } from "../api/client";

// R-4.1/R-4.3/R-4.4: open the *configured* vault in Obsidian. The vault info
// comes from /api/me, not a hardcoded value. When no vault is configured yet
// (e.g. /api/me 503s during first-run onboarding) the button is disabled
// rather than opening a non-existent vault.
export function OpenVaultButton() {
  const [vault, setVault] = useState<{ name: string; path: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .me()
      .then((me) => {
        if (!cancelled) setVault(me.active_workspace ?? null);
      })
      .catch(() => {
        // 503 (no vault yet) or backend offline → leave disabled. Never throw.
        if (!cancelled) setVault(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleClick = () => {
    if (!vault) return;
    // Open by *path*, not vault name: Obsidian registers vaults under their
    // folder name, which can differ from squirrel's configured vault name.
    void openUrl(`obsidian://open?path=${encodeURIComponent(vault.path)}`);
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className="btn"
      disabled={!vault}
      title={vault ? `Open ${vault.name} in Obsidian` : "No vault configured yet"}
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
