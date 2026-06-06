import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
import { OnboardingWizard } from "./OnboardingWizard";

// Story in-app-vault-onboarding 4.2 — R-2.4/2.6, R-3.1/3.3/3.9, R-1.4.

vi.mock("@tauri-apps/plugin-opener", () => ({ openUrl: vi.fn() }));
vi.mock("@tauri-apps/plugin-dialog", () => ({ open: vi.fn() }));
vi.mock("../lib/onboarding", () => ({ markOnboardingDone: vi.fn().mockResolvedValue(undefined) }));
vi.mock("../api/client", () => ({
  api: { obsidianStatus: vi.fn(), setVaultConfig: vi.fn() },
}));

import { openUrl } from "@tauri-apps/plugin-opener";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { markOnboardingDone } from "../lib/onboarding";
import { api } from "../api/client";

const mockOpenUrl = vi.mocked(openUrl);
const mockDialog = vi.mocked(openDialog);
const mockMarkDone = vi.mocked(markOnboardingDone);
const mockObsidian = vi.mocked(api.obsidianStatus);
const mockSetVault = vi.mocked(api.setVaultConfig);

async function gotoVaultStep() {
  await userEvent.click(screen.getByRole("button", { name: /Get started/ }));
  // obsidian step auto-checks; wait for it to resolve, then continue
  await screen.findByRole("button", { name: /Continue/ });
  await userEvent.click(screen.getByRole("button", { name: /Continue/ }));
}

describe("OnboardingWizard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the download link + re-check when Obsidian is not installed (R-2.4/R-2.6)", async () => {
    mockObsidian.mockResolvedValue({ installed: false, path: null });
    render(<OnboardingWizard onComplete={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: /Get started/ }));

    const download = await screen.findByRole("button", { name: /Download Obsidian/ });
    await userEvent.click(download);
    expect(mockOpenUrl).toHaveBeenCalledWith("https://obsidian.md/download");
    expect(screen.getByRole("button", { name: /Re-check/ })).toBeTruthy();
  });

  it("saves the vault and advances to done, marking onboarding complete (R-3.3/R-1.4)", async () => {
    mockObsidian.mockResolvedValue({ installed: true, path: "/Applications/Obsidian.app" });
    mockSetVault.mockResolvedValue({ name: "personal", path: "/Users/x/squirrel-vault", default: true });
    const onComplete = vi.fn();
    render(<OnboardingWizard onComplete={onComplete} />);
    await gotoVaultStep();

    await userEvent.click(screen.getByRole("button", { name: /Install/ }));
    await waitFor(() =>
      expect(mockSetVault).toHaveBeenCalledWith({ path: "~/squirrel-vault", create: true }),
    );
    const launch = await screen.findByRole("button", { name: /Launch Squirrel/ });
    await userEvent.click(launch);
    expect(mockMarkDone).toHaveBeenCalled();
    expect(onComplete).toHaveBeenCalled();
  });

  it("keeps the user on the vault step when the backend rejects the path (R-3.9)", async () => {
    mockObsidian.mockResolvedValue({ installed: true, path: "/x" });
    mockSetVault.mockRejectedValue(new Error("Vault path must be inside your home directory."));
    render(<OnboardingWizard onComplete={vi.fn()} />);
    await gotoVaultStep();

    await userEvent.click(screen.getByRole("button", { name: /Install/ }));
    expect(await screen.findByText(/inside your home directory/)).toBeTruthy();
    // still on the vault step
    expect(screen.getByRole("button", { name: /Install/ })).toBeTruthy();
    expect(mockMarkDone).not.toHaveBeenCalled();
  });

  it("opens a native folder picker for the existing-folder option (R-3.1)", async () => {
    mockObsidian.mockResolvedValue({ installed: true, path: "/x" });
    mockDialog.mockResolvedValue("/Users/x/Documents/myvault");
    mockSetVault.mockResolvedValue({ name: "personal", path: "/Users/x/Documents/myvault", default: true });
    render(<OnboardingWizard onComplete={vi.fn()} />);
    await gotoVaultStep();

    await userEvent.click(screen.getByRole("button", { name: /Choose…/ }));
    await waitFor(() => expect(mockDialog).toHaveBeenCalledWith({ directory: true }));
    await screen.findByText("/Users/x/Documents/myvault");
    await userEvent.click(screen.getByRole("button", { name: /Install/ }));
    await waitFor(() =>
      expect(mockSetVault).toHaveBeenCalledWith({ path: "/Users/x/Documents/myvault", create: false }),
    );
  });
});
