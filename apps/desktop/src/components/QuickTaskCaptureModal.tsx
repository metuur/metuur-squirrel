// QuickTaskCaptureModal — minimal one-line capture box for a Quick Task.
// EARS R-1.1 (single-line input, Enter submits), R-1.3 (empty rejected),
// R-2.4 (stays open with an inline message when the stack is full).

import { useEffect, useRef, useState } from "react";

interface Props {
  open: boolean;
  error: string | null;
  busy: boolean;
  /** Returns true on success (modal closes via the hook). */
  onSubmit: (text: string) => Promise<boolean>;
  onClose: () => void;
}

const BACKDROP_STYLE: React.CSSProperties = {
  background: "rgba(14, 17, 22, 0.45)",
};

export function QuickTaskCaptureModal({ open, error, busy, onSubmit, onClose }: Props) {
  const [text, setText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setText("");
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  if (!open) return null;

  const handleSubmit = async () => {
    const ok = await onSubmit(text);
    if (ok) setText("");
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Add Quick Task"
      className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-24 backdrop-blur-sm"
      style={BACKDROP_STYLE}
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div className="panel w-full max-w-sm flex flex-col">
        <div className="px-4 py-3 border-b border-hairline">
          <h2 className="title text-sm">⚡ Add Quick Task</h2>
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
          <input
            ref={inputRef}
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="A 2–5 min task to park…"
            disabled={busy}
            className="bg-surface-2 text-ink border border-hairline rounded-lg px-2.5 py-2 text-xs outline-none disabled:opacity-50"
            style={{ fontFamily: "var(--font-sans)" }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void handleSubmit();
              } else if (e.key === "Escape") {
                e.preventDefault();
                if (!busy) onClose();
              }
            }}
          />
        </div>
        <div className="px-4 py-3 bg-surface-2 border-t border-hairline-2 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="btn btn-ghost disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void handleSubmit()}
            disabled={busy || text.trim() === ""}
            className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? "Adding…" : "Add"}
          </button>
        </div>
      </div>
    </div>
  );
}
