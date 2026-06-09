// QuickTaskPopover — floating panel under the header ⚡ icon. Lists the Quick
// Task Stack with complete/snooze/delete and an "Add a task" button.
// Mirrors the NotificationCenter popover (backdrop + fixed panel at top-12).

import { useState } from "react";
import { useQuickTasks } from "../hooks/useQuickTasks";

interface Props {
  open: boolean;
  onClose: () => void;
  online: boolean;
  refreshSignal: number;
  /** Opens the capture modal (the "Add a task" button). */
  onAdd: () => void;
}

const ACTION_BTN_STYLE: React.CSSProperties = { padding: "4px 8px", fontSize: 11 };
const SNOOZE_OPTIONS = [
  { label: "15m", until: "15m" },
  { label: "1h", until: "1h" },
  { label: "Next block", until: "next_block" },
];

export function QuickTaskPopover({ open, onClose, online, refreshSignal, onAdd }: Props) {
  const qt = useQuickTasks(refreshSignal);
  const [snoozeFor, setSnoozeFor] = useState<string | null>(null);

  if (!open) return null;

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
    <>
      {/* Backdrop — closes the popover on outside click */}
      <div className="fixed inset-0 z-40" onClick={onClose} />

      {/* Floating panel under the header icons */}
      <div
        className="fixed inset-x-3 top-12 z-50 panel flex flex-col"
        style={{ maxHeight: "calc(100vh - 3.5rem)" }}
        role="dialog"
        aria-label="Quick Tasks"
      >
        <div className="flex items-center justify-between px-4 pt-3 pb-2 shrink-0">
          <div className="flex items-center gap-2">
            <span className="eyebrow">Quick Tasks</span>
            {active.length > 0 && (
              <span className="chip chip-count tabular">{active.length}/{limit}</span>
            )}
          </div>
          <button
            type="button"
            onClick={onAdd}
            disabled={!online || atCap}
            title={atCap ? "Stack is full — complete, delete, or snooze one first" : "Add a quick task"}
            className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            style={ACTION_BTN_STYLE}
          >
            + Add a task
          </button>
        </div>

        {data?.return_blocked && (
          <div
            className="mx-4 mb-2 bg-critical-bg text-critical px-2.5 py-1.5 rounded text-[11px]"
            style={{ border: "1px solid rgba(200, 54, 42, 0.25)" }}
          >
            A snoozed quick task is ready — clear a slot.
          </div>
        )}

        {active.length > 0 ? (
          <ul className="flex-1 min-h-0 overflow-y-auto space-y-2 px-4 pb-2">
            {active.map((task, idx) => (
              <li
                key={task.id}
                className={`card ${idx === 0 ? "stripe stripe-warning" : ""}`}
                style={{ padding: "8px 10px" }}
              >
                <div className="flex justify-between items-start gap-2">
                  <p className={`title text-[13px] leading-snug min-w-0 flex-1 ${idx === 0 ? "font-semibold" : ""}`}>
                    {task.text}
                  </p>
                  <div className="flex items-center gap-1 shrink-0">
                    <button type="button" onClick={() => online && qt.complete(task.id)} disabled={!online}
                      title="Complete" aria-label={`Complete ${task.id}`} className="btn" style={ACTION_BTN_STYLE}>✓</button>
                    <button type="button" onClick={() => setSnoozeFor(snoozeFor === task.id ? null : task.id)} disabled={!online}
                      title="Snooze" aria-label={`Snooze ${task.id}`} className="btn" style={ACTION_BTN_STYLE}>💤</button>
                    <button type="button" onClick={() => online && qt.remove(task.id)} disabled={!online}
                      title="Delete" aria-label={`Delete ${task.id}`} className="btn" style={ACTION_BTN_STYLE}>✕</button>
                  </div>
                </div>
                {snoozeFor === task.id && (
                  <div className="flex items-center gap-1.5 mt-2">
                    <span className="text-[10px] text-ink-4">Snooze for</span>
                    {SNOOZE_OPTIONS.map((opt) => (
                      <button key={opt.until} type="button" onClick={() => handleSnooze(task.id, opt.until)}
                        className="btn" style={ACTION_BTN_STYLE}>{opt.label}</button>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        ) : data ? (
          <div className="px-4 pb-3 text-xs text-ink-3">No quick tasks parked.</div>
        ) : (
          <div className="px-4 pb-3 text-xs text-ink-4">—</div>
        )}

        {snoozed.length > 0 && (
          <div className="px-4 pb-3 text-[10px] text-ink-4 shrink-0">{snoozed.length} snoozed</div>
        )}
      </div>
    </>
  );
}
