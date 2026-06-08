// Friendly "you're already checked in" confirm. Shown when the user taps Check
// in on a focus pick while a session is open for a *different* intent. We never
// auto-check-out (EARS R-4.4): the user must explicitly check out first, so this
// dialog offers a check-out action and a cancel — it does not chain into a new
// check-in.
import { useEffect } from "react";

interface Props {
  open: boolean;
  currentTitle: string | null; // the task currently checked in
  nextTitle: string | null; // the task the user tried to switch to
  busy?: boolean; // checkout request in flight
  onCheckoutCurrent: () => void;
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
                to <span className="text-ink-1 font-medium">{currentTitle}</span>
              </>
            ) : null}
            .
          </p>
          <p>
            Do you really want to change task? Double-check it's really necessary —
            if it is, that's fine. You just need to{" "}
            <span className="text-ink-1 font-medium">check out</span> the current
            task before checking into
            {nextTitle ? (
              <>
                {" "}
                <span className="text-ink-1 font-medium">{nextTitle}</span>
              </>
            ) : (
              " a new one"
            )}
            .
          </p>
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
            onClick={onCheckoutCurrent}
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
