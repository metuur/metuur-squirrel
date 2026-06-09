// Tests for QuickTaskWidget — render, ordering, controls, cap-disabled Add.
// EARS R-5.3 (stack render + controls), R-5.4 (Add disabled at cap), R-3.4 (snooze options).

import { render, act, fireEvent, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { QuickTasksPayload } from "../api/client";

const { mocks } = vi.hoisted(() => ({
  mocks: {
    quickTasks: vi.fn(),
    complete: vi.fn().mockResolvedValue({ success: true }),
    remove: vi.fn().mockResolvedValue({ success: true }),
    snooze: vi.fn().mockResolvedValue({ success: true, snoozed_until: "x" }),
  },
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(() => Promise.resolve(() => {})),
}));

vi.mock("../api/client", () => ({
  api: {
    quickTasks: () => mocks.quickTasks(),
    quickTaskComplete: (id: string) => mocks.complete(id),
    quickTaskDelete: (id: string) => mocks.remove(id),
    quickTaskSnooze: (id: string, until: string) => mocks.snooze(id, until),
  },
}));

import { QuickTaskWidget } from "./QuickTaskWidget";

function payload(over: Partial<QuickTasksPayload> = {}): QuickTasksPayload {
  return {
    active: [
      { id: "QT-001", text: "Oldest task" },
      { id: "QT-002", text: "Newer task" },
    ],
    snoozed: [],
    active_count: 2,
    snoozed_count: 0,
    limit: 5,
    return_blocked: false,
    ...over,
  };
}

async function renderWidget(over: Partial<QuickTasksPayload> = {}, onAdd = vi.fn()) {
  mocks.quickTasks.mockResolvedValue(payload(over));
  let utils!: ReturnType<typeof render>;
  await act(async () => {
    utils = render(
      <QuickTaskWidget online={true} refreshSignal={0} onAdd={onAdd} />,
    );
  });
  return utils;
}

describe("QuickTaskWidget", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the active stack oldest-first (R-5.3)", async () => {
    await renderWidget();
    const titles = screen.getAllByText(/task$/i).map((el) => el.textContent);
    expect(titles).toEqual(["Oldest task", "Newer task"]);
  });

  it("completes a task via the API (R-5.3)", async () => {
    await renderWidget();
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Complete QT-001"));
    });
    expect(mocks.complete).toHaveBeenCalledWith("QT-001");
  });

  it("deletes a task via the API (R-5.3)", async () => {
    await renderWidget();
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Delete QT-002"));
    });
    expect(mocks.remove).toHaveBeenCalledWith("QT-002");
  });

  it("snoozes with the chosen duration (R-3.4)", async () => {
    await renderWidget();
    await act(async () => {
      fireEvent.click(screen.getByLabelText("Snooze QT-001"));
    });
    await act(async () => {
      fireEvent.click(screen.getByText("Next block"));
    });
    expect(mocks.snooze).toHaveBeenCalledWith("QT-001", "next_block");
  });

  it("disables Add when the stack is at the cap (R-5.4)", async () => {
    await renderWidget({ active_count: 5, limit: 5 });
    const addBtn = screen.getByRole("button", { name: "+ Add" }) as HTMLButtonElement;
    expect(addBtn.disabled).toBe(true);
  });

  it("enables Add and calls onAdd below the cap", async () => {
    const onAdd = vi.fn();
    await renderWidget({ active_count: 2 }, onAdd);
    const addBtn = screen.getByRole("button", { name: "+ Add" }) as HTMLButtonElement;
    expect(addBtn.disabled).toBe(false);
    fireEvent.click(addBtn);
    expect(onAdd).toHaveBeenCalledTimes(1);
  });

  it("shows the return-blocked banner when set (R-5.5)", async () => {
    await renderWidget({ return_blocked: true });
    expect(screen.getByText(/clear a slot/i)).toBeTruthy();
  });
});
