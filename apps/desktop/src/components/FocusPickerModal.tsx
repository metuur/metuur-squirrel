import { useEffect, useState } from "react";
import {
  ApiError,
  api,
  type ManualFocusPayload,
  type ManualPick,
  type ProjectListItem,
  type ProjectNote,
} from "../api/client";

interface Props {
  slot: "today" | "week";
  projects: ProjectListItem[];
  /** Current AM pick, if any — used to show context in step 2. */
  currentAmPick?: ManualPick | null;
  /** Current PM pick, if any — used to show context in step 2. */
  currentPmPick?: ManualPick | null;
  onClose: () => void;
  onPicked?: (result: ManualFocusPayload) => void;
}

interface PendingIntent {
  projectSlug: string;
  projectTitle: string;
  intentSlug: string;
  intentTitle: string;
}

export function FocusPickerModal({
  slot,
  projects,
  currentAmPick,
  currentPmPick,
  onClose,
  onPicked,
}: Props) {
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
  const [intentsBySlug, setIntentsBySlug] = useState<Record<string, ProjectNote[]>>({});
  const [loadingSlug, setLoadingSlug] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState<PendingIntent | null>(null);

  const onStep2 = slot === "today" && pending !== null;
  const hasAM = !!currentAmPick;
  const hasPM = !!currentPmPick;
  const isAllDay = !!(
    currentAmPick && currentPmPick &&
    currentAmPick.intent_slug === currentPmPick.intent_slug
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !submitting) {
        if (onStep2) setPending(null);
        else onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, submitting, onStep2]);

  const handleExpand = async (slug: string) => {
    if (submitting) return;
    if (expandedSlug === slug) { setExpandedSlug(null); return; }
    setExpandedSlug(slug);
    if (intentsBySlug[slug]) return;
    setLoadingSlug(slug);
    setError(null);
    try {
      const detail = await api.projectDetail(slug);
      setIntentsBySlug((prev) => ({ ...prev, [slug]: detail.notes }));
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingSlug((cur) => (cur === slug ? null : cur));
    }
  };

  const handleIntentClick = (p: ProjectListItem, intent: ProjectNote) => {
    if (submitting) return;
    if (slot === "week") {
      submitFocus("week", p.slug, intent.id);
    } else {
      setPending({ projectSlug: p.slug, projectTitle: p.title, intentSlug: intent.id, intentTitle: intent.title });
    }
  };

  const submitFocus = async (
    focusSlot: "today" | "today_pm" | "week" | "all_day",
    projectSlug: string,
    intentSlug: string,
  ) => {
    setSubmitting(true);
    setError(null);
    try {
      if (focusSlot === "all_day") {
        // Explicitly clear both slots first, then set both to the new task.
        // This ensures a clean transition from any previous state.
        await api.focusSet("today", { clear: true });
        await api.focusSet("today_pm", { clear: true });
        await api.focusSet("today", { project_slug: projectSlug, intent_slug: intentSlug });
        const result = await api.focusSet("today_pm", { project_slug: projectSlug, intent_slug: intentSlug });
        onPicked?.(result);
      } else if (focusSlot === "today") {
        // AM only: set AM. PM is left untouched (additive).
        const result = await api.focusSet("today", { project_slug: projectSlug, intent_slug: intentSlug });
        onPicked?.(result);
      } else if (focusSlot === "today_pm") {
        // PM only: set PM. AM is left untouched (additive).
        const result = await api.focusSet("today_pm", { project_slug: projectSlug, intent_slug: intentSlug });
        onPicked?.(result);
      } else {
        const result = await api.focusSet(focusSlot, { project_slug: projectSlug, intent_slug: intentSlug });
        onPicked?.(result);
      }
      onClose();
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  const handleSlotChoice = (half: "all" | "am" | "pm") => {
    if (!pending) return;
    if (half === "all") submitFocus("all_day", pending.projectSlug, pending.intentSlug);
    else if (half === "am") submitFocus("today", pending.projectSlug, pending.intentSlug);
    else submitFocus("today_pm", pending.projectSlug, pending.intentSlug);
  };

  const backdropClass =
    "fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm";
  const cardClass =
    "w-full max-w-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]";
  const btnBack =
    "px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-700/50 rounded-md transition-colors disabled:opacity-50";

  // ── Step 2: When / AM / PM ────────────────────────────────────────────────
  if (onStep2 && pending) {
    // Context-aware sublabels so the user sees exactly what will change.
    const allDayNote = isAllDay
      ? "Replaces current all-day focus — sets both slots to this task"
      : hasAM || hasPM
        ? "Replaces current focus — sets both morning and afternoon"
        : "Sets both morning and afternoon for today";

    const amNote = isAllDay
      ? "Splits all-day — morning becomes this task, afternoon stays"
      : hasAM
        ? `Replaces morning focus${hasPM ? " (afternoon stays)" : ""}`
        : `Sets morning focus${hasPM ? " (afternoon stays)" : ""}`;

    const pmNote = isAllDay
      ? "Splits all-day — afternoon becomes this task, morning stays"
      : hasPM
        ? `Replaces afternoon focus${hasAM ? " (morning stays)" : ""}`
        : `Sets afternoon focus${hasAM ? " (morning stays)" : ""}`;

    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Choose when to focus"
        className={backdropClass}
        onClick={(e) => { if (e.target === e.currentTarget && !submitting) setPending(null); }}
      >
        <div className={cardClass}>
          <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">When will you work on this?</h2>
          </div>
          <div className="px-4 py-4 flex flex-col gap-3">
            {error && (
              <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-900/50 px-2.5 py-1.5 rounded text-[11px]">
                {error}
              </div>
            )}
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              <span className="font-semibold">{pending.projectTitle}</span>
              {" — "}
              {pending.intentTitle}
            </p>
            <div className="flex flex-col gap-2">
              {/* All day */}
              <button
                type="button"
                onClick={() => handleSlotChoice("all")}
                disabled={submitting}
                className={`w-full px-3 py-2.5 rounded-xl border-2 text-left disabled:opacity-50 transition-colors ${
                  isAllDay
                    ? "border-slate-500 dark:border-slate-400 bg-slate-100 dark:bg-slate-700/60 hover:bg-slate-200 dark:hover:bg-slate-700"
                    : "border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-700/40 hover:bg-slate-100 dark:hover:bg-slate-700"
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold text-slate-700 dark:text-slate-200">📅 All day</span>
                  {isAllDay && (
                    <span className="text-[9px] font-bold bg-slate-500 text-white rounded px-1 py-0.5 leading-none">current</span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">{allDayNote}</div>
              </button>
              {/* AM + PM side by side */}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleSlotChoice("am")}
                  disabled={submitting}
                  className={`flex-1 px-3 py-2.5 rounded-xl border-2 text-left disabled:opacity-50 transition-colors ${
                    hasAM && !isAllDay
                      ? "border-amber-500 dark:border-amber-400 bg-amber-100 dark:bg-amber-900/40 hover:bg-amber-150 dark:hover:bg-amber-900/60"
                      : "border-amber-200 dark:border-amber-700 bg-amber-50/60 dark:bg-amber-900/10 hover:bg-amber-100 dark:hover:bg-amber-900/30"
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-bold text-amber-800 dark:text-amber-300">☀️ Morning</span>
                    {hasAM && !isAllDay && (
                      <span className="text-[9px] font-bold bg-amber-500 text-white rounded px-1 py-0.5 leading-none">current</span>
                    )}
                  </div>
                  <div className="text-[10px] text-amber-700/70 dark:text-amber-400/70 mt-0.5">{amNote}</div>
                </button>
                <button
                  type="button"
                  onClick={() => handleSlotChoice("pm")}
                  disabled={submitting}
                  className={`flex-1 px-3 py-2.5 rounded-xl border-2 text-left disabled:opacity-50 transition-colors ${
                    hasPM && !isAllDay
                      ? "border-indigo-500 dark:border-indigo-400 bg-indigo-100 dark:bg-indigo-900/40 hover:bg-indigo-150 dark:hover:bg-indigo-900/60"
                      : "border-indigo-200 dark:border-indigo-700 bg-indigo-50/60 dark:bg-indigo-900/10 hover:bg-indigo-100 dark:hover:bg-indigo-900/30"
                  }`}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-bold text-indigo-800 dark:text-indigo-300">🌙 Afternoon</span>
                    {hasPM && !isAllDay && (
                      <span className="text-[9px] font-bold bg-indigo-500 text-white rounded px-1 py-0.5 leading-none">current</span>
                    )}
                  </div>
                  <div className="text-[10px] text-indigo-700/70 dark:text-indigo-400/70 mt-0.5">{pmNote}</div>
                </button>
              </div>
            </div>
          </div>
          <div className="px-4 py-3 bg-slate-50/70 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-700 flex justify-end">
            <button type="button" onClick={() => setPending(null)} disabled={submitting} className={btnBack}>
              ← Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Step 1: pick intent ───────────────────────────────────────────────────
  const title = slot === "today" ? "Pick today's focus" : "Pick this week's focus";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className={backdropClass}
      onClick={(e) => { if (e.target === e.currentTarget && !submitting) onClose(); }}
    >
      <div className={cardClass}>
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">{title}</h2>
        </div>
        <div className="px-4 py-3 flex flex-col gap-2 overflow-y-auto">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-900/50 px-2.5 py-1.5 rounded text-[11px]">
              {error}
            </div>
          )}
          {projects.length === 0 ? (
            <div className="text-xs text-slate-500 dark:text-slate-400 px-1 py-2">No active projects.</div>
          ) : (
            <ul className="flex flex-col gap-1">
              {projects.map((p) => {
                const expanded = expandedSlug === p.slug;
                const intents = intentsBySlug[p.slug];
                const loading = loadingSlug === p.slug;
                return (
                  <li key={p.slug} className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
                    <button
                      type="button"
                      onClick={() => handleExpand(p.slug)}
                      disabled={submitting}
                      aria-expanded={expanded}
                      className="w-full px-3 py-2 text-left flex items-center justify-between gap-2 text-xs font-semibold text-slate-800 dark:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-700/50 disabled:opacity-50"
                    >
                      <span className="truncate">{p.title}</span>
                      <span className="text-slate-400 dark:text-slate-500 text-[10px]">{expanded ? "▾" : "▸"}</span>
                    </button>
                    {expanded && (
                      <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-900/30">
                        {loading ? (
                          <div className="px-3 py-2 text-[11px] text-slate-500 dark:text-slate-400">Loading…</div>
                        ) : intents && intents.length > 0 ? (
                          <ul>
                            {intents.map((intent) => (
                              <li key={intent.id}>
                                <button
                                  type="button"
                                  onClick={() => handleIntentClick(p, intent)}
                                  disabled={submitting}
                                  className="w-full px-3 py-1.5 text-left text-[11px] text-slate-700 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 disabled:opacity-50 flex items-center gap-2"
                                >
                                  <span className="text-slate-400 dark:text-slate-500">›</span>
                                  <span className="truncate">{intent.title}</span>
                                </button>
                              </li>
                            ))}
                          </ul>
                        ) : intents ? (
                          <div className="px-3 py-2 text-[11px] text-slate-500 dark:text-slate-400">No intents.</div>
                        ) : null}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <div className="px-4 py-3 bg-slate-50/70 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-700 flex justify-end">
          <button type="button" onClick={onClose} disabled={submitting} className={btnBack}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
