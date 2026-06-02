import { useState } from 'react';
import { useFetch } from '@/hooks/useFetch';
import { api, type ReminderItem, type RemindersPayload } from '@/api/client';

export function RemindersWidget() {
  const { data, isLoading } = useFetch('reminders', () => api.reminders());
  const [local, setLocal] = useState<RemindersPayload | null>(null);

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
            <span className="material-icons text-base text-ink-4">notifications_none</span>
            <h2 className="eyebrow">On your radar</h2>
            <span className="text-[10px] font-bold text-ink-4">({lists.approaching.length})</span>
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
            <span className="material-icons text-base text-warning">notifications_active</span>
            <h2 className="eyebrow">Reminder due</h2>
            <span className="text-[10px] font-bold text-ink-4">({lists.active.length})</span>
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
    <div className="panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-mono text-ink-4 mb-0.5">{item.id}</div>
          <h3 className="font-medium text-ink truncate">{item.title}</h3>
          {item.project && (
            <div className="text-xs text-ink-3 mt-0.5">{item.project}</div>
          )}
        </div>
        <span className="chip whitespace-nowrap">
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
    <div className="panel p-4 stripe stripe-warning">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-mono text-ink-4 mb-0.5">{item.id}</div>
          <h3 className="font-medium text-ink truncate">{item.title}</h3>
          {item.project && (
            <div className="text-xs text-ink-3 mt-0.5">{item.project}</div>
          )}
          <div className="text-xs text-warning mt-1">Due {item.reminder_date}</div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => onDismiss(item.id)}
            className="btn text-xs font-semibold px-2.5 py-1"
          >
            Dismiss
          </button>
          <button
            onClick={() => setShowSnooze((v) => !v)}
            className="btn text-xs font-semibold px-2.5 py-1"
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
            className="text-xs border border-hairline rounded-lg px-2 py-1 bg-surface text-ink-2 focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
          <button
            onClick={handleSnoozeConfirm}
            disabled={!snoozeDate}
            className="btn btn-primary text-xs font-semibold px-3 py-1 disabled:opacity-40"
          >
            Set
          </button>
          <button
            onClick={() => { setShowSnooze(false); setSnoozeDate(''); }}
            className="text-xs text-ink-4 hover:text-ink-2"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
