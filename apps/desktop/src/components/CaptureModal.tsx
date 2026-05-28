// Phase 2 CaptureModal — multi-line textarea + project chip selector +
// Save / Cancel. EARS R-3.4 (POST /api/notes), R-3.5 (close+toast on 2xx),
// R-3.6 (keep open + inline error + preserve input on non-2xx).
//
// Supersedes original R-3.4 wording: project_slug is now whatever the user
// picked in the ProjectSelector (defaults to null = Inbox).

import { useEffect, useRef, useState } from "react";
import { api, type ProjectListItem } from "../api/client";
import { useToast } from "./Toast";
import { ProjectSelector } from "./ProjectSelector";

interface Props {
  open: boolean;
  onClose: () => void;
  projects: ProjectListItem[];
  focusSlug: string | null;
  /** Pre-selected project when the modal opens (e.g. user clicked a project
   *  shortcut). null = Inbox. */
  initialSlug?: string | null;
}

export function CaptureModal({ open, onClose, projects, focusSlug, initialSlug }: Props) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(initialSlug ?? null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setError(null);
      setSelectedSlug(initialSlug ?? null);
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  }, [open, initialSlug]);

  if (!open) return null;

  const handleSave = async () => {
    const trimmed = text.trim();
    if (trimmed === "") return;
    setSaving(true);
    setError(null);
    try {
      await api.noteCreate(trimmed, selectedSlug);
      setText("");
      setSaving(false);
      onClose();
      toast.show(
        selectedSlug ? `Captured to ${selectedSlug}` : "Captured to inbox",
      );
    } catch (err) {
      setSaving(false);
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
    }
  };

  const handleCancel = () => {
    if (saving) return;
    setText("");
    setError(null);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleCancel();
      }}
    >
      <div className="w-full max-w-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">Capture</h2>
        </div>
        <div className="px-4 py-3 flex flex-col gap-3">
          {error && (
            <div className="bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-200 border border-red-200 dark:border-red-900/50 px-2.5 py-1.5 rounded text-[11px]">
              {error}
            </div>
          )}
          <ProjectSelector
            projects={projects}
            focusSlug={focusSlug}
            selectedSlug={selectedSlug}
            onSelect={setSelectedSlug}
          />
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="What's on your mind?"
            rows={5}
            disabled={saving}
            className="bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-2 text-xs font-sans resize-y outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50"
          />
        </div>
        <div className="px-4 py-3 bg-slate-50/70 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-700 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={handleCancel}
            disabled={saving}
            className="px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-700/50 rounded-md transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || text.trim() === ""}
            className="px-3 py-1.5 text-xs font-semibold text-white bg-primary hover:bg-primary-dark disabled:bg-slate-300 disabled:text-slate-500 dark:disabled:bg-slate-700 dark:disabled:text-slate-500 rounded-md transition-colors"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
