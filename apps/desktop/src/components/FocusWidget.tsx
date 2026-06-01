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
  dotStyle?: React.CSSProperties;
  onPick?: () => void;
  onClear?: () => void;
}

// Violet — used for the PM chip override and the "Add afternoon focus" dot
// per code.html line 472. Not a theme token because it's a one-off accent.
const VIOLET = "#8B5CF6";
const VIOLET_DOT_STYLE: React.CSSProperties = {
  background: VIOLET,
  boxShadow: `0 0 0 3px rgba(139, 92, 246, 0.10)`,
};
const VIOLET_CHIP_STYLE: React.CSSProperties = {
  background: "rgba(139, 92, 246, 0.10)",
  borderColor: "rgba(139, 92, 246, 0.18)",
  color: VIOLET,
};
const OK_DOT_STYLE: React.CSSProperties = {
  background: "var(--color-ok)",
  boxShadow: "0 0 0 3px rgba(47, 107, 79, 0.12)",
};
const WEEK_CHIP_STYLE: React.CSSProperties = {
  background: "rgba(47, 107, 79, 0.10)",
  borderColor: "rgba(47, 107, 79, 0.18)",
  color: "var(--color-ok)",
};

function FocusPill({ slot, label, online, dotStyle, onPick, onClear }: PillProps) {
  const pickLabel = slot === "today" ? "Pick today's focus" : "Pick this week's focus";

  if (!online) {
    return (
      <div className="quick-action" style={{ opacity: 0.5, cursor: "default" }}>
        <span className="dot" style={dotStyle}></span>
        <span>
          {slot === "today" ? "What matters today:" : "What matters this week:"}{" "}
          <span className="text-ink-4">—</span>
        </span>
      </div>
    );
  }

  if (label) {
    return (
      <div className="quick-action">
        <span className="dot" style={dotStyle}></span>
        <span>{label}:</span>
        <button
          type="button"
          onClick={onPick}
          disabled={!onPick}
          className="text-[11px] underline-offset-2 hover:underline text-ink-3 disabled:opacity-50 disabled:no-underline"
        >
          Change
        </button>
        <span className="text-ink-4">·</span>
        <button
          type="button"
          onClick={onClear}
          disabled={!onClear}
          className="text-[11px] underline-offset-2 hover:underline text-critical disabled:opacity-50 disabled:no-underline"
          style={{ color: "var(--color-critical)" }}
        >
          Clear
        </button>
      </div>
    );
  }

  return (
    <button type="button" onClick={onPick} className="quick-action">
      <span className="dot" style={dotStyle}></span>
      {pickLabel}
    </button>
  );
}

interface FocusRowProps {
  badge: string;
  chipStyle?: React.CSSProperties;
  pick: ManualPick;
  separator: boolean;
}

function ManualFocusRow({ badge, chipStyle, pick, separator }: FocusRowProps) {
  // If next_action exists, the slug line carries project + intent context and
  // the title line carries the action. Otherwise project goes to the slug and
  // intent_title becomes the title (avoids printing intent twice).
  const slugText = pick.next_action
    ? `${pick.project_title} · ${pick.intent_title}`
    : pick.project_title;
  const titleText = pick.next_action || pick.intent_title;

  return (
    <div
      className={`flex items-start gap-2.5 ${
        separator ? "mt-2 pt-2 border-t border-hairline-2" : ""
      }`}
    >
      <span className="chip chip-am shrink-0 mt-0.5" style={chipStyle}>
        {badge}
      </span>
      <div className="min-w-0 flex-1">
        <p className="slug truncate mb-0.5">{slugText}</p>
        <div className="flex items-baseline gap-2 min-w-0">
          <p className="title text-[13px] leading-tight truncate min-w-0">{titleText}</p>
          {pick.note && (
            <span
              className="text-[10.5px] text-ink-3 italic leading-tight truncate min-w-0"
              title={pick.note}
            >
              “{pick.note}”
            </span>
          )}
        </div>
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
      <div className="card-focus p-2.5">
        <div className="eyebrow mb-1">Today's focus</div>

        {hasManualToday ? (
          isAllDay ? (
            <ManualFocusRow
              badge="Today"
              pick={amPick!}
              separator={false}
            />
          ) : (
            <div className="flex flex-col">
              {amPick && (
                <ManualFocusRow
                  badge="AM"
                  pick={amPick}
                  separator={false}
                />
              )}
              {pmPick && (
                <ManualFocusRow
                  badge="PM"
                  chipStyle={VIOLET_CHIP_STYLE}
                  pick={pmPick}
                  separator={!!amPick}
                />
              )}
            </div>
          )
        ) : focus ? (
          <>
            <h2 className="title text-[13px] leading-tight">{focus.title}</h2>
            {focus.next_action && (
              <p className="mt-0.5 text-[11px] text-ink-3 leading-snug">
                {focus.next_action}
              </p>
            )}
          </>
        ) : home.data ? (
          <div className="text-xs text-ink-3">
            No active focus — capture a thought or start a project.
          </div>
        ) : (
          <div className="text-xs text-ink-4">—</div>
        )}
      </div>

      {weekPick && (
        <div className="card-focus p-2.5 mt-1.5">
          <div className="eyebrow mb-1">This week</div>
          <ManualFocusRow
            badge="Week"
            chipStyle={WEEK_CHIP_STYLE}
            pick={weekPick}
            separator={false}
          />
        </div>
      )}

      <div className="mt-2 flex flex-row flex-wrap items-center gap-x-4 gap-y-1">
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
            className="quick-action"
          >
            <span className="dot" style={VIOLET_DOT_STYLE}></span>
            Add afternoon focus
          </button>
        )}
        <FocusPill
          slot="week"
          label={weekPick ? "This week" : null}
          online={online}
          dotStyle={OK_DOT_STYLE}
          onPick={onPick ? () => onPick("week") : undefined}
          onClear={onClear ? () => onClear("week") : undefined}
        />
      </div>
    </section>
  );
}
