import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";
import { OpenVaultButton } from "./OpenVaultButton";

// Story in-app-vault-onboarding 5.1 — R-4.1, R-4.3, R-4.4.

vi.mock("@tauri-apps/plugin-opener", () => ({ openUrl: vi.fn() }));
vi.mock("../api/client", () => ({ api: { me: vi.fn() } }));

import { openUrl } from "@tauri-apps/plugin-opener";
import { api } from "../api/client";

const mockOpenUrl = vi.mocked(openUrl);
const mockMe = vi.mocked(api.me);

function meWith(name: string) {
  return {
    active_workspace: { name, path: "/x", default: true },
    workspaces: [],
    multi_vault: false,
    theme: "auto",
    version: "0",
  } as Awaited<ReturnType<typeof api.me>>;
}

describe("OpenVaultButton", () => {
  beforeEach(() => {
    mockOpenUrl.mockReset();
    mockMe.mockReset();
  });

  it("opens the configured vault name from /api/me, not a hardcoded one (R-4.1)", async () => {
    mockMe.mockResolvedValue(meWith("mine"));
    render(<OpenVaultButton />);
    const btn = await screen.findByRole("button", { name: /Open Vault/ });
    await waitFor(() => expect((btn as HTMLButtonElement).disabled).toBe(false));
    await userEvent.click(btn);
    expect(mockOpenUrl).toHaveBeenCalledWith("obsidian://open?vault=mine");
  });

  it("disables the button when /api/me 503s with no vault (R-4.3/R-4.4)", async () => {
    mockMe.mockRejectedValue(Object.assign(new Error("no vault"), { status: 503 }));
    render(<OpenVaultButton />);
    const btn = await screen.findByRole("button", { name: /Open Vault/ });
    await waitFor(() => expect((btn as HTMLButtonElement).disabled).toBe(true));
    await userEvent.click(btn);
    expect(mockOpenUrl).not.toHaveBeenCalled();
  });
});
