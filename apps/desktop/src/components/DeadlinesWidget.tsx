// Phase 2 DeadlinesWidget — renders /api/home.pressing[] as small cards
// matching the paper-indigo design (`.card` + `.stripe-*` severity rail,
// `.slug` + `.title` typography, `.chip chip-critical/warning` overdue badge,
// stacked `.btn` action buttons).
//
// Each card carries:
// - the task id (mono, .slug)
// - the task title (.title, clamped to 2 lines)
// - an overdue/urgency chip (color tracks the stripe level)
// - "Last worked Xd ago" if mtime present
// - two .btn actions: "+ Note" (opens capture modal) and "Open ↗" (opens
//   the web UI's /notes/<id> in the browser)

import { useEffect, useRef } from "react";
import type { HomeState } from "../hooks/useHome";
import type { DeepLinkTarget } from "../hooks/useDeepLink";
import type { PressingItem, ProjectListItem } from "../api/client";
import { openWebUrl } from "../api/client";
import { projectForTask } from "../lib/projectForTask";
import { timeAgo } from "../lib/timeAgo";
import styles from "./DeadlinesWidget.module.css";

// Import styles for side-effect (injects [data-highlight="on"] keyframe rule).
void styles;

interface Props {
  home: HomeState;
  online: boolean;
  projects: ProjectListItem[];
  onAddNote: (initialSlug: string | null) => void;
  scrollTarget?: DeepLinkTarget | null;
}

type StripeLevel = "critical" | "warning" | "ok";

// Map a PressingItem to one of three stripe colors. Backend reduces the 6
// canonical urgency levels (critical, urgent, soon, upcoming, eventual,
// distant) to the 3 stripe variants the design system supports. Overdue
// always escalates to critical regardless of bucket.
function stripeLevel(item: PressingItem): StripeLevel {
  if (item.is_overdue) return "critical";
  switch (item.urgency) {
    case "critical":
      return "critical";
    case "urgent":
    case "soon":
      return "warning";
    default:
      return "ok";
  }
}

function tail(item: PressingItem): string {
  if (item.is_overdue) {
    return `${item.days_overdue ?? "?"}d overdue`;
  }
  if (item.hours_left != null) {
    return `${Math.round(item.hours_left)}h left`;
  }
  return item.urgency_label;
}

function openTaskDetails(taskId: string) {
  void openWebUrl(`/notes/${taskId}`);
}

// Compact .btn — matches the per-card action button padding from code.html
// lines 511-528 (5px 10px, 11px font). Used inline via style={ACTION_BTN_STYLE}.
const ACTION_BTN_STYLE: React.CSSProperties = { padding: "5px 10px", fontSize: 11 };

