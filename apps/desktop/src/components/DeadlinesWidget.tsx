// Phase 2 DeadlinesWidget — renders /api/home.pressing[] as small cards
// styled like the web UI's PressingCard column header (red accent rule
// above PRESSING items, white surface cards, mono id, red overdue chip).
// EARS R-2.4, R-2.5, R-2.6, R-2.9.

import type { HomeState } from "../hooks/useHome";
import type { PressingItem } from "../api/client";

interface Props {
  home: HomeState;
  online: boolean;
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

export function DeadlinesWidget({ home, online }: Props) {
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
          {top.map((item) => (
            <li
              key={item.id}
              className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-sm px-3 py-2"
            >
              <div className="text-[10px] font-mono text-slate-400 truncate">{item.id}</div>
              <h4 className="text-xs font-semibold text-slate-800 dark:text-slate-200 leading-snug mt-0.5 line-clamp-2">
                {item.title}
              </h4>
              <div
                className={`mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium ${
                  item.is_overdue ? "text-red-600 dark:text-red-400" : "text-orange-600 dark:text-orange-400"
                }`}
              >
                <span aria-hidden>⏰</span>
                {tail(item)}
              </div>
            </li>
          ))}
        </ul>
      ) : home.data ? (
        <div className="text-xs text-slate-500 dark:text-slate-400 px-1">Nothing pressing today.</div>
      ) : (
        <div className="text-xs text-slate-400 dark:text-slate-500 px-1">—</div>
      )}
    </section>
  );
}
