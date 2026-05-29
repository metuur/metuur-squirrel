// Phase 2 FocusWidget — renders /api/home.focus inside a card that mirrors
// the web UI's "Today's focus" panel (apps/backend/app/src/pages/HomePage.tsx
// Header component): white surface, rounded-2xl, subtle shadow + border, an
// uppercase tracking-wider label, then a bold title and a muted next action.
// EARS R-2.2, R-2.3, R-2.9.
//
// Story 5.2 — adds two "manual focus" pills below the primary card (today
// + this week). Story 5.3 — wires the Change / Clear controls on populated
// pills (R-5.6). EARS R-5.1..R-5.9.

import type { HomeState } from "../hooks/useHome";
import type { ManualPick } from "../api/client";

interface Props {
  home: HomeState;
  online: boolean;
  /** Opens the FocusPickerModal for that slot. Fires from both the unset CTA
   *  and the populated pill's "Change" control. */
  onPick?: (slot: "today" | "week") => void;
  /** Clears the slot via PUT /api/focus/<slot> {clear: true}. */
  onClear?: (slot: "today" | "week") => void;
}

interface ManualFocusPillProps {
  slot: "today" | "week";
  pick: ManualPick | null;
  alignedWithFocus: boolean;
  online: boolean;
  onPick?: () => void;
  onClear?: () => void;
}

function ManualFocusPill({
  slot,
  pick,
  alignedWithFocus,
  online,
  onPick,
  onClear,
}: ManualFocusPillProps) {
  const label = slot === "today" ? "Today" : "This week";
  const ctaLabel = slot === "today" ? "Pick today's focus" : "Pick this week's focus";
  const base =
    "text-xs text-slate-500 dark:text-slate-400 leading-relaxed flex items-center gap-1";
  const controlClass =
    "ml-1 text-[11px] underline-offset-2 hover:underline disabled:opacity-50 disabled:no-underline";

  // R-5.9: backend offline ⇒ show em-dash and disable the CTA.
  if (!online) {
    return <div className={base}>📌 {label}: —</div>;
  }

  if (pick) {
    return (
      <div className={base}>
        <span className="truncate">
          📌 {label}: {pick.project_title} — {pick.intent_title}
          {alignedWithFocus ? " (aligned with critical)" : ""}
        </span>
        {alignedWithFocus && <span aria-label="aligned with critical focus">✓</span>}
        <span className="ml-auto flex items-center shrink-0">
          <button
            type="button"
            onClick={onPick}
            disabled={!onPick}
            className={controlClass}
          >
            Change
          </button>
          <button
            type="button"
            onClick={onClear}
            disabled={!onClear}
            className={controlClass}
          >
            Clear
          </button>
        </span>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={onPick}
      className={`${base} cursor-pointer hover:text-slate-700 dark:hover:text-slate-200 disabled:cursor-not-allowed text-left`}
    >
      📌 {ctaLabel}
    </button>
  );
}

export function FocusWidget({ home, online, onPick, onClear }: Props) {
  const focus = home.data?.focus ?? null;
  const manualFocus = home.data?.manual_focus ?? null;
  const dimmed = !online;

  // R-5.7 alignment is project_slug-only because FocusItem doesn't expose
  // an intent_slug on the existing /api/home.focus payload. Intent-level
  // refinement can land when the API surfaces it.
  const todayAligned =
    !!focus && !!manualFocus?.today && focus.slug === manualFocus.today.project_slug;
  const weekAligned =
    !!focus && !!manualFocus?.week && focus.slug === manualFocus.week.project_slug;

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
      <div className="mt-2 flex flex-col gap-1">
        <ManualFocusPill
          slot="today"
          pick={manualFocus?.today ?? null}
          alignedWithFocus={todayAligned}
          online={online}
          onPick={onPick ? () => onPick("today") : undefined}
          onClear={onClear ? () => onClear("today") : undefined}
        />
        <ManualFocusPill
          slot="week"
          pick={manualFocus?.week ?? null}
          alignedWithFocus={weekAligned}
          online={online}
          onPick={onPick ? () => onPick("week") : undefined}
          onClear={onClear ? () => onClear("week") : undefined}
        />
      </div>
    </section>
  );
}
