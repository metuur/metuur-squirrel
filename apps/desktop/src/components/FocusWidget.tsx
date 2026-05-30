import type { HomeState } from "../hooks/useHome";
import type { ManualPick } from "../api/client";

interface Props {
  home: HomeState;
  online: boolean;
  onPick?: (slot: "today" | "week") => void;
  onClear?: (slot: "today" | "week") => void;
}

interface PillProps {
  slot: "today" | "week";
  label: string | null;
  online: boolean;
  onPick?: () => void;
  onClear?: () => void;
}

function FocusPill({ slot, label, online, onPick, onClear }: PillProps) {
  const pickLabel = slot === "today" ? "Pick today's focus" : "Pick this week's focus";
  const base = "text-xs text-slate-500 dark:text-slate-400 leading-relaxed flex items-center gap-1";
  const linkClass = "text-[11px] underline-offset-2 hover:underline disabled:opacity-50 disabled:no-underline";
  const clearClass = "text-[11px] text-red-500 dark:text-red-400 underline-offset-2 hover:underline disabled:opacity-50 disabled:no-underline";

  if (!online) {
    return <div className={base}>📌 {pickLabel.replace("Pick ", "")}: —</div>;
  }

  if (label) {
    return (
      <div className={base}>
        <span>📌 {label}:</span>
        <button type="button" onClick={onPick} disabled={!onPick} className={linkClass}>Change</button>
        <span className="text-slate-300 dark:text-slate-600">·</span>
        <button type="button" onClick={onClear} disabled={!onClear} className={clearClass}>Clear</button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={onPick}
      className={`${base} cursor-pointer hover:text-slate-700 dark:hover:text-slate-200 disabled:cursor-not-allowed text-left`}
    >
      📌 {pickLabel}
    </button>
  );
}

interface FocusRowProps {
  badge: string;
  badgeColor: string;
  pick: ManualPick;
  separator: boolean;
}

function ManualFocusRow({ badge, badgeColor, pick, separator }: FocusRowProps) {
  return (
    <div className={`flex items-start gap-2 ${separator ? "mt-2 pt-2 border-t border-slate-100 dark:border-slate-700/60" : ""}`}>
      <span className={`mt-0.5 shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded ${badgeColor}`}>
        {badge}
      </span>
      <div className="min-w-0">
        <p className="text-sm font-bold text-slate-900 dark:text-slate-100 leading-snug truncate">
          {pick.project_title} — {pick.intent_title}
        </p>
        {pick.next_action && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
            {pick.next_action}
          </p>
        )}
      </div>
    </div>
  );
}

export function FocusWidget({ home, online, onPick, onClear }: Props) {
  const focus = home.data?.focus ?? null;
  const manualFocus = home.data?.manual_focus ?? null;
  const dimmed = !online;

  const amPick = manualFocus?.today ?? null;
  const pmPick = manualFocus?.today_pm ?? null;
  const weekPick = manualFocus?.week ?? null;
  const hasManualToday = amPick || pmPick;
  const isAllDay = !!(amPick && pmPick && amPick.intent_slug === pmPick.intent_slug);

  // Label shown in the compact pill when a pick exists
  const todayPillLabel = hasManualToday
    ? isAllDay
      ? "Today (All day)"
      : amPick && pmPick
        ? "Today (AM + PM)"
        : amPick
          ? "Today (AM)"
          : "Today (PM)"
    : null;

  return (
    <section className={`px-4 pt-3 ${dimmed ? "opacity-50" : ""}`}>
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm p-3">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
          Today's focus
        </div>

        {hasManualToday ? (
          isAllDay ? (
            <ManualFocusRow
              badge="Today"
              badgeColor="bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
              pick={amPick!}
              separator={false}
            />
          ) : (
            <div className="flex flex-col">
              {amPick && (
                <ManualFocusRow
                  badge="AM"
                  badgeColor="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                  pick={amPick}
                  separator={false}
                />
              )}
              {pmPick && (
                <ManualFocusRow
                  badge="PM"
                  badgeColor="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
                  pick={pmPick}
                  separator={!!amPick}
                />
              )}
            </div>
          )
        ) : focus ? (
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

      <div className="mt-2 flex flex-col gap-1">
        <FocusPill
          slot="today"
          label={todayPillLabel}
          online={online}
          onPick={onPick ? () => onPick("today") : undefined}
          onClear={onClear ? () => onClear("today") : undefined}
        />
        {online && amPick && !pmPick && onPick && (
          <button
            type="button"
            onClick={() => onPick("today")}
            className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1 hover:text-slate-700 dark:hover:text-slate-200 text-left"
          >
            <span>📌</span>
            <span className="underline-offset-2 hover:underline">Add afternoon focus</span>
          </button>
        )}
        <FocusPill
          slot="week"
          label={weekPick ? "This week" : null}
          online={online}
          onPick={onPick ? () => onPick("week") : undefined}
          onClear={onClear ? () => onClear("week") : undefined}
        />
      </div>
    </section>
  );
}
