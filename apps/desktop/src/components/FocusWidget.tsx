import type { HomeState } from "../hooks/useHome";
import type { ManualPick } from "../api/client";

interface Props {
  home: HomeState;
  online: boolean;
  onPick?: (slot: "today" | "week") => void;
  onClear?: (slot: "today" | "today_pm" | "week") => void;
}

// Compact action-only pill — selected content is shown inside the card, not here.
interface PillProps {
  slot: "today" | "today_pm" | "week";
  isPicked: boolean;
  online: boolean;
  onPick?: () => void;
  onClear?: () => void;
}

function FocusPill({ slot, isPicked, online, onPick, onClear }: PillProps) {
  const pickLabel =
    slot === "today" ? "Pick AM focus" : slot === "today_pm" ? "Pick PM focus" : "Pick this week's focus";
  const slotShort = slot === "today" ? "AM" : slot === "today_pm" ? "PM" : "Week";
  const base = "text-xs text-slate-500 dark:text-slate-400 leading-relaxed flex items-center gap-1";
  const linkClass =
    "text-[11px] underline-offset-2 hover:underline disabled:opacity-50 disabled:no-underline";

  if (!online) {
    return <div className={base}>📌 {slotShort}: —</div>;
  }

  if (isPicked) {
    return (
      <div className={base}>
        <span>📌 {slotShort}:</span>
        <button type="button" onClick={onPick} disabled={!onPick} className={linkClass}>
          Change
        </button>
        <span className="text-slate-300 dark:text-slate-600">·</span>
        <button type="button" onClick={onClear} disabled={!onClear} className={linkClass}>
          Clear
        </button>
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
}

function ManualFocusRow({ badge, badgeColor, pick }: FocusRowProps) {
  return (
    <div className="flex items-start gap-2 mt-2 pt-2 border-t border-slate-100 dark:border-slate-700/60 first:mt-0 first:pt-0 first:border-0">
      <span
        className={`mt-0.5 shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded ${badgeColor}`}
      >
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

  return (
    <section className={`px-4 pt-3 ${dimmed ? "opacity-50" : ""}`}>
      <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-sm p-3">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
          Today's focus
        </div>

        {hasManualToday ? (
          <div className="flex flex-col">
            {amPick && (
              <ManualFocusRow
                badge="AM"
                badgeColor="bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                pick={amPick}
              />
            )}
            {pmPick && (
              <ManualFocusRow
                badge="PM"
                badgeColor="bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
                pick={pmPick}
              />
            )}
          </div>
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
          isPicked={!!amPick}
          online={online}
          onPick={onPick ? () => onPick("today") : undefined}
          onClear={onClear ? () => onClear("today") : undefined}
        />
        <FocusPill
          slot="today_pm"
          isPicked={!!pmPick}
          online={online}
          onPick={onPick ? () => onPick("today") : undefined}
          onClear={onClear ? () => onClear("today_pm") : undefined}
        />
        <FocusPill
          slot="week"
          isPicked={!!weekPick}
          online={online}
          onPick={onPick ? () => onPick("week") : undefined}
          onClear={onClear ? () => onClear("week") : undefined}
        />
      </div>
    </section>
  );
}
