// PostItCaptureModal — capture box for a Post-it note.
// EARS R-4.3 (trigger in popup), R-4.4 (text + color → POST /api/post-its,
// empty text → no submit).

import { useEffect, useRef, useState } from "react";

interface Props {
  open: boolean;
  error: string | null;
  busy: boolean;
  /** Returns true on success (modal closes via the hook). */
  onSubmit: (text: string, color: string) => Promise<boolean>;
  onClose: () => void;
}

const COLOR_MAP: Record<string, string> = {
  yellow: "#fef08a",
  pink: "#f9a8d4",
  blue: "#93c5fd",
  green: "#86efac",
  orange: "#fdba74",
  purple: "#c4b5fd",
  white: "#f8fafc",
};

const COLOR_KEYS = Object.keys(COLOR_MAP) as Array<keyof typeof COLOR_MAP>;

const BACKDROP_STYLE: React.CSSProperties = {
  background: "rgba(14, 17, 22, 0.45)",
};

export function PostItCaptureModal({ open, error, busy, onSubmit, onClose }: Props) {
  const [text, setText] = useState("");
  const [selectedColor, setSelectedColor] = useState("yellow");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setText("");
      setSelectedColor("yellow");
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  if (!open) return null;

  const handleSubmit = async () => {
    const ok = await onSubmit(text, selectedColor);
    if (ok) setText("");
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Add Post-it"
      className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-24 backdrop-blur-sm"
      style={BACKDROP_STYLE}
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <div className="panel w-full max-w-sm flex flex-col">
        <div className="px-4 py-3 border-b border-hairline">
          <h2 className="title text-sm">📝 Add Post-it</h2>
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
            placeholder="What's on your mind…"
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
          {/* Color swatches */}
          <div className="flex items-center gap-1.5">
            {COLOR_KEYS.map((key) => (
              <button
                key={key}
                type="button"
                title={key}
                aria-label={`Color: ${key}`}
                aria-pressed={selectedColor === key}
                disabled={busy}
                onClick={() => setSelectedColor(key)}
                className="w-5 h-5 rounded-full shrink-0 disabled:opacity-50"
                style={{
                  background: COLOR_MAP[key],
                  outline: selectedColor === key ? "2px solid var(--ink, #1a1a1a)" : "none",
                  outlineOffset: 1,
                  border: "1px solid rgba(0,0,0,0.12)",
                }}
              />
            ))}
          </div>
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
