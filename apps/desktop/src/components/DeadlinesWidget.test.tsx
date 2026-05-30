import { render, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { DeadlinesWidget } from "./DeadlinesWidget";
import type { HomeState } from "../hooks/useHome";
import type { ProjectListItem, PressingItem } from "../api/client";
import type { DeepLinkTarget } from "../hooks/useDeepLink";

vi.mock("@tauri-apps/plugin-opener", () => ({ openUrl: vi.fn() }));
vi.mock("./DeadlinesWidget.module.css", () => ({ default: {} }));

// jsdom does not implement scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

const scrollIntoView = vi.mocked(Element.prototype.scrollIntoView);

const PROJECTS: ProjectListItem[] = [
  { slug: "P1", title: "Project One" },
  { slug: "P2", title: "Project Two" },
];

function makeItem(id: string, projectSlug: string): PressingItem {
  return {
    id: `${projectSlug}-${id}`,
    title: `Task ${id}`,
    deadline: "2026-06-01",
    urgency: "high",
    urgency_label: "urgent",
    is_overdue: false,
    hours_left: 10,
    days_overdue: null,
  };
}

const ITEMS: PressingItem[] = [
  makeItem("T1", "P1"),
  makeItem("T2", "P1"),
  makeItem("T3", "P2"),
];

function makeHome(items: PressingItem[]): HomeState {
  return {
    data: {
      focus: null,
      pressing: items,
      projects: PROJECTS,
      manual_focus: { today: null, today_pm: null, week: null },
      parakeet: "",
    },
    loading: false,
    error: null,
    lastFetchedAt: Date.now(),
  };
}

function renderWidget(scrollTarget?: DeepLinkTarget | null) {
  return render(
    <DeadlinesWidget
      home={makeHome(ITEMS)}
      online={true}
      projects={PROJECTS}
      onAddNote={vi.fn()}
      scrollTarget={scrollTarget}
    />,
  );
}

describe("DeadlinesWidget scroll-and-highlight (R-9.3, R-9.4)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    scrollIntoView.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("(a) taskId match → scrollIntoView on that card + data-highlight='on'", () => {
    // ITEMS[1] has id "P1-T2", projectSlug "P1"
    const target: DeepLinkTarget = { projectId: "P1", taskId: "P1-T2", key: 1 };
    renderWidget(target);

    const el = document.getElementById("deadline-card-P1-T2")!;
    expect(el).toBeTruthy();
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(scrollIntoView).toHaveBeenCalledWith({ block: "center", behavior: "smooth" });
    expect(el.getAttribute("data-highlight")).toBe("on");
  });

  it("(b) projectId-only (taskId null) → first card with matching data-project-id", () => {
    const target: DeepLinkTarget = { projectId: "P2", taskId: null, key: 1 };
    renderWidget(target);

    // ITEMS[2] is the only P2 card
    const el = document.querySelector('[data-project-id="P2"]')!;
    expect(el).toBeTruthy();
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(el.getAttribute("data-highlight")).toBe("on");
  });

  it("(c) repeat event with same payload but incremented key re-triggers scrollIntoView", () => {
    const target1: DeepLinkTarget = { projectId: "P1", taskId: "P1-T1", key: 1 };
    const { rerender } = renderWidget(target1);
    expect(scrollIntoView).toHaveBeenCalledTimes(1);

    // Advance past the highlight timer so the first highlight clears
    act(() => { vi.runAllTimers(); });

    const target2: DeepLinkTarget = { projectId: "P1", taskId: "P1-T1", key: 2 };
    rerender(
      <DeadlinesWidget
        home={makeHome(ITEMS)}
        online={true}
        projects={PROJECTS}
        onAddNote={vi.fn()}
        scrollTarget={target2}
      />,
    );

    expect(scrollIntoView).toHaveBeenCalledTimes(2);
    const el = document.getElementById("deadline-card-P1-T1")!;
    expect(el.getAttribute("data-highlight")).toBe("on");
  });
});
