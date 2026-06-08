import type { HomeState } from "../hooks/useHome";
import type { ManualPick, OpenSession } from "../api/client";

interface Props {
  home: HomeState;
  online: boolean;
  // Live focus session + derived elapsed minutes (HH:MM timer on the open pick).
  session?: OpenSession | null;
  elapsedMinutes?: number;
  onPick?: (slot: "today" | "week") => void;
  onClear?: (slot: "today" | "week") => void;
  onSetEstimate?: (
    projectSlug: string,
    intentSlug: string,
    minutes: number | null,
  ) => void;
  // Check in to a pick / check out the open session. Only provided when online.
  onCheckin?: (pick: ManualPick) => void;
  onCheckout?: () => void;
}

// Format minutes as "Xh Ym" / "Ym".
function fmtMins(m: number): string {
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  const r = m % 60;
  return r ? `${h}h ${r}m` : `${h}h`;
}

// Elapsed minutes as a zero-padded HH:MM with unbounded hours (e.g. "00:07",
// "12:34"). Drives the live focus timer; minute granularity by design.
function fmtHHMM(totalMinutes: number): string {
  const safe = Math.max(0, Math.floor(totalMinutes));
  const h = Math.floor(safe / 60);
  const m = safe % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

// True when the open session belongs to this pick.
function isSessionFor(
  session: OpenSession | null | undefined,
  pick: ManualPick,
): boolean {
  return (
    !!session &&
    session.project_slug === pick.project_slug &&
    session.intent_slug === pick.intent_slug
  );
}

// Green chip used for the live timer pill.
const TIMER_CHIP_STYLE: React.CSSProperties = {
  background: "rgba(47, 107, 79, 0.10)",
  borderColor: "rgba(47, 107, 79, 0.18)",
  color: "var(--color-ok)",
};

// Check in / live HH:MM timer + Check out, shown under a focused intent. Rendered
// only when online (handlers present). Tapping Check in while another session is
// open is gated by a friendly confirm in App — here we just emit the intent.
function CheckinControls({
  pick,
  session,
  elapsedMinutes,
  onCheckin,
  onCheckout,
}: {
  pick: ManualPick;
  session: OpenSession | null | undefined;
  elapsedMinutes: number;
  onCheckin?: (pick: ManualPick) => void;
  onCheckout?: () => void;
}) {
  if (!onCheckin && !onCheckout) return null; // offline / not wired

  if (isSessionFor(session, pick)) {
    return (
      <div className="mt-1 flex items-center gap-2">
        <span
          className="chip chip-am shrink-0 tabular-nums"
          style={TIMER_CHIP_STYLE}
          title="Time on this sitting"
        >
          ⏱ {fmtHHMM(elapsedMinutes)}
        </span>
        <button
          type="button"
          onClick={onCheckout}
          disabled={!onCheckout}
          className="text-[11px] underline-offset-2 hover:underline text-critical disabled:opacity-50 disabled:no-underline"
          style={{ color: "var(--color-critical)" }}
        >
          Check out
        </button>
      </div>
    );
  }

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => onCheckin?.(pick)}
        disabled={!onCheckin}
        className="text-[11px] underline-offset-2 hover:underline text-ink-3 disabled:opacity-50 disabled:no-underline"
      >
        Check in
      </button>
    </div>
  );
}

// Neutral, non-shaming variance copy by ratio band (R-4.3, R-4.4). Inlined here
// (not a shared cross-surface helper) — the web HomePage carries its own copy.
function varianceLabel(ratio: number): string {
  if (ratio >= 0.85 && ratio <= 1.15) return "about right — learning your pace";
  if (ratio > 1.15) return "ran longer than planned — learning your pace";
  return "finished ahead of plan";
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
  onSetEstimate?: (
    projectSlug: string,
    intentSlug: string,
    minutes: number | null,
  ) => void;
  session?: OpenSession | null;
  elapsedMinutes?: number;
  onCheckin?: (pick: ManualPick) => void;
  onCheckout?: () => void;
}

