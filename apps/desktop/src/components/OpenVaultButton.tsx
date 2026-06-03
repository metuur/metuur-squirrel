import { openUrl } from "@tauri-apps/plugin-opener";

const VAULT_URL = "obsidian://open?vault=vault-tdah";

export function OpenVaultButton() {
  const handleClick = () => {
    void openUrl(VAULT_URL);
  };

  return (
    <button type="button" onClick={handleClick} className="btn">
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
