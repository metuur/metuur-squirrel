// Phase 2 FocusPickerModal — Story 6.1. Modal overlay used by FocusWidget
// to let the user pick (or clear) a manual focus for the today/week slot.
// EARS R-6.1..R-6.8.
//
// - R-6.2: project list comes from the parent's cached /api/home.projects[];
//   no extra fetch at open time.
// - R-6.3: expanding a project row fetches /api/projects/{slug} ONCE per
//   modal session, cached in modal-local state. Re-expand of the same
//   project does NOT refetch.
// - R-6.4 / R-6.6: PUT /api/focus/{slot} via api.focusSet; on 2xx close the
//   modal and notify the parent via onPicked.
// - R-6.5: on non-2xx, stay open, show server `error` field inline, preserve
//   the user's expanded project so they can retry without re-navigation.
// - R-6.7: Cancel closes without any network request.
// - R-6.8: modal-session cache lives in useState ⇒ unmounts clear it.

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

export function FocusPickerModal({ slot, projects, onClose, onPicked }: Props) {
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
  const [intentsBySlug, setIntentsBySlug] = useState<
    Record<string, ProjectNote[]>
  >({});
  const [loadingSlug, setLoadingSlug] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const slotLabel = slot === "today" ? "Today" : "This week";

  // Escape closes the modal (R-6.7 by convention — no network).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !submitting) {
        onClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose, submitting]);

  const handleExpand = async (slug: string) => {
    if (submitting) return;
    if (expandedSlug === slug) {
      setExpandedSlug(null);
      return;
    }
    setExpandedSlug(slug);
    // R-6.3: only fetch the first time we expand a given slug per session.
    if (intentsBySlug[slug]) return;
    setLoadingSlug(slug);
    setError(null);
    try {
      const detail = await api.projectDetail(slug);
      setIntentsBySlug((prev) => ({ ...prev, [slug]: detail.notes }));
    } catch (err) {
      const msg =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : String(err);
      setError(msg);
    } finally {
      setLoadingSlug((cur) => (cur === slug ? null : cur));
    }
  };

  const handlePick = async (projectSlug: string, intentSlug: string) => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.focusSet(slot, {
        project_slug: projectSlug,
        intent_slug: intentSlug,
      });
      onPicked?.(result);
      onClose();
    } catch (err) {
      const msg =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : String(err);
      setError(msg);
      setSubmitting(false);
    }
  };

  const handleClear = async () => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.focusSet(slot, { clear: true });
      onPicked?.(result);
      onClose();
    } catch (err) {
      const msg =
        err instanceof ApiError || err instanceof Error
          ? err.message
          : String(err);
      setError(msg);
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (submitting) return;
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Pick ${slotLabel.toLowerCase()}'s focus`}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleCancel();
      }}
    >
      <div className="w-full max-w-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
            Pick {slotLabel.toLowerCase()}'s focus
          </h2>
        </div>
        <div className="px-4 py-3 flex flex-col gap-2 overflow-y-auto">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-900/50 px-2.5 py-1.5 rounded text-[11px]">
              {error}
            </div>
          )}
          {projects.length === 0 ? (
            <div className="text-xs text-slate-500 dark:text-slate-400 px-1 py-2">
              No active projects.
            </div>
          ) : (
            <ul className="flex flex-col gap-1">
              {projects.map((p) => {
                const expanded = expandedSlug === p.slug;
                const intents = intentsBySlug[p.slug];
                const loading = loadingSlug === p.slug;
                return (
                  <li
                    key={p.slug}
                    className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden"
                  >
                    <button
                      type="button"
                      onClick={() => handleExpand(p.slug)}
                      disabled={submitting}
                      aria-expanded={expanded}
                      className="w-full px-3 py-2 text-left flex items-center justify-between gap-2 text-xs font-semibold text-slate-800 dark:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-700/50 disabled:opacity-50"
                    >
                      <span className="truncate">{p.title}</span>
                      <span className="text-slate-400 dark:text-slate-500 text-[10px]">
                        {expanded ? "▾" : "▸"}
                      </span>
                    </button>
                    {expanded && (
                      <div className="border-t border-slate-200 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-900/30">
                        {loading ? (
                          <div className="px-3 py-2 text-[11px] text-slate-500 dark:text-slate-400">
                            Loading…
                          </div>
                        ) : intents && intents.length > 0 ? (
                          <ul>
                            {intents.map((intent) => (
                              <li key={intent.id}>
                                <button
                                  type="button"
                                  onClick={() => handlePick(p.slug, intent.id)}
                                  disabled={submitting}
                                  className="w-full px-3 py-1.5 text-left text-[11px] text-slate-700 dark:text-slate-200 hover:bg-white dark:hover:bg-slate-800 disabled:opacity-50 flex items-center gap-2"
                                >
                                  <span className="text-slate-400 dark:text-slate-500">
                                    ›
                                  </span>
                                  <span className="truncate">
                                    {intent.title}
                                  </span>
                                </button>
                              </li>
                            ))}
                          </ul>
                        ) : intents ? (
                          <div className="px-3 py-2 text-[11px] text-slate-500 dark:text-slate-400">
                            No intents.
                          </div>
                        ) : null}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <div className="px-4 py-3 bg-slate-50/70 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={handleClear}
            disabled={submitting}
            className="px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-700/50 rounded-md transition-colors disabled:opacity-50"
          >
            Clear current pick
          </button>
          <button
            type="button"
            onClick={handleCancel}
            disabled={submitting}
            className="px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-700/50 rounded-md transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
