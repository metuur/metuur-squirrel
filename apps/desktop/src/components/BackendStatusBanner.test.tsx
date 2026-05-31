import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import { BackendStatusBanner } from "./BackendStatusBanner";
import type { BackendStatus } from "../hooks/useBackend";

vi.mock("@tauri-apps/plugin-process", () => ({
  relaunch: vi.fn(),
}));

import { relaunch } from "@tauri-apps/plugin-process";
const mockRelaunch = vi.mocked(relaunch);

function offline(): BackendStatus {
  return { online: false, lastOnlineAt: null, lastError: "ECONNREFUSED" };
}
function online(): BackendStatus {
  return { online: true, lastOnlineAt: Date.now(), lastError: null };
}

describe("BackendStatusBanner", () => {
  beforeEach(() => {
    mockRelaunch.mockReset();
  });

  afterEach(() => {
    // Clean up the Tauri context marker between tests
    delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__;
  });

  it("renders nothing when backend is online", () => {
    const { container } = render(<BackendStatusBanner status={online()} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows user-friendly copy when offline, not the dev-facing make command", () => {
    render(<BackendStatusBanner status={offline()} />);
    expect(
      screen.getByText(/Backend offline\. Trying to reconnect\. If this persists, restart Squirrel\./)
    ).toBeTruthy();
    // Guard against the prior dev-facing wording reappearing.
    expect(screen.queryByText(/make backend-start/)).toBeNull();
    expect(screen.queryByText(/monorepo/)).toBeNull();
  });

  it("renders Restart button only inside the Tauri webview", () => {
    // Browser-only dev context — no __TAURI_INTERNALS__
    const { rerender, container } = render(<BackendStatusBanner status={offline()} />);
    expect(container.querySelector("button")).toBeNull();

    // Flip to a Tauri context and re-render
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {};
    rerender(<BackendStatusBanner status={offline()} />);
    const button = screen.getByRole("button", { name: /Restart/ });
    expect(button).toBeTruthy();
  });

  it("calls relaunch() when the Restart button is clicked", async () => {
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {};
    // relaunch() normally terminates the process; pretend it just hangs so
    // our finally-branch error path isn't exercised here.
    mockRelaunch.mockImplementation(() => new Promise(() => {}));

    render(<BackendStatusBanner status={offline()} />);
    const button = screen.getByRole("button", { name: /Restart/ });
    await act(async () => {
      await userEvent.click(button);
    });
    expect(mockRelaunch).toHaveBeenCalledOnce();
  });

  it("resets the button state when relaunch() fails", async () => {
    (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {};
    mockRelaunch.mockRejectedValue(new Error("denied"));

    render(<BackendStatusBanner status={offline()} />);
    const button = screen.getByRole("button", { name: /Restart/ });
    await act(async () => {
      await userEvent.click(button);
    });
    // After the failed promise settles the button should be clickable again.
    const buttonAfter = screen.getByRole("button", { name: /Restart/ });
    expect((buttonAfter as HTMLButtonElement).disabled).toBe(false);
  });
});
