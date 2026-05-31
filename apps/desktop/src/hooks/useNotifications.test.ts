// Regression guard for EARS R-5.2 — the `squirrel:notif-updated` listener
// must tear down on App unmount. The supervisor work in 7fbb297 emits the
// event from Rust; if the React subscriber leaked, every notification would
// grow memory and re-fetch counts would compound across reloads.

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

type EventHandler = (event: { payload: number }) => void;

const mockUnlisten = vi.fn();
let capturedHandler: EventHandler | null = null;
let listenResolve: ((fn: typeof mockUnlisten) => void) | null = null;

vi.mock("@tauri-apps/api/event", () => ({
  // Capture the handler so tests can fire synthetic events; expose a
  // promise that resolves to the unlisten fn so tests can also exercise
  // the unmount-before-listen-resolves race.
  listen: vi.fn((_eventName: string, handler: EventHandler) => {
    capturedHandler = handler;
    return new Promise<typeof mockUnlisten>((resolve) => {
      listenResolve = resolve;
      // By default, resolve synchronously in a microtask so most tests
      // don't need to manually nudge the race.
      queueMicrotask(() => resolve(mockUnlisten));
    });
  }),
}));

const mockNotifications = vi.fn();
vi.mock("../api/client", () => ({
  api: {
    notifications: (...args: unknown[]) => mockNotifications(...args),
    notificationsMarkAllRead: vi.fn().mockResolvedValue({ updated: 0 }),
    notificationDismiss: vi.fn().mockResolvedValue({ success: true }),
  },
}));

import { useNotifications } from "./useNotifications";

describe("useNotifications listener lifecycle (EARS R-5.2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedHandler = null;
    listenResolve = null;
    mockNotifications.mockResolvedValue({ items: [], unread_count: 0 });
  });

  it("calls the unlisten callback exactly once on unmount", async () => {
    const { unmount } = renderHook(() => useNotifications());
    // Flush the listen() promise so unlisten is registered.
    await act(async () => {});
    unmount();
    expect(mockUnlisten).toHaveBeenCalledTimes(1);
  });

  it("does not double-unlisten when React re-runs the effect", async () => {
    const { unmount, rerender } = renderHook(() => useNotifications());
    await act(async () => {});
    rerender();
    await act(async () => {});
    unmount();
    // Strict-mode-like rerender doesn't re-invoke the effect (empty deps),
    // so only one unlisten call is expected for the single mount.
    expect(mockUnlisten).toHaveBeenCalledTimes(1);
  });

  it("calls unlisten if the component unmounts before listen() resolves", async () => {
    // Override the default microtask resolution — leave the promise pending
    // until we explicitly resolve it post-unmount.
    const eventModule = await import("@tauri-apps/api/event");
    (eventModule.listen as ReturnType<typeof vi.fn>).mockImplementationOnce(
      (_eventName: string, handler: EventHandler) => {
        capturedHandler = handler;
        return new Promise<typeof mockUnlisten>((resolve) => {
          listenResolve = resolve;
          // Intentionally do not resolve in a microtask — wait for the test.
        });
      },
    );

    const { unmount } = renderHook(() => useNotifications());
    unmount();

    // The listen() promise resolves AFTER unmount; the hook should
    // immediately invoke unlisten when that happens.
    await act(async () => {
      listenResolve!(mockUnlisten);
    });

    expect(mockUnlisten).toHaveBeenCalledTimes(1);
  });

  it("refetches notifications when the event fires", async () => {
    renderHook(() => useNotifications());
    // Initial fetch on mount + listen() resolution.
    await act(async () => {});
    const initialCalls = mockNotifications.mock.calls.length;
    expect(initialCalls).toBeGreaterThan(0);

    // Fire a synthetic event — should trigger a refetch.
    await act(async () => {
      capturedHandler!({ payload: 3 });
    });
    expect(mockNotifications.mock.calls.length).toBeGreaterThan(initialCalls);
  });
});