function ClockIcon() {
  return (
    <svg
      width="9"
      height="9"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      aria-hidden
    >
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

export function DeadlinesWidget({ home, online, projects, onAddNote, scrollTarget }: Props) {
  const pressing = home.data?.pressing ?? [];
  const top = pressing.slice(0, 3);
  const dimmed = !online;

  // R-5.6 / R-5.7 / R-5.8 / R-5.10
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Tracks the last scrollTarget.key we successfully highlighted so we don't
  // re-highlight on data refreshes once the element has been found.
  const lastHandledKeyRef = useRef<number | null>(null);

  // Also depend on !!home.data so the effect retries once data arrives when
  // the deep-link fires before the first home fetch completes.
  const dataReady = !!home.data;
  useEffect(() => {
    if (!scrollTarget) return;
    if (lastHandledKeyRef.current === scrollTarget.key) return;

    let el: Element | null = null;

    if (scrollTarget.taskId) {
      el = document.getElementById(`deadline-card-${scrollTarget.taskId}`);
    }

    if (!el) {
      el = document.querySelector(`[data-project-id="${scrollTarget.projectId}"]`);
    }

    // The daemon encodes the task ID as the project path segment (R-8.1), so
    // projectId may be a task ID when no project slug prefix matches.
    if (!el) {
      el = document.getElementById(`deadline-card-${scrollTarget.projectId}`);
    }

    if (!el) {
      console.debug("[DeadlinesWidget] scroll target not found, will retry when data loads", scrollTarget);
      return;
    }

    lastHandledKeyRef.current = scrollTarget.key;

    el.scrollIntoView({ block: "center", behavior: "smooth" });

    if (highlightTimerRef.current !== null) {
      clearTimeout(highlightTimerRef.current);
      el.removeAttribute("data-highlight");
    }

    el.setAttribute("data-highlight", "on");
    const captured = el;
    highlightTimerRef.current = setTimeout(() => {
      captured.removeAttribute("data-highlight");
      highlightTimerRef.current = null;
    }, 1500);

    return () => {
      if (highlightTimerRef.current !== null) {
        clearTimeout(highlightTimerRef.current);
      }
    };
  }, [scrollTarget?.key, dataReady]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className={`px-4 pt-3 ${dimmed ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between mb-2 px-0.5">
        <div className="flex items-center gap-2">
          <span className="eyebrow">Pressing</span>
          <span className="relative group flex items-center cursor-help">
          <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-info-icon lucide-info"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>

            <span
              role="tooltip"
              className="absolute left-full ml-2 top-1/2 -translate-y-1/2 z-30 hidden group-hover:block w-100 panel px-3 py-2 text-xs text-ink-2 shadow-lg"
            >
              Filled automatically: your 3 most urgent items by deadline — overdue or due soon.
              Give a task a deadline to surface it here.
            </span>
          </span>
          {top.length > 0 && (
            <span className="chip chip-count tabular">{pressing.length}</span>
          )}
        </div>
      </div>

      {top.length > 0 ? (
        <ul className="space-y-2">
          {top.map((item) => {
            const lastWorked = timeAgo(item.last_worked);
            const projectSlug = projectForTask(item.id, projects) ?? "";
            const level = stripeLevel(item);
            const chipClass = level === "critical" ? "chip-critical" : "chip-warning";
            return (
              <li
                key={item.id}
                id={`deadline-card-${item.id}`}
                data-task-id={item.id}
                data-project-id={projectSlug}
                className={`card stripe stripe-${level}`}
                style={{ padding: "10px 10px 10px 14px" }}
              >
                <div className="flex justify-between items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="slug truncate">{item.id}</p>
                    <p className="title text-[13.5px] leading-snug mt-0.5 mb-2 line-clamp-2">
                      {item.title}
                    </p>
                    <span className={`chip ${chipClass}`}>
                      <ClockIcon />
                      {tail(item)}
                    </span>
                    {lastWorked && (
                      <span className="ml-2 text-[10px] text-ink-4 tabular">
                        Last worked {lastWorked}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => online && onAddNote(projectForTask(item.id, projects))}
                      disabled={!online}
                      title={
                        online
                          ? `Add a note to ${projectForTask(item.id, projects) ?? "Inbox"}`
                          : "Backend offline"
                      }
                      className="btn"
                      style={ACTION_BTN_STYLE}
                    >
                      <svg
                        width="10"
                        height="10"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        aria-hidden
                      >
                        <line x1="12" x2="12" y1="5" y2="19" />
                        <line x1="5" x2="19" y1="12" y2="12" />
                      </svg>
                      Note
                    </button>
                    <button
                      type="button"
                      onClick={() => openTaskDetails(item.id)}
                      title="Open task in web UI"
                      aria-label="Open task in web UI"
                      className="btn"
                      style={ACTION_BTN_STYLE}
                    >
                      Open
                      <svg
                        width="9"
                        height="9"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        aria-hidden
                      >
                        <line x1="7" y1="17" x2="17" y2="7" />
                        <polyline points="7 7 17 7 17 17" />
                      </svg>
                    </button>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      ) : home.data ? (
        <div className="text-xs text-ink-3 px-1">Nothing pressing today.</div>
      ) : (
        <div className="text-xs text-ink-4 px-1">—</div>
      )}
    </section>
  );
}
