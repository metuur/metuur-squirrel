import { useEffect, useState } from "react";
import {
  ApiError,
  api,
  type ManualFocusPayload,
  type ProjectListItem,
  type ProjectNote,
} from "../api/client";

interface Props {
  slot: "today" | "week";
  projects: ProjectListItem[];
  onClose: () => void;
  onPicked?: (result: ManualFocusPayload) => void;
}

interface PendingIntent {
  projectSlug: string;
  projectTitle: string;
  intentSlug: string;
  intentTitle: string;
}

export function FocusPickerModal({ slot, projects, onClose, onPicked }: Props) {
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
  const [intentsBySlug, setIntentsBySlug] = useState<Record<string, ProjectNote[]>>({});
  const [loadingSlug, setLoadingSlug] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState<PendingIntent | null>(null);

  const onStep2 = slot === "today" && pending !== null;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !submitting) {
        if (onStep2) {
          setPending(null);
        } else {
          onClose();
        }
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
    focusSlot: "today" | "today_pm" | "week",
    projectSlug: string,
    intentSlug: string,
  ) => {
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.focusSet(focusSlot, { project_slug: projectSlug, intent_slug: intentSlug });
      onPicked?.(result);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  const handleSlotChoice = (half: "am" | "pm") => {
    if (!pending) return;
    submitFocus(half === "pm" ? "today_pm" : "today", pending.projectSlug, pending.intentSlug);
  };

  const backdropClass =
    "fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm";
  const cardClass =
    "w-full max-w-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]";
  const btnBase =
    "px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-700/50 rounded-md transition-colors disabled:opacity-50";

  // ── Step 2: AM / PM choice ────────────────────────────────────────────────
  if (onStep2 && pending) {
    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Choose morning or afternoon"
        className={backdropClass}
        onClick={(e) => { if (e.target === e.currentTarget && !submitting) setPending(null); }}
      >
        <div className={cardClass}>
          <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
            <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
              Morning or afternoon?
            </h2>
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
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => handleSlotChoice("am")}
                disabled={submitting}
                className="flex-1 py-3 rounded-xl border-2 border-amber-300 dark:border-amber-600 bg-amber-50 dark:bg-amber-900/20 text-sm font-bold text-amber-800 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/40 disabled:opacity-50 transition-colors"
              >
                ☀️ Morning
                <div className="text-[10px] font-normal opacity-70 mt-0.5">AM</div>
              </button>
              <button
                type="button"
                onClick={() => handleSlotChoice("pm")}
                disabled={submitting}
                className="flex-1 py-3 rounded-xl border-2 border-indigo-300 dark:border-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 text-sm font-bold text-indigo-800 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 disabled:opacity-50 transition-colors"
              >
                🌙 Afternoon
                <div className="text-[10px] font-normal opacity-70 mt-0.5">PM</div>
              </button>
            </div>
          </div>
          <div className="px-4 py-3 bg-slate-50/70 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-700 flex justify-end">
            <button
              type="button"
              onClick={() => setPending(null)}
              disabled={submitting}
              className={btnBase}
            >
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
          <button type="button" onClick={onClose} disabled={submitting} className={btnBase}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
