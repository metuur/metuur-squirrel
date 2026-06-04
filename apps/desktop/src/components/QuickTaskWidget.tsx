// QuickTaskWidget — the always-visible Quick Task Stack (R-5.3, R-5.4).
//
// Renders the FIFO stack (oldest at top, emphasized) with per-row
// ✓ Complete · 💤 Snooze · ✕ Delete, a snoozed section, a return-blocked
// banner, and an Add button that is disabled at the hard cap.

import { useState } from "react";
import { useQuickTasks } from "../hooks/useQuickTasks";

interface Props {
  online: boolean;
  /** Bumped by the parent to force a refetch (e.g. after a capture). */
  refreshSignal: number;
  /** Opens the capture modal (Add button). */
  onAdd: () => void;
}

const ACTION_BTN_STYLE: React.CSSProperties = { padding: "4px 8px", fontSize: 11 };

const SNOOZE_OPTIONS: { label: string; until: string }[] = [
  { label: "15m", until: "15m" },
  { label: "1h", until: "1h" },
  { label: "Next block", until: "next_block" },
];

export function QuickTaskWidget({ online, refreshSignal, onAdd }: Props) {
  const qt = useQuickTasks(refreshSignal);
  const [snoozeFor, setSnoozeFor] = useState<string | null>(null);
  const dimmed = !online;

  const data = qt.data;
  const active = data?.active ?? [];
  const snoozed = data?.snoozed ?? [];
  const limit = data?.limit ?? 5;
  const atCap = (data?.active_count ?? 0) >= limit;

  const handleSnooze = async (id: string, until: string) => {
    setSnoozeFor(null);
    if (online) await qt.snooze(id, until);
  };

  return (
    <section className={`px-4 pt-3 ${dimmed ? "opacity-50" : ""}`} aria-label="Quick Tasks">
      <div className="flex items-center justify-between mb-2 px-0.5">
        <div className="flex items-center gap-2">
          <span className="eyebrow">Quick Tasks</span>
          {active.length > 0 && (
            <span className="chip chip-count tabular">
              {active.length}/{limit}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onAdd}
          disabled={!online || atCap}
          title={atCap ? "Stack is full — complete, delete, or snooze one first" : "Add a quick task"}
          className="btn disabled:opacity-50 disabled:cursor-not-allowed"
          style={ACTION_BTN_STYLE}
        >
          + Add
        </button>
      </div>

      {data?.return_blocked && (
        <div
          className="bg-critical-bg text-critical px-2.5 py-1.5 rounded text-[11px] mb-2"
          style={{ border: "1px solid rgba(200, 54, 42, 0.25)" }}
        >
          A snoozed quick task is ready — clear a slot.
        </div>
      )}

      {active.length > 0 ? (
        <ul className="space-y-2">
          {active.map((task, idx) => (
            <li
              key={task.id}
              data-quick-task-id={task.id}
              className={`card ${idx === 0 ? "stripe stripe-warning" : ""}`}
              style={{ padding: "8px 10px" }}
            >
              <div className="flex justify-between items-start gap-2">
                <p
                  className={`title text-[13px] leading-snug min-w-0 flex-1 ${
                    idx === 0 ? "font-semibold" : ""
                  }`}
                >
                  {task.text}
                </p>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={() => online && qt.complete(task.id)}
                    disabled={!online}
                    title="Complete"
                    aria-label={`Complete ${task.id}`}
                    className="btn"
                    style={ACTION_BTN_STYLE}
                  >
                    ✓
                  </button>
                  <button
                    type="button"
                    onClick={() => setSnoozeFor(snoozeFor === task.id ? null : task.id)}
                    disabled={!online}
                    title="Snooze"
                    aria-label={`Snooze ${task.id}`}
                    className="btn"
                    style={ACTION_BTN_STYLE}
                  >
                    💤
                  </button>
                  <button
                    type="button"
                    onClick={() => online && qt.remove(task.id)}
                    disabled={!online}
                    title="Delete"
                    aria-label={`Delete ${task.id}`}
                    className="btn"
                    style={ACTION_BTN_STYLE}
                  >
                    ✕
                  </button>
                </div>
              </div>
              {snoozeFor === task.id && (
                <div className="flex items-center gap-1.5 mt-2">
                  <span className="text-[10px] text-ink-4">Snooze for</span>
                  {SNOOZE_OPTIONS.map((opt) => (
                    <button
                      key={opt.until}
                      type="button"
                      onClick={() => handleSnooze(task.id, opt.until)}
                      className="btn"
                      style={ACTION_BTN_STYLE}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      ) : data ? (
        <div className="text-xs text-ink-3 px-1">No quick tasks parked.</div>
      ) : (
        <div className="text-xs text-ink-4 px-1">—</div>
      )}

      {snoozed.length > 0 && (
        <div className="mt-2 px-1 text-[10px] text-ink-4">
          {snoozed.length} snoozed
        </div>
      )}
    </section>
  );
}
