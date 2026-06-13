// Full-screen recovery flow shown when the configured vault can't be used.
// Driven by the backend's /api/me error payload (see api/client.ts):
//   NO_VAULT / VAULT_MISSING → ask for a folder and (re)create it
//   VAULT_EMPTY              → one-click "Generate Squirrel structure"
//   VAULT_UNSTRUCTURED       → show the /sq-migrate-vault prompt to reorganize
import { useState } from 'react';
import { api, type VaultRecoveryPayload } from '@/api/client';

export function VaultRecovery({
  info,
  onRecovered,
}: {
  info: VaultRecoveryPayload;
  onRecovered: () => void;
}) {
  const currentPath = info.vault?.path ?? '';
  const [path, setPath] = useState(currentPath);
  // Destination for the new Squirrel vault in the unstructured (import) flow —
  // must differ from the source folder, so we never default it to currentPath.
  const [newPath, setNewPath] = useState('~/squirrel-vault');
  const [vaultCreated, setVaultCreated] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const isEmpty = info.code === 'VAULT_EMPTY';
  const isLegacy = info.code === 'VAULT_LEGACY';
  const isUnstructured = info.code === 'VAULT_UNSTRUCTURED';
  const migrateCmd = info.migrate_command ?? `/sq-migrate-vault ${currentPath}`;

  // Legacy layout: rename old folders to the canonical names in place, then re-probe.
  async function repair() {
    setBusy(true);
    setError(null);
    try {
      await api.repairVault();
      onRecovered();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not repair the workspace.');
    } finally {
      setBusy(false);
    }
  }

  // Set/repair the active vault, then leave the recovery screen (re-probe).
  async function setup(targetPath: string) {
    if (!targetPath.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.setVaultConfig({ path: targetPath.trim(), create: true });
      onRecovered();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not set up the workspace.');
    } finally {
      setBusy(false);
    }
  }

  // Unstructured step 1: create a NEW Squirrel vault (becomes the migrate
  // target) but stay on screen so the user can then run the import command.
  async function createNewVault(targetPath: string) {
    if (!targetPath.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.setVaultConfig({ path: targetPath.trim(), create: true });
      setVaultCreated(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create the vault.');
    } finally {
      setBusy(false);
    }
  }

  async function copyCmd() {
    try {
      await navigator.clipboard.writeText(migrateCmd);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — the command is still visible to copy by hand */
    }
  }

  return (
    <div className="min-h-full flex items-center justify-center p-6">
      <div className="w-full max-w-lg flex flex-col gap-5 rounded-xl border border-hairline bg-surface p-7 shadow-sm">
        <div className="flex items-center gap-2 text-ink">
          <img src="/squirrel.svg" alt="" aria-hidden className="w-9 h-9" />
          <span className="font-bold tracking-tight text-lg">Squirrel</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="material-icons text-3xl text-amber-500">folder_off</span>
          <h1 className="text-xl font-bold text-ink">
            {isEmpty
              ? 'Your workspace is empty'
              : isLegacy
                ? 'Update your workspace structure'
                : isUnstructured
                  ? 'Convert your existing vault'
                  : 'Workspace not found'}
          </h1>
        </div>

        <p className="text-sm text-ink-3">{info.error}</p>

        {currentPath && (
          <div className="font-mono text-xs break-all text-ink-2 px-3 py-2 rounded-lg bg-surface-2 border border-hairline">
            {currentPath}
          </div>
        )}

        {/* ── Unstructured: import into a NEW vault via the migrate skill ── */}
        {isUnstructured ? (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-ink-3">
              This folder has notes but isn’t a Squirrel vault (looks like a raw
              Obsidian vault). Convert it: create a Squirrel vault, then import these
              notes into it. Your original folder is never modified.
            </p>

            {/* Step 1 — create the destination vault */}
            <div className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-ink-4">
                Step 1 · Create your Squirrel vault
              </span>
              {vaultCreated ? (
                <p className="text-sm text-emerald-600">✓ Vault created at {newPath}</p>
              ) : (
                <>
                  <input
                    type="text"
                    value={newPath}
                    onChange={(e) => setNewPath(e.target.value)}
                    placeholder="~/squirrel-vault"
                    spellCheck={false}
                    className="w-full px-3 py-2 border border-hairline rounded-lg bg-surface text-sm text-ink placeholder-ink-4 focus:border-accent focus:ring-0 outline-none font-mono"
                  />
                  <button
                    type="button"
                    className="btn btn-primary px-4 py-1.5 text-sm font-semibold disabled:opacity-50 w-fit"
                    disabled={busy || !newPath.trim() || newPath.trim() === currentPath}
                    onClick={() => createNewVault(newPath)}
                  >
                    {busy ? 'Creating…' : 'Create vault'}
                  </button>
                </>
              )}
            </div>

            {/* Step 2 — run the importer */}
            <div className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-wide text-ink-4">
                Step 2 · Import these notes
              </span>
              <p className="text-sm text-ink-3">Run this in your coding agent:</p>
              <div className="flex items-stretch gap-2">
                <code className="flex-1 font-mono text-xs break-all text-ink px-3 py-2 rounded-lg bg-surface-2 border border-hairline select-all">
                  {migrateCmd}
                </code>
                <button
                  type="button"
                  className="btn btn-ghost px-3 text-sm font-semibold"
                  onClick={copyCmd}
                >
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}
            <button
              type="button"
              className="btn btn-primary px-4 py-1.5 text-sm font-semibold disabled:opacity-50"
              disabled={busy}
              onClick={onRecovered}
            >
              Open Squirrel
            </button>
          </div>
        ) : isLegacy ? (
          /* ── Legacy: rename old folders to canonical names in place ── */
          <div className="flex flex-col gap-3">
            <p className="text-sm text-ink-3">
              This workspace uses Squirrel’s old folder names. Rename them to the
              current structure in place — your notes stay where they are, only the
              top-level folders are renamed.
            </p>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <button
              type="button"
              className="btn btn-primary px-4 py-1.5 text-sm font-semibold disabled:opacity-50 w-fit"
              disabled={busy}
              onClick={() => repair()}
            >
              {busy ? 'Repairing…' : 'Repair structure'}
            </button>
          </div>
        ) : isEmpty ? (
          /* ── Empty: one-click scaffold ── */
          <div className="flex flex-col gap-3">
            <p className="text-sm text-ink-3">
              Generate Squirrel’s starter structure (Active Projects, Parking Lot,
              Areas, Archive, Resources) in this folder.
            </p>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <button
              type="button"
              className="btn btn-primary px-4 py-1.5 text-sm font-semibold disabled:opacity-50"
              disabled={busy}
              onClick={() => setup(currentPath)}
            >
              {busy ? 'Generating…' : 'Generate Squirrel structure'}
            </button>
          </div>
        ) : (
          /* ── Missing / no vault: choose a folder ── */
          <div className="flex flex-col gap-3">
            <label className="text-sm text-ink-3 flex flex-col gap-1.5">
              Set up your workspace at this folder (it’s created if missing):
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="~/squirrel-vault"
                spellCheck={false}
                className="w-full px-3 py-2 border border-hairline rounded-lg bg-surface text-sm text-ink placeholder-ink-4 focus:border-accent focus:ring-0 outline-none font-mono"
              />
            </label>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <button
              type="button"
              className="btn btn-primary px-4 py-1.5 text-sm font-semibold disabled:opacity-50"
              disabled={busy || !path.trim()}
              onClick={() => setup(path)}
            >
              {busy ? 'Setting up…' : 'Set up workspace'}
            </button>
            <p className="text-xs text-ink-4">
              Converting an existing Obsidian vault? Create a fresh vault here, then
              run <code className="font-mono">/sq-migrate-vault &lt;your-vault&gt;</code> to import it.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
