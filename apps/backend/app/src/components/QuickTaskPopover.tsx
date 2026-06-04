import { useState } from 'react';
import { api, ApiError } from '@/api/client';
import { useQuickTasks } from '@/hooks/useQuickTasks';

interface Props {
  open: boolean;
  onClose: () => void;
}

const ACTION_BTN_STYLE: React.CSSProperties = { padding: '4px 8px', fontSize: 11 };
const SNOOZE_OPTIONS = [
  { label: '15m', until: '15m' },
  { label: '1h', until: '1h' },
  { label: 'Next block', until: 'next_block' },
];

/**
 * Floating Quick Task Stack panel anchored under the header ⚡ button.
 * Mirrors NotificationCenter's absolute popover. Lists the stack with
 * complete/snooze/delete and an inline "add a task" input (capped at 5).
 */
export function QuickTaskPopover({ open, onClose }: Props) {
  const qt = useQuickTasks(open);
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [snoozeFor, setSnoozeFor] = useState<string | null>(null);

  if (!open) return null;

  const data = qt.data;
  const active = data?.active ?? [];
  const snoozed = data?.snoozed ?? [];
  const limit = data?.limit ?? 5;
  const atCap = (data?.active_count ?? 0) >= limit;

  const add = async () => {
    const trimmed = text.trim();
    if (!trimmed) { setError('Type a quick task first.'); return; }
    setBusy(true);
    try {
      await api.quickTaskCreate(trimmed);
      setText('');
      setError(null);
      await qt.reload();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setError('Stack is full — complete, delete, or snooze one first.');
      } else {
        setError(e instanceof Error ? e.message : 'Could not add the quick task.');
      }
    } finally {
      setBusy(false);
    }
  };

  const handleSnooze = async (id: string, until: string) => {
    setSnoozeFor(null);
    await qt.snooze(id, until);
  };

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="panel absolute right-0 top-full mt-2 w-80 z-50 flex flex-col" role="dialog" aria-label="Quick Tasks">
        <div className="flex items-center justify-between px-4 pt-3 pb-2 shrink-0">
          <div className="flex items-center gap-2">
            <span className="eyebrow">Quick Tasks</span>
            {active.length > 0 && (
              <span className="chip chip-count tabular">{active.length}/{limit}</span>
            )}
          </div>
        </div>

        {/* inline add */}
        <div className="px-4 pb-2 shrink-0">
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={text}
              onChange={(e) => { setText(e.target.value); if (error) setError(null); }}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void add(); } }}
              placeholder={atCap ? 'Stack is full…' : 'A 2–5 min task to park…'}
              disabled={busy || atCap}
              className="flex-1 min-w-0 px-2.5 py-1.5 text-xs border border-hairline rounded bg-surface text-ink outline-none focus:border-accent disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => void add()}
              disabled={busy || atCap || text.trim() === ''}
              className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              style={ACTION_BTN_STYLE}
            >
              {busy ? 'Adding…' : 'Add'}
            </button>
          </div>
          {error && (
            <div className="mt-1.5 bg-critical-bg text-critical px-2.5 py-1.5 rounded text-[11px]" style={{ border: '1px solid rgba(200, 54, 42, 0.25)' }}>
              {error}
            </div>
          )}
        </div>

        {data?.return_blocked && (
          <div className="mx-4 mb-2 bg-critical-bg text-critical px-2.5 py-1.5 rounded text-[11px]" style={{ border: '1px solid rgba(200, 54, 42, 0.25)' }}>
            A snoozed quick task is ready — clear a slot.
          </div>
        )}

        {active.length > 0 ? (
          <ul className="flex-1 min-h-0 overflow-y-auto space-y-2 px-4 pb-2" style={{ maxHeight: '50vh' }}>
            {active.map((task, idx) => (
              <li key={task.id} className={`card ${idx === 0 ? 'stripe stripe-warning' : ''}`} style={{ padding: '8px 10px' }}>
                <div className="flex justify-between items-start gap-2">
                  <p className={`text-[13px] leading-snug text-ink min-w-0 flex-1 ${idx === 0 ? 'font-semibold' : ''}`}>{task.text}</p>
                  <div className="flex items-center gap-1 shrink-0">
                    <button type="button" onClick={() => qt.complete(task.id)} title="Complete" aria-label={`Complete ${task.id}`} className="btn" style={ACTION_BTN_STYLE}>✓</button>
                    <button type="button" onClick={() => setSnoozeFor(snoozeFor === task.id ? null : task.id)} title="Snooze" aria-label={`Snooze ${task.id}`} className="btn" style={ACTION_BTN_STYLE}>💤</button>
                    <button type="button" onClick={() => qt.remove(task.id)} title="Delete" aria-label={`Delete ${task.id}`} className="btn" style={ACTION_BTN_STYLE}>✕</button>
                  </div>
                </div>
                {snoozeFor === task.id && (
                  <div className="flex items-center gap-1.5 mt-2">
                    <span className="text-[10px] text-ink-4">Snooze for</span>
                    {SNOOZE_OPTIONS.map((opt) => (
                      <button key={opt.until} type="button" onClick={() => void handleSnooze(task.id, opt.until)} className="btn" style={ACTION_BTN_STYLE}>{opt.label}</button>
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
