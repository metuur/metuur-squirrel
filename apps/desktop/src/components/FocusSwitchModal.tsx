// Friendly "you're already checked in" confirm. Shown when the user taps Check
// in on a focus pick while a session is open for a *different* intent. We never
// auto-check-out (EARS R-4.4): the user must explicitly check out first, so this
// dialog offers a check-out action and a cancel — it does not chain into a new
// check-in.
import { useEffect, useState } from "react";

interface Props {
  open: boolean;
  currentTitle: string | null; // the task currently checked in
  nextTitle: string | null; // the task the user tried to switch to
  busy?: boolean; // checkout request in flight
  // Receives the optional "why I'm switching" note (null when left blank).
  onCheckoutCurrent: (note: string | null) => void;
  onCancel: () => void;
}

const BACKDROP_STYLE: React.CSSProperties = {
  background: "rgba(14, 17, 22, 0.45)",
};

export function FocusSwitchModal({
  open,
  currentTitle,
  nextTitle,
  busy = false,
  onCheckoutCurrent,
  onCancel,
}: Props) {
  // Optional "why I'm switching" note. Reset each time the dialog opens so a
  // previous note never leaks into the next switch.
  const [note, setNote] = useState("");
  useEffect(() => {
    if (open) setNote("");
  }, [open]);

  // Escape cancels (ignored while a checkout is in flight).
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, busy, onCancel]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Change task?"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
      style={BACKDROP_STYLE}
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onCancel();
      }}
    >
      <div className="panel w-full max-w-sm flex flex-col">
        <div className="px-4 py-3 border-b border-hairline">
          <h2 className="title text-sm">Change task?</h2>
        </div>
        <div className="px-4 py-3 flex flex-col gap-2.5 text-[12.5px] leading-relaxed text-ink-2">
          <p>
            You're already checked in
            {currentTitle ? (
              <>
                {" "}
                to <span className="text-ink-1 font-bold">{currentTitle}</span>
              </>
            ) : null}
            .
          </p>
          <p>
            Before we drop everything and sprint toward
            {nextTitle ? (
              <>
                {" "}
                <span className="text-ink-1 font-bold">{nextTitle}</span>
              </>
            ) : (
              " the next task"
            )}
            , let's do a quick sanity check.
          </p>
          <p>
            Is this a genuine priority shift, or did your brain just spot
            something newer, shinier, and significantly more exciting?
          </p>
          <p>
            No judgment either way. Just remember you'll need to{" "}
            <span className="text-ink-1 font-medium">check out</span> of the
            current task before chasing the next adventure.
          </p>
          <label className="flex flex-col gap-1 mt-0.5">
            <span className="text-[11px] text-ink-3">
              Why are you switching?{" "}
              <span className="text-ink-4">(optional — for future you)</span>
            </span>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={busy}
              rows={2}
              placeholder="e.g. blocked on review, deadline moved up…"
              className="w-full resize-none rounded border border-hairline bg-surface px-2 py-1.5 text-[12px] text-ink-1 outline-none focus:border-ink-3 disabled:opacity-50"
            />
          </label>
        </div>
        <div className="px-4 py-3 bg-surface-2 border-t border-hairline-2 flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="btn btn-ghost disabled:opacity-50"
          >
            Keep current task
          </button>
          <button
            type="button"
            onClick={() => onCheckoutCurrent(note.trim() ? note.trim() : null)}
            disabled={busy}
            className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? "Checking out…" : "Check out current task"}
          </button>
        </div>
      </div>
    </div>
  );
}
