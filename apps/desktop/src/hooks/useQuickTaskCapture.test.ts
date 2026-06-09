// Tests for useQuickTaskCapture — capture-from-anywhere flow.
// EARS R-1.1 (event opens modal), R-1.3 (empty rejected),
// R-2.4 (409 keeps modal open with stack-full message).

import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

type EventHandler = () => void;

const mockUnlisten = vi.fn();
let capturedHandler: EventHandler | null = null;

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn((_eventName: string, handler: EventHandler) => {
    capturedHandler = handler;
    return new Promise<typeof mockUnlisten>((resolve) => {
      queueMicrotask(() => resolve(mockUnlisten));
    });
  }),
}));

const { ApiError, mockCreate } = vi.hoisted(() => {
  class ApiError extends Error {
    status: number;
    data: unknown;
    constructor(status: number, message: string, data?: unknown) {
      super(message);
      this.status = status;
      this.data = data;
    }
  }
  return { ApiError, mockCreate: vi.fn() };
});
vi.mock("../api/client", () => ({
  ApiError,
  api: { quickTaskCreate: (...args: unknown[]) => mockCreate(...args) },
}));

import { useQuickTaskCapture } from "./useQuickTaskCapture";

describe("useQuickTaskCapture", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedHandler = null;
  });

  it("opens the modal when the capture event fires (R-1.1)", async () => {
    const { result } = renderHook(() => useQuickTaskCapture());
    await act(async () => {});
    expect(result.current.open).toBe(false);
    act(() => capturedHandler?.());
    expect(result.current.open).toBe(true);
  });

  it("rejects empty text without calling the API (R-1.3)", async () => {
    const { result } = renderHook(() => useQuickTaskCapture());
    await act(async () => {});
    let ok = true;
    await act(async () => {
      ok = await result.current.submit("   ");
    });
    expect(ok).toBe(false);
    expect(mockCreate).not.toHaveBeenCalled();
    expect(result.current.error).toBeTruthy();
  });

  it("closes and fires onCreated on success", async () => {
    mockCreate.mockResolvedValue({ success: true, id: "QT-001" });
    const onCreated = vi.fn();
    const { result } = renderHook(() => useQuickTaskCapture(onCreated));
    await act(async () => {});
    act(() => result.current.openCapture());
    expect(result.current.open).toBe(true);

    let ok = false;
    await act(async () => {
      ok = await result.current.submit("Reply to Ana");
    });
    expect(ok).toBe(true);
    expect(mockCreate).toHaveBeenCalledWith("Reply to Ana");
    expect(result.current.open).toBe(false);
    expect(onCreated).toHaveBeenCalledTimes(1);
  });

  it("keeps the modal open with a stack-full message on 409 (R-2.4)", async () => {
    mockCreate.mockRejectedValue(
      new ApiError(409, "QUICK_TASK_LIMIT_REACHED", { error: "QUICK_TASK_LIMIT_REACHED" }),
    );
    const { result } = renderHook(() => useQuickTaskCapture());
    await act(async () => {});
    act(() => result.current.openCapture());

    let ok = true;
    await act(async () => {
      ok = await result.current.submit("Sixth task");
    });
    expect(ok).toBe(false);
    expect(result.current.open).toBe(true); // stays open
    expect(result.current.error).toMatch(/full/i);
  });

  it("tears down the listener on unmount", async () => {
    const { unmount } = renderHook(() => useQuickTaskCapture());
    await act(async () => {});
    unmount();
    expect(mockUnlisten).toHaveBeenCalledTimes(1);
  });
});
