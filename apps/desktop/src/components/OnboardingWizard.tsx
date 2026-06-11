// First-run onboarding wizard (in-app-vault-onboarding Unit 2/3/4).
// Steps: welcome → obsidian → vault → done. Config only: checks Obsidian,
// picks/creates a vault folder, and writes it to ~/.squirrel/config.toml via
// the backend. Binaries/launchd/agent-pack remain the installer's job.
// The final "done" step also surfaces recommended OS setup: notification
// permission and launch-at-login.

import { useEffect, useState } from "react";
import { getVersion } from "@tauri-apps/api/app";
import { openUrl } from "@tauri-apps/plugin-opener";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { api, openWebUrl, type ObsidianStatus } from "../api/client";
import { markOnboardingDone } from "../lib/onboarding";
import { ackSetupNudge } from "../lib/setupNudge";
import { RecommendedSetup } from "./RecommendedSetup";

const OBSIDIAN_DOWNLOAD = "https://obsidian.md/download";
const DEFAULT_VAULT = "~/squirrel-vault";

type Step = "welcome" | "obsidian" | "vault" | "done";
type VaultMode = "create" | "existing";

export function OnboardingWizard({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState<Step>("welcome");

  // ── App version (read at runtime via Tauri, mirrors AppCredit) ──
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getVersion()
      .then((v) => {
        if (alive) setVersion(v);
      })
      .catch(() => {
        // Non-Tauri host (e.g. plain browser dev) or denied — just omit it.
      });
    return () => {
      alive = false;
    };
  }, []);

  // ── Obsidian step state ──
  const [obsidian, setObsidian] = useState<ObsidianStatus | null>(null);
  const [obsidianLoading, setObsidianLoading] = useState(false);
  // Distinct from a definitive {installed:false}: the probe request itself
  // failed (backend still booting, auth, network), so we genuinely don't know.
  const [obsidianError, setObsidianError] = useState(false);

  const checkObsidian = () => {
    setObsidianLoading(true);
    setObsidianError(false);
    api
      .obsidianStatus()
      .then(setObsidian)
      // A failed request is NOT proof that Obsidian is missing — the backend
      // sidecar may still be starting up. Surface a "couldn't check" state with
      // Re-check instead of a misleading "Obsidian not found".
      .catch(() => setObsidianError(true))
      .finally(() => setObsidianLoading(false));
  };

  useEffect(() => {
    if (step === "obsidian" && obsidian === null && !obsidianLoading) checkObsidian();
  }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Vault step state ──
  const [mode, setMode] = useState<VaultMode>("create");
  const [createPath, setCreatePath] = useState(DEFAULT_VAULT);
  const [existingPath, setExistingPath] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedName, setSavedName] = useState<string>("");
  const [savedPath, setSavedPath] = useState<string>("");

  const chosenPath = mode === "create" ? createPath.trim() : (existingPath ?? "");

  const pickFolder = async () => {
    const picked = await openDialog({ directory: true });
    if (typeof picked === "string") setExistingPath(picked);
  };

  const saveVault = async () => {
    if (!chosenPath) return;
    setSaving(true);
    setError(null);
    try {
      const res = await api.setVaultConfig({
        path: chosenPath,
        create: mode === "create",
      });
      setSavedName(res.name);
      setSavedPath(res.path);
      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the vault. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const finish = async () => {
    await markOnboardingDone();
    // Stamp the current version as setup-acknowledged so the post-update nudge
    // doesn't immediately re-show the same card right after onboarding.
    await ackSetupNudge();
    onComplete();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Squirrel setup"
      className="fixed inset-0 z-50 flex items-center justify-center bg-surface"
    >
      <div className="w-full max-w-md px-6 py-7 flex flex-col gap-5">
        <header className="flex items-center gap-3">
          <img src="/squirrel-logo.svg" alt="" aria-hidden className="h-8 w-8" />
          <span className="title text-[16px]">Squirrel</span>
        </header>

        {step === "welcome" && (
          <section className="flex flex-col gap-4">
            <h1 className="title text-[20px]">Welcome to Squirrel</h1>
            {version && <p className="text-ink-4 tabular text-[11px]">Version {version}</p>}
            <p className="text-ink-3 text-[13px]">
              Let’s get you set up — no Terminal required. We’ll check for Obsidian
              and point Squirrel at your vault.
            </p>
            <div className="flex justify-end">
              <button type="button" className="btn" onClick={() => setStep("obsidian")}>
                Get started →
              </button>
            </div>
          </section>
        )}

        {step === "obsidian" && (
          <section className="flex flex-col gap-4">
            <h1 className="title text-[18px]">Checking for Obsidian…</h1>
            {obsidianLoading && <p className="text-ink-3 text-[13px]">Checking…</p>}
            {!obsidianLoading && obsidianError && (
              <div className="flex flex-col gap-2 text-[13px]">
                <span>⚠ Couldn’t reach Squirrel’s backend to check for Obsidian — it may still be starting up.</span>
                <div className="flex gap-2">
                  <button type="button" className="btn" onClick={checkObsidian}>
                    Re-check
                  </button>
                  <button type="button" className="btn" onClick={() => void openWebUrl("/guide")}>
                    Open guide
                  </button>
                </div>
              </div>
            )}
            {!obsidianLoading && !obsidianError && obsidian?.installed && (
              <div className="text-[13px]">
                ✓ Obsidian found
                <div className="text-ink-4 tabular truncate">{obsidian.path}</div>
              </div>
            )}
            {!obsidianLoading && !obsidianError && obsidian && !obsidian.installed && (
              <div className="flex flex-col gap-2 text-[13px]">
                <span>⚠ Obsidian not found. Squirrel works without it, but the vault is best viewed in Obsidian.</span>
                <div className="flex gap-2">
                  <button type="button" className="btn" onClick={() => void openUrl(OBSIDIAN_DOWNLOAD)}>
                    Download Obsidian
                  </button>
                  <button type="button" className="btn" onClick={checkObsidian}>
                    Re-check
                  </button>
                </div>
              </div>
            )}
            <div className="flex justify-between">
              <button type="button" className="btn" onClick={() => setStep("welcome")}>
                ← Back
              </button>
              <button type="button" className="btn" onClick={() => setStep("vault")}>
                Continue →
              </button>
            </div>
          </section>
        )}

        {step === "vault" && (
          <section className="flex flex-col gap-4">
            <h1 className="title text-[18px]">Where should your vault live?</h1>

            <label className="flex items-start gap-2 text-[13px]">
              <input
                type="radio"
                name="vault-mode"
                checked={mode === "create"}
                onChange={() => setMode("create")}
              />
              <span className="flex-1">
                Create a new vault
                <input
                  type="text"
                  value={createPath}
                  onChange={(e) => setCreatePath(e.target.value)}
                  onFocus={() => setMode("create")}
                  aria-label="New vault path"
                  className="mt-1 w-full px-2 py-1 border border-hairline rounded bg-surface-2"
                />
              </span>
            </label>

            <label className="flex items-start gap-2 text-[13px]">
              <input
                type="radio"
                name="vault-mode"
                checked={mode === "existing"}
                onChange={() => setMode("existing")}
              />
              <span className="flex-1">
                Use an existing folder
                <div className="mt-1 flex gap-2">
                  <span className="flex-1 px-2 py-1 border border-hairline rounded bg-surface-2 tabular truncate">
                    {existingPath ?? "No folder chosen"}
                  </span>
                  <button
                    type="button"
                    className="btn"
                    onClick={() => {
                      setMode("existing");
                      void pickFolder();
                    }}
                  >
                    Choose…
                  </button>
                </div>
              </span>
            </label>

            {error && (
              <div className="flex flex-col gap-1">
                <p className="text-[13px]" style={{ color: "var(--danger, #c0392b)" }}>{error}</p>
                <button
                  type="button"
                  className="self-start text-[12px] underline text-ink-3 hover:text-ink-1"
                  onClick={() => void openWebUrl("/guide")}
                >
                  Open the guide for help
                </button>
              </div>
            )}

            <div className="flex justify-between">
              <button type="button" className="btn" onClick={() => setStep("obsidian")}>
                ← Back
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => void saveVault()}
                disabled={!chosenPath || saving}
              >
                {saving ? "Installing…" : "Install →"}
              </button>
            </div>
          </section>
        )}

        {step === "done" && (
          <section className="flex flex-col gap-4">
            <h1 className="title text-[20px]">✓ You’re all set</h1>
            <div className="text-[13px]">
              <div>Vault: <span className="tabular">{savedPath}</span></div>
              <div className="text-ink-4">{savedName}</div>
            </div>

            <div className="flex flex-col gap-1 text-[13px]">
              <span>Already have notes in Obsidian? Ask your coding agent to migrate them:</span>
              <code className="w-fit rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[12px] text-ink-1 select-all">
                /sq-migrate-vault ~/path/to/your-obsidian-vault
              </code>
              <span className="text-ink-4 text-[11px]">
                Shows a dry-run plan first — your original vault is never modified.
              </span>
            </div>

            <RecommendedSetup />

            <p className="text-[13px] text-ink-3">
              New to Squirrel?{" "}
              <button
                type="button"
                className="underline hover:text-ink-1"
                onClick={() => void openWebUrl("/guide")}
              >
                Open the guide
              </button>{" "}
              to learn how it works.
            </p>

            <div className="flex justify-end">
              <button type="button" className="btn" onClick={() => void finish()}>
                Launch Squirrel
              </button>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
