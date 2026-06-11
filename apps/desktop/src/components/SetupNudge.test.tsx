import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import userEvent from "@testing-library/user-event";

vi.mock("@tauri-apps/api/app", () => ({ getVersion: vi.fn().mockResolvedValue("9.9.9") }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn().mockResolvedValue(() => {}) }));
vi.mock("../lib/onboarding", () => ({ isOnboardingDone: vi.fn() }));
vi.mock("../lib/setupNudge", () => ({
  shouldShowSetupNudge: vi.fn(),
  ackSetupNudge: vi.fn().mockResolvedValue(undefined),
}));
vi.mock("./RecommendedSetup", () => ({
  RecommendedSetup: () => <div data-testid="recommended-setup" />,
}));

import { SetupNudge } from "./SetupNudge";
import { isOnboardingDone } from "../lib/onboarding";
import { shouldShowSetupNudge, ackSetupNudge } from "../lib/setupNudge";

const mockDone = vi.mocked(isOnboardingDone);
const mockShould = vi.mocked(shouldShowSetupNudge);
const mockAck = vi.mocked(ackSetupNudge);

describe("SetupNudge", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows after an update (onboarding done + version changed)", async () => {
    mockDone.mockResolvedValue(true);
    mockShould.mockResolvedValue(true);
    render(<SetupNudge />);
    expect(await screen.findByText(/up to date/i)).toBeTruthy();
    expect(screen.getByTestId("recommended-setup")).toBeTruthy();
  });

  it("stays hidden when the version is unchanged", async () => {
    mockDone.mockResolvedValue(true);
    mockShould.mockResolvedValue(false);
    render(<SetupNudge />);
    await waitFor(() => expect(mockShould).toHaveBeenCalled());
    expect(screen.queryByText(/up to date/i)).toBeNull();
  });

  it("stays hidden until onboarding is complete (first run uses the wizard)", async () => {
    mockDone.mockResolvedValue(false);
    mockShould.mockResolvedValue(true);
    render(<SetupNudge />);
    await waitFor(() => expect(mockDone).toHaveBeenCalled());
    expect(screen.queryByText(/up to date/i)).toBeNull();
  });

  it("acknowledges the version on dismiss and hides", async () => {
    mockDone.mockResolvedValue(true);
    mockShould.mockResolvedValue(true);
    render(<SetupNudge />);
    const got = await screen.findByRole("button", { name: /Got it/ });
    await userEvent.click(got);
    expect(mockAck).toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByText(/up to date/i)).toBeNull());
  });
});
