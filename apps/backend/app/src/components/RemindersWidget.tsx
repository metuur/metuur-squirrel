import { useState } from 'react';
import { useFetch } from '@/hooks/useFetch';
import { api, type ReminderItem, type RemindersPayload } from '@/api/client';

export function RemindersWidget() {
  const { data, isLoading } = useFetch('reminders', () => api.reminders());
  const [local, setLocal] = useState<RemindersPayload | null>(null);

  // Once data arrives, seed local state (only once per fetch)
  const lists = local ?? data ?? null;

  if (isLoading && !data) return null;
  if (!lists) return null;
  if (lists.approaching.length === 0 && lists.active.length === 0) return null;

  function dismissItem(id: string) {
    if (!lists) return;
    const next: RemindersPayload = {
      approaching: lists.approaching.filter((r) => r.id !== id),
      active: lists.active.filter((r) => r.id !== id),
    };
    setLocal(next);
    api.reminderDismiss(id).catch(() => {});
  }

  function snoozeItem(id: string, until: string) {
    if (!lists) return;
    const next: RemindersPayload = {
      approaching: lists.approaching,
      active: lists.active.filter((r) => r.id !== id),
    };
    setLocal(next);
    api.reminderSnooze(id, until).catch(() => {});
  }

  return (
    <div className="mb-6 space-y-4">
      {lists.approaching.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-icons text-base text-slate-400">notifications_none</span>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              On your radar
            </h2>
            <span className="text-[10px] font-bold text-slate-400">({lists.approaching.length})</span>
          </div>
          <div className="space-y-2">
            {lists.approaching.map((item) => (
              <ApproachingRow key={item.id} item={item} />
            ))}
          </div>
        </section>
      )}

      {lists.active.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <span className="material-icons text-base text-amber-500">notifications_active</span>
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Reminder due
            </h2>
            <span className="text-[10px] font-bold text-slate-400">({lists.active.length})</span>
          </div>
          <div className="space-y-2">
            {lists.active.map((item) => (
              <ActiveRow key={item.id} item={item} onDismiss={dismissItem} onSnooze={snoozeItem} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function ApproachingRow({ item }: { item: ReminderItem }) {
  return (
    <div className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-mono text-slate-400 mb-0.5">{item.id}</div>
          <h3 className="font-medium text-slate-900 dark:text-slate-100 truncate">{item.title}</h3>
          {item.proyecto && (
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{item.proyecto}</div>
          )}
        </div>
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300 whitespace-nowrap">
          <span className="material-icons text-sm">event</span>
          {item.reminder_date}
        </span>
      </div>
    </div>
  );
}

function ActiveRow({
  item,
  onDismiss,
  onSnooze,
}: {
  item: ReminderItem;
  onDismiss: (id: string) => void;
  onSnooze: (id: string, until: string) => void;
}) {
  const [showSnooze, setShowSnooze] = useState(false);
  const [snoozeDate, setSnoozeDate] = useState('');
  const today = new Date().toISOString().split('T')[0];

  function handleSnoozeConfirm() {
    if (!snoozeDate) return;
    onSnooze(item.id, snoozeDate);
    setShowSnooze(false);
    setSnoozeDate('');
  }

  return (
    <div className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-xl p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-mono text-slate-400 mb-0.5">{item.id}</div>
          <h3 className="font-medium text-slate-900 dark:text-slate-100 truncate">{item.title}</h3>
          {item.proyecto && (
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{item.proyecto}</div>
          )}
          <div className="text-xs text-amber-600 dark:text-amber-400 mt-1">Due {item.reminder_date}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => onDismiss(item.id)}
            className="text-xs font-semibold px-2.5 py-1 rounded-lg border border-border-light dark:border-border-dark text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            Dismiss
          </button>
          <button
            onClick={() => setShowSnooze((v) => !v)}
            className="text-xs font-semibold px-2.5 py-1 rounded-lg border border-border-light dark:border-border-dark text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            Snooze
          </button>
        </div>
      </div>

      {showSnooze && (
        <div className="mt-3 flex items-center gap-2">
          <input
            type="date"
            min={today}
            value={snoozeDate}
            onChange={(e) => setSnoozeDate(e.target.value)}
            className="text-xs border border-border-light dark:border-border-dark rounded-lg px-2 py-1 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <button
            onClick={handleSnoozeConfirm}
            disabled={!snoozeDate}
            className="text-xs font-semibold px-3 py-1 rounded-lg bg-primary text-white hover:bg-primary/90 disabled:opacity-40 transition-colors"
          >
            Set
          </button>
          <button
            onClick={() => { setShowSnooze(false); setSnoozeDate(''); }}
            className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
