// Blocking recovery overlay for the popup when the configured vault can't be
// used. Driven by the /api/me error payload (see api/client.ts::asVaultRecovery):
//   NO_VAULT / VAULT_MISSING → pick/enter a folder and (re)create it in-app
//   VAULT_EMPTY              → one-click "Generate Squirrel structure"
//   VAULT_UNSTRUCTURED       → show the /sq-migrate-vault prompt to reorganize
// Actions complete in-app (no web UI), consistent with the rest of the popup.
import { useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { api, openWebUrl, type VaultRecoveryPayload } from "../api/client";

export function VaultRecovery({
  info,
  onRecovered,
}: {
  info: VaultRecoveryPayload;
  onRecovered: () => void;
}) {
  const currentPath = info.vault?.path ?? "";
  const [path, setPath] = useState(currentPath);
  // Destination for the new Squirrel vault in the unstructured (import) flow —
  // must differ from the source folder, so never default it to currentPath.
  const [newPath, setNewPath] = useState("~/squirrel-vault");
  const [vaultCreated, setVaultCreated] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const isEmpty = info.code === "VAULT_EMPTY";
  const isUnstructured = info.code === "VAULT_UNSTRUCTURED";
  const migrateCmd = info.migrate_command ?? `/sq-migrate-vault ${currentPath}`;

  // Set/repair the active vault, then leave the recovery screen (re-probe).
  const setup = async (targetPath: string) => {
    if (!targetPath.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.setVaultConfig({ path: targetPath.trim(), create: true });
      onRecovered();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not set up the workspace.");
    } finally {
      setBusy(false);
    }
  };

  // Unstructured step 1: create a NEW Squirrel vault (the migrate target) but
  // stay on screen so the user can then run the import command.
  const createNewVault = async (targetPath: string) => {
    if (!targetPath.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.setVaultConfig({ path: targetPath.trim(), create: true });
      setVaultCreated(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not create the vault.");
    } finally {
      setBusy(false);
    }
  };

  const pickFolder = async (setter: (p: string) => void) => {
    const picked = await openDialog({ directory: true });
    if (typeof picked === "string") setter(picked);
  };

  const copyCmd = async () => {
    try {
      await navigator.clipboard.writeText(migrateCmd);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — the command is still visible to copy by hand */
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Workspace recovery"
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface"
    >
      <div className="w-full max-w-md px-6 py-7 flex flex-col gap-4">
        <header className="flex items-center gap-3">
          <img src="/squirrel-logo.svg" alt="" aria-hidden className="h-8 w-8" />
          <span className="title text-[16px]">Squirrel</span>
        </header>

        <h1 className="title text-[18px]">
          {isEmpty
            ? "Your workspace is empty"
            : isUnstructured
              ? "Convert your existing vault"
              : "Workspace not found"}
        </h1>

        <p className="text-ink-3 text-[13px]">{info.error}</p>

        {currentPath && (
          <div className="tabular text-[12px] break-all text-ink-2 px-2 py-1 rounded bg-surface-2 border border-hairline">
            {currentPath}
          </div>
        )}

        {isUnstructured ? (
          <section className="flex flex-col gap-4">
            <p className="text-ink-3 text-[13px]">
              This folder has notes but isn’t a Squirrel vault. Convert it: create a
              Squirrel vault, then import these notes into it. Your original folder is
              never modified.
            </p>

            {/* Step 1 — create the destination vault */}
            <div className="flex flex-col gap-1.5">
              <span className="eyebrow text-[11px] text-ink-4">Step 1 · Create your Squirrel vault</span>
              {vaultCreated ? (
                <p className="text-[13px]" style={{ color: "var(--ok, #2e7d32)" }}>
                  ✓ Vault created at {newPath}
                </p>
              ) : (
                <>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newPath}
                      onChange={(e) => setNewPath(e.target.value)}
                      placeholder="~/squirrel-vault"
                      spellCheck={false}
                      aria-label="New vault path"
                      className="flex-1 px-2 py-1 border border-hairline rounded bg-surface-2 tabular text-[13px]"
                    />
                    <button type="button" className="btn" onClick={() => void pickFolder(setNewPath)}>
                      Choose…
                    </button>
                  </div>
                  <button
                    type="button"
                    className="btn w-fit"
                    disabled={busy || !newPath.trim() || newPath.trim() === currentPath}
                    onClick={() => void createNewVault(newPath)}
                  >
                    {busy ? "Creating…" : "Create vault"}
                  </button>
                </>
              )}
            </div>

            {/* Step 2 — import the notes */}
            <div className="flex flex-col gap-1.5">
              <span className="eyebrow text-[11px] text-ink-4">Step 2 · Import these notes</span>
              <span className="text-ink-3 text-[13px]">Run this in your coding agent:</span>
              <div className="flex items-stretch gap-2">
                <code className="flex-1 rounded bg-surface-2 px-1.5 py-1 font-mono text-[12px] text-ink-1 break-all select-all">
                  {migrateCmd}
                </code>
                <button type="button" className="btn" onClick={() => void copyCmd()}>
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
            </div>

            {error && <p className="text-[13px]" style={{ color: "var(--danger, #c0392b)" }}>{error}</p>}
            <div className="flex justify-end">
              <button type="button" className="btn" disabled={busy} onClick={onRecovered}>
                Open Squirrel
              </button>
            </div>
          </section>
        ) : isEmpty ? (
          <section className="flex flex-col gap-3">
            <p className="text-ink-3 text-[13px]">
              Generate Squirrel’s starter structure (Active Projects, Parking Lot,
              Areas, Archive, Resources) in this folder.
            </p>
            {error && <p className="text-[13px]" style={{ color: "var(--danger, #c0392b)" }}>{error}</p>}
            <div className="flex justify-end">
              <button
                type="button"
                className="btn"
                disabled={busy}
                onClick={() => void setup(currentPath)}
              >
                {busy ? "Generating…" : "Generate structure"}
              </button>
            </div>
          </section>
        ) : (
          <section className="flex flex-col gap-3">
            <label className="text-ink-3 text-[13px] flex flex-col gap-1.5">
              Set up your workspace here (created if missing):
              <div className="flex gap-2">
                <input
                  type="text"
                  value={path}
                  onChange={(e) => setPath(e.target.value)}
                  placeholder="~/squirrel-vault"
                  spellCheck={false}
                  aria-label="Workspace path"
                  className="flex-1 px-2 py-1 border border-hairline rounded bg-surface-2 tabular text-[13px]"
                />
                <button type="button" className="btn" onClick={() => void pickFolder(setPath)}>
                  Choose…
                </button>
              </div>
            </label>
            <p className="text-ink-4 text-[12px]">
              Converting an existing Obsidian vault? Create a fresh vault here, then
              run <code className="font-mono">/sq-migrate-vault &lt;your-vault&gt;</code>.
            </p>
            {error && <p className="text-[13px]" style={{ color: "var(--danger, #c0392b)" }}>{error}</p>}
            <div className="flex justify-end">
              <button
                type="button"
                className="btn"
                disabled={busy || !path.trim()}
                onClick={() => void setup(path)}
              >
                {busy ? "Setting up…" : "Set up workspace"}
              </button>
            </div>
          </section>
        )}

        {/* Escape hatch: set up the vault in the full web UI (bigger window). */}
        <div className="pt-1 border-t border-hairline">
          <button
            type="button"
            className="text-ink-4 text-[12px] hover:text-ink-2 underline underline-offset-2"
            onClick={() => void openWebUrl("")}
          >
            Prefer a bigger window? Set up in the web UI →
          </button>
        </div>
      </div>
    </div>
  );
}
