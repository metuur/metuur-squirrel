import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useDeepLink } from "./useDeepLink";

type EventHandler = (event: { payload: { projectId: string; taskId: string | null } }) => void;

const mockUnlisten = vi.fn();
let capturedHandler: EventHandler | null = null;

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn((_eventName: string, handler: EventHandler) => {
    capturedHandler = handler;
    return Promise.resolve(mockUnlisten);
  }),
}));

describe("useDeepLink", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedHandler = null;
  });

  it("increments key on every event, even for identical payloads", async () => {
    const { result } = renderHook(() => useDeepLink());

    // Wait for listen() promise to resolve and unlisten to be registered
    await act(async () => {});

    const payload = { projectId: "FOO", taskId: null };

    await act(async () => {
      capturedHandler!({ payload });
    });
    const key1 = result.current?.key;

    await act(async () => {
      capturedHandler!({ payload });
    });
    const key2 = result.current?.key;

    expect(key1).toBeDefined();
    expect(key2).toBeDefined();
    expect(key2).toBeGreaterThan(key1!);
  });

  it("calls the unlisten callback exactly once on unmount", async () => {
    const { unmount } = renderHook(() => useDeepLink());

    // Wait for listen() promise to resolve
    await act(async () => {});

    unmount();

    expect(mockUnlisten).toHaveBeenCalledTimes(1);
  });
});
