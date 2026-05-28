// Phase 2 CaptureModal — multi-line textarea + Save / Cancel.
// EARS R-3.4 (POST /api/notes), R-3.5 (close+toast on 2xx),
// R-3.6 (keep open + inline error + preserve input on non-2xx).

import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useToast } from "./Toast";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CaptureModal({ open, onClose }: Props) {
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const toast = useToast();

  useEffect(() => {
    if (open) {
      setError(null);
      // Defer focus until the textarea is mounted in the DOM.
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  }, [open]);

  if (!open) return null;

  const handleSave = async () => {
    const trimmed = text.trim();
    if (trimmed === "") return;
    setSaving(true);
    setError(null);
    try {
      await api.noteCreate(trimmed, null);
      setText("");
      setSaving(false);
      onClose();
      toast.show("Captured to inbox");
    } catch (err) {
      setSaving(false);
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      // R-3.6: do not clear input.
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
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
        fontFamily: "system-ui, sans-serif",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleCancel();
      }}
    >
      <div
        style={{
          background: "#1e293b",
          border: "1px solid #334155",
          borderRadius: 8,
          padding: 16,
          width: "min(420px, calc(100% - 32px))",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <h2 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>Capture</h2>
        {error && (
          <div
            style={{
              background: "#7f1d1d",
              color: "#fee2e2",
              padding: "6px 10px",
              borderRadius: 4,
              fontSize: 12,
            }}
          >
            {error}
          </div>
        )}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="What's on your mind?"
          rows={5}
          disabled={saving}
          style={{
            background: "#0f172a",
            color: "#f1f5f9",
            border: "1px solid #334155",
            borderRadius: 4,
            padding: 8,
            fontSize: 13,
            fontFamily: "inherit",
            resize: "vertical",
            outline: "none",
          }}
        />
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button
            type="button"
            onClick={handleCancel}
            disabled={saving}
            style={{
              background: "transparent",
              border: "1px solid #475569",
              color: "#cbd5e1",
              padding: "6px 14px",
              borderRadius: 4,
              fontSize: 13,
              cursor: saving ? "not-allowed" : "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || text.trim() === ""}
            style={{
              background: "#2563eb",
              border: "1px solid #2563eb",
              color: "white",
              padding: "6px 14px",
              borderRadius: 4,
              fontSize: 13,
              cursor: saving || text.trim() === "" ? "not-allowed" : "pointer",
              opacity: saving || text.trim() === "" ? 0.6 : 1,
            }}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