// The estimate/actual/variance line shown under a focused intent.
// - has_variance:   "guessed 45m · est 1h53m · actual 2h10m · 1.0× — copy"
// - estimate only:  "est 1h53m · not started yet"
// - actual only:    "actual 2h10m · + estimate"  (prompt to add an estimate)
function EstimateLine({
  pick,
  onSetEstimate,
}: {
  pick: ManualPick;
  onSetEstimate?: FocusRowProps["onSetEstimate"];
}) {
  const promptEstimate = () => {
    if (!onSetEstimate) return;
    const raw = window.prompt("Estimate for this task — minutes (blank to clear):", "");
    if (raw === null) return; // cancelled
    const trimmed = raw.trim();
    if (trimmed === "") {
      onSetEstimate(pick.project_slug, pick.intent_slug, null);
      return;
    }
    const mins = Number(trimmed);
    if (!Number.isFinite(mins) || mins <= 0) return;
    onSetEstimate(pick.project_slug, pick.intent_slug, Math.round(mins));
  };

  const setBtn = onSetEstimate ? (
    <button
      type="button"
      onClick={promptEstimate}
      className="text-[10.5px] underline-offset-2 hover:underline text-ink-3"
    >
      {pick.estimate_minutes ? "edit estimate" : "+ estimate"}
    </button>
  ) : null;

  if (pick.has_variance && pick.estimate_minutes && pick.variance_ratio != null) {
    return (
      <p className="mt-1 text-[10.5px] text-ink-3 leading-snug">
        {pick.estimate_user_minutes ? `guessed ${fmtMins(pick.estimate_user_minutes)} · ` : ""}
        est {fmtMins(pick.estimate_minutes)} · actual {fmtMins(pick.time_invested_minutes)} ·{" "}
        <span className="text-ink-2">{pick.variance_ratio.toFixed(1)}×</span>{" "}
        <span className="italic">— {varianceLabel(pick.variance_ratio)}</span> {setBtn}
      </p>
    );
  }
  if (pick.estimate_minutes) {
    return (
      <p className="mt-1 text-[10.5px] text-ink-3 leading-snug">
        est {fmtMins(pick.estimate_minutes)} · not started yet {setBtn}
      </p>
    );
  }
  if (pick.time_invested_minutes > 0) {
    return (
      <p className="mt-1 text-[10.5px] text-ink-3 leading-snug">
        actual {fmtMins(pick.time_invested_minutes)} {setBtn}
      </p>
    );
  }
  return setBtn ? (
    <p className="mt-1 text-[10.5px] leading-snug">{setBtn}</p>
  ) : null;
}

function ManualFocusRow({
  badge,
  chipStyle,
  pick,
  separator,
  onSetEstimate,
  session,
  elapsedMinutes = 0,
  onCheckin,
  onCheckout,
}: FocusRowProps) {
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
        <EstimateLine pick={pick} onSetEstimate={onSetEstimate} />
        <CheckinControls
          pick={pick}
          session={session}
          elapsedMinutes={elapsedMinutes}
          onCheckin={onCheckin}
          onCheckout={onCheckout}
        />
      </div>
    </div>
  );
}

export function FocusWidget({
  home,
  online,
  session,
  elapsedMinutes,
  onPick,
  onClear,
  onSetEstimate,
  onCheckin,
  onCheckout,
}: Props) {
  const focus = home.data?.focus ?? null;
  const manualFocus = home.data?.manual_focus ?? null;
  const dimmed = !online;

  // Check-in props shared by every focus row.
  const checkinProps = { session, elapsedMinutes, onCheckin, onCheckout };

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
              onSetEstimate={onSetEstimate}
              {...checkinProps}
            />
          ) : (
            <div className="flex flex-col">
              {amPick && (
                <ManualFocusRow
                  badge="AM"
                  pick={amPick}
                  separator={false}
                  onSetEstimate={onSetEstimate}
                  {...checkinProps}
                />
              )}
              {pmPick && (
                <ManualFocusRow
                  badge="PM"
                  chipStyle={VIOLET_CHIP_STYLE}
                  pick={pmPick}
                  separator={!!amPick}
                  onSetEstimate={onSetEstimate}
                  {...checkinProps}
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
            onSetEstimate={onSetEstimate}
            {...checkinProps}
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
