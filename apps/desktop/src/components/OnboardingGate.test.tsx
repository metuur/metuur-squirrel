import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OnboardingGate } from "./OnboardingGate";

// Story in-app-vault-onboarding 4.3 — R-1.1, R-1.2, R-1.3, R-1.6.

vi.mock("../lib/onboarding", () => ({ isOnboardingDone: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn() }));
vi.mock("./OnboardingWizard", () => ({
  OnboardingWizard: () => <div data-testid="wizard">wizard</div>,
}));

import { isOnboardingDone } from "../lib/onboarding";
import { listen } from "@tauri-apps/api/event";

const mockDone = vi.mocked(isOnboardingDone);
const mockListen = vi.mocked(listen);

describe("OnboardingGate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // default: handshake listener never fires
    mockListen.mockResolvedValue(() => {});
  });

  it("shows the wizard when onboarding is not done (R-1.1)", async () => {
    mockDone.mockResolvedValue(false);
    render(<OnboardingGate />);
    expect(await screen.findByTestId("wizard")).toBeTruthy();
  });

  it("renders nothing when onboarding is done (R-1.2)", async () => {
    mockDone.mockResolvedValue(true);
    const { container } = render(<OnboardingGate />);
    await waitFor(() => expect(mockDone).toHaveBeenCalled());
    expect(screen.queryByTestId("wizard")).toBeNull();
    expect(container.firstChild).toBeNull();
  });

  it("shows the wizard when the flag cannot be read (R-1.6)", async () => {
    mockDone.mockRejectedValue(new Error("store unreadable"));
    render(<OnboardingGate />);
    expect(await screen.findByTestId("wizard")).toBeTruthy();
  });

  it("suppresses the wizard while a handshake refusal is active (R-1.3)", async () => {
    mockDone.mockResolvedValue(false);
    // Capture the handshake-refused callback and fire it.
    let fire: (() => void) | null = null;
    mockListen.mockImplementation((_event, cb) => {
      fire = cb as unknown as () => void;
      return Promise.resolve(() => {});
    });
    render(<OnboardingGate />);
    // Wizard initially shows (not done, no handshake yet)
    await screen.findByTestId("wizard");
    // Handshake fires → wizard must disappear
    fire!();
    await waitFor(() => expect(screen.queryByTestId("wizard")).toBeNull());
  });
});
