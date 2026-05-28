// Phase 2 FocusWidget — renders /api/home.focus inside a card that mirrors
// the web UI's "Today's focus" panel (apps/backend/app/src/pages/HomePage.tsx
// Header component): white surface, rounded-2xl, subtle shadow + border, an
// uppercase tracking-wider label, then a bold title and a muted next action.
// EARS R-2.2, R-2.3, R-2.9.

import type { HomeState } from "../hooks/useHome";

interface Props {
  home: HomeState;
  online: boolean;
}

export function FocusWidget({ home, online }: Props) {
  const focus = home.data?.focus ?? null;
  const dimmed = !online;

  return (
    <section className={`px-4 pt-3 ${dimmed ? "opacity-50" : ""}`}>
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm p-3">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
          Today's focus
        </div>
        {focus ? (
          <>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 leading-snug">
              {focus.title}
            </h2>
            {focus.next_action && (
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                {focus.next_action}
              </p>
            )}
          </>
        ) : home.data ? (
          <div className="text-xs text-slate-500 dark:text-slate-400">
            No active focus — capture a thought or start a project.
          </div>
        ) : (
          <div className="text-xs text-slate-400 dark:text-slate-500">—</div>
        )}
      </div>
    </section>
  );
}
