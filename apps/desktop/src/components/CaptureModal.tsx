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

const BACKDROP_STYLE: React.CSSProperties = {
  background: "rgba(14, 17, 22, 0.45)",
};

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
      className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
      style={BACKDROP_STYLE}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleCancel();
      }}
    >
      <div className="panel w-full max-w-sm flex flex-col">
        <div className="px-4 py-3 border-b border-hairline">
          <h2 className="title text-sm">Capture</h2>
        </div>
        <div className="px-4 py-3 flex flex-col gap-3">
          {error && (
            <div
              className="bg-critical-bg text-critical px-2.5 py-1.5 rounded text-[11px]"
              style={{ border: "1px solid rgba(200, 54, 42, 0.25)" }}
            >
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
            className="bg-surface-2 text-ink border border-hairline rounded-lg px-2.5 py-2 text-xs resize-y outline-none disabled:opacity-50"
            style={{ fontFamily: "var(--font-sans)" }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "var(--color-accent)";
              e.currentTarget.style.boxShadow = "0 0 0 3px rgba(31, 58, 138, 0.20)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "";
              e.currentTarget.style.boxShadow = "";
            }}
          />
        </div>
        <div className="px-4 py-3 bg-surface-2 border-t border-hairline-2 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={handleCancel}
            disabled={saving}
            className="btn btn-ghost disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || text.trim() === ""}
            className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
