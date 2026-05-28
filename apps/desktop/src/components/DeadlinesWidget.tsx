// Phase 2 DeadlinesWidget — renders /api/home.pressing[] as small cards
// styled like the web UI's PressingCard column header (red accent rule
// above PRESSING items, white surface cards, mono id, red overdue chip).
// EARS R-2.4, R-2.5, R-2.6, R-2.9.
//
// Each card has:
// - the task id (mono, small)
// - the task title (clamped to 2 lines)
// - a meta row: overdue/hours indicator + "Updated Xd ago" if mtime present
// - an action row: "+ note" (opens capture modal pre-set to the task's
//   project) and "↗" (opens the web UI's /notes/<id> in the browser).

import { openUrl } from "@tauri-apps/plugin-opener";
import type { HomeState } from "../hooks/useHome";
import type { PressingItem, ProjectListItem } from "../api/client";
import { BACKEND_ORIGIN } from "../api/client";
import { projectForTask } from "../lib/projectForTask";
import { timeAgo } from "../lib/timeAgo";

interface Props {
  home: HomeState;
  online: boolean;
  projects: ProjectListItem[];
  onAddNote: (initialSlug: string | null) => void;
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
  void openUrl(`${BACKEND_ORIGIN}/notes/${taskId}`);
}

export function DeadlinesWidget({ home, online, projects, onAddNote }: Props) {
  const pressing = home.data?.pressing ?? [];
  const top = pressing.slice(0, 3);
  const dimmed = !online;

  return (
    <section className={`px-4 pt-4 ${dimmed ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between border-b-2 border-red-300 dark:border-red-700/50 pb-1.5 mb-2 px-0.5">
        <h3 className="text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
          Pressing
        </h3>
        {top.length > 0 && (
          <span className="inline-flex items-center justify-center min-w-5 h-5 px-1.5 bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400 text-[10px] font-bold rounded-full">
            {pressing.length}
          </span>
        )}
      </div>
      {top.length > 0 ? (
        <ul className="space-y-2">
          {top.map((item) => {
            const updated = timeAgo(item.mtime);
            return (
              <li
                key={item.id}
                className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm px-3 py-2"
              >
                <div className="text-[10px] font-mono text-slate-400 truncate">{item.id}</div>
                <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200 leading-snug mt-0.5 line-clamp-2">
                  {item.title}
                </h4>

                {/* meta row: urgency · last updated */}
                <div className="mt-1.5 flex items-center gap-2 text-[11px] font-medium">
                  <span
                    className={`inline-flex items-center gap-1 ${
                      item.is_overdue ? "text-red-600 dark:text-red-400" : "text-orange-600 dark:text-orange-400"
                    }`}
                  >
                    <span aria-hidden>⏰</span>
                    {tail(item)}
                  </span>
                  {updated && (
                    <>
                      <span className="text-slate-300 dark:text-slate-600">·</span>
                      <span className="text-slate-500 dark:text-slate-400 text-[10px]">
                        Updated {updated}
                      </span>
                    </>
                  )}
                </div>

                {/* action row */}
                <div className="mt-2 flex items-center justify-end gap-1.5">
                  <button
                    type="button"
                    onClick={() => online && onAddNote(projectForTask(item.id, projects))}
                    disabled={!online}
                    title={
                      online
                        ? `Add a note to ${projectForTask(item.id, projects) ?? "Inbox"}`
                        : "Backend offline"
                    }
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-primary hover:text-white hover:border-primary dark:hover:bg-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <span aria-hidden>+</span>
                    note
                  </button>
                  <button
                    type="button"
                    onClick={() => openTaskDetails(item.id)}
                    title="Open task in web UI"
                    aria-label="Open task in web UI"
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-semibold rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  >
                    <span aria-hidden>↗</span>
                    open
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      ) : home.data ? (
        <div className="text-xs text-slate-500 dark:text-slate-400 px-1">Nothing pressing today.</div>
      ) : (
        <div className="text-xs text-slate-400 dark:text-slate-500 px-1">—</div>
      )}
    </section>
  );
}
