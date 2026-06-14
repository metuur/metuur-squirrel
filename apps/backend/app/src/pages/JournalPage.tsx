import { useState } from 'react';
import { useFetch } from '@/hooks/useFetch';
import { useToast } from '@/components/Toast';
import { api, type JournalEntry, type Mood } from '@/api/client';

const MOODS: { value: Mood; emoji: string; label: string }[] = [
  { value: 'happy', emoji: '😊', label: 'Happy' },
  { value: 'neutral', emoji: '😐', label: 'Neutral' },
  { value: 'sad', emoji: '😔', label: 'Sad' },
];
const MOOD_EMOJI: Record<Mood, string> = { happy: '😊', neutral: '😐', sad: '😔' };

// Matches the form-control styling used across the app (see CaptureModal).
const INPUT_CLS =
  'px-3 py-2 border border-hairline rounded-lg bg-surface text-sm text-ink placeholder-ink-4 focus:border-accent focus:ring-0 outline-none';

function formatNextDue(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString('en-US', {
    weekday: 'short', hour: 'numeric', minute: '2-digit',
  });
}

export default function JournalPage() {
  const toast = useToast();
  const { data, isLoading, mutate } = useFetch('journal', () => api.journal());

  const [mind, setMind] = useState('');
  const [doing, setDoing] = useState('');
  const [mood, setMood] = useState<Mood>('neutral');
  const [saving, setSaving] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  if (isLoading && !data) {
    return <div className="h-64 animate-pulse rounded-lg bg-surface-2" />;
  }

  const createJournal = async () => {
    if (creating) return;
    setCreating(true);
    try {
      await api.journalCreate();
      toast.show('Mind Journal created.', 'success');
      mutate();
    } catch (err) {
      toast.show((err as Error).message || 'Could not create the journal.', 'error');
    } finally {
      setCreating(false);
    }
  };

  if (data && !data.exists) {
    return (
      <div className="max-w-2xl">
        <h1 className="title mb-6">Mind Journal</h1>
        <div className="text-center py-12 panel border-dashed">
          <span className="material-icons text-ink-4 text-4xl">psychology</span>
          <p className="text-ink-3 mt-2">
            No Mind Journal here. It was removed — and that's fine.
          </p>
          <button
            type="button"
            onClick={createJournal}
            disabled={creating}
            className="btn btn-primary mt-5 inline-flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="material-icons text-base">add</span>
            {creating ? 'Adding…' : 'Add Journal'}
          </button>
        </div>
      </div>
    );
  }

  const entries: JournalEntry[] = data?.entries ?? [];
  const due = !!data?.due;
  // Require at least 3 characters in either prompt so empty check-ins can't be logged.
  const canSave = mind.trim().length >= 3 || doing.trim().length >= 3;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (saving || !canSave) return;
    setSaving(true);
    try {
      await api.journalEntry({ mind: mind.trim(), doing: doing.trim(), mood });
      setMind('');
      setDoing('');
      setMood('neutral');
      setShowForm(false);
      toast.show('Journal entry saved.', 'success');
      mutate(); // R-5.2 — refresh entries + due state
    } catch (err) {
      toast.show((err as Error).message || 'Could not save entry.', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="title">Mind Journal</h1>
        <div className="flex items-center gap-3">
          {/* R-5.4 — due flag / next check-in time */}
          {due ? (
            <span className="chip chip-warning whitespace-nowrap">Check-in due</span>
          ) : (
            data?.next_due && (
              <span className="text-xs text-ink-3 whitespace-nowrap">
                Next check-in {formatNextDue(data.next_due)}
              </span>
            )
          )}
          <button
            type="button"
            className="icon-btn"
            aria-label="Journal settings"
            title="Journal settings"
            onClick={() => setShowConfig((v) => !v)}
          >
            <span className="material-icons text-base">tune</span>
          </button>
        </div>
      </div>

      {showConfig && data?.exists && (
        <ConfigPanel
          intervalHours={data.interval_hours ?? 4}
          wakingStart={data.waking?.start ?? '08:00'}
          wakingEnd={data.waking?.end ?? '22:00'}
          onSaved={() => {
            setShowConfig(false);
            mutate();
          }}
        />
      )}

      {/* R-5.1 — check-in form, collapsed behind an "Add entry" button */}
      {!showForm ? (
        <button
          type="button"
          onClick={() => setShowForm(true)}
          className={`btn inline-flex items-center gap-1 ${due ? 'btn-primary' : ''}`}
        >
          <span className="material-icons text-base">add</span>
          Add entry
        </button>
      ) : (
      <form onSubmit={submit} className="panel p-4 space-y-4">
        <div>
          <label className="eyebrow text-ink-2 block mb-1.5">
            What is your mind thinking right now?
          </label>
          <textarea
            value={mind}
            onChange={(e) => setMind(e.target.value)}
            rows={2}
            className={`${INPUT_CLS} w-full resize-none`}
            placeholder="Let it out…"
          />
        </div>
        <div>
          <label className="eyebrow text-ink-2 block mb-1.5">
            What are you doing right now?
          </label>
          <textarea
            value={doing}
            onChange={(e) => setDoing(e.target.value)}
            rows={2}
            className={`${INPUT_CLS} w-full resize-none`}
            placeholder="The activity…"
          />
        </div>
        <div>
          <span className="eyebrow text-ink-2 block mb-1.5">How do you feel?</span>
          <div className="flex gap-2">
            {MOODS.map((m) => (
              <button
                key={m.value}
                type="button"
                onClick={() => setMood(m.value)}
                aria-pressed={mood === m.value}
                className={`flex-1 panel p-3 text-center transition-all ${
                  mood === m.value ? 'ring-2 ring-accent' : 'hover:shadow-md'
                }`}
              >
                <div className="text-2xl leading-none">{m.emoji}</div>
                <div className="text-xs text-ink-3 mt-1">{m.label}</div>
              </button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="submit"
            className="btn btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={saving || !canSave}
          >
            {saving ? 'Saving…' : 'Log this moment'}
          </button>
          <button
            type="button"
            onClick={() => setShowForm(false)}
            disabled={saving}
            className="btn btn-ghost disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </form>
      )}

      {/* R-5.3 — chronological entries with mood indicator */}
      <section>
        <h2 className="eyebrow text-ink-2 mb-3">Entries ({entries.length})</h2>
        {entries.length === 0 ? (
          <p className="text-ink-4 text-sm">No entries yet. Your first check-in starts the log.</p>
        ) : (
          <div className="space-y-2">
            {entries.map((entry, i) => (
              <div key={`${entry.timestamp}-${i}`} className="panel p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg leading-none">{MOOD_EMOJI[entry.mood] ?? '·'}</span>
                  <span className="text-xs font-mono text-ink-4">{entry.timestamp}</span>
                </div>
                {entry.mind && <p className="text-sm text-ink"><strong className="text-ink-3">Mind:</strong> {entry.mind}</p>}
                {entry.doing && <p className="text-sm text-ink mt-0.5"><strong className="text-ink-3">Doing:</strong> {entry.doing}</p>}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// R-5.5 — interval + waking-window controls wired to PATCH /api/journal/config.
function ConfigPanel({
  intervalHours,
  wakingStart,
  wakingEnd,
  onSaved,
}: {
  intervalHours: number;
  wakingStart: string;
  wakingEnd: string;
  onSaved: () => void;
}) {
  const toast = useToast();
  const [interval, setIntervalH] = useState(String(intervalHours));
  const [start, setStart] = useState(wakingStart);
  const [end, setEnd] = useState(wakingEnd);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (saving) return;
    setSaving(true);
    try {
      await api.journalConfig({
        interval_hours: Number(interval),
        waking_start: start,
        waking_end: end,
      });
      toast.show('Settings updated.', 'success');
      onSaved();
    } catch (err) {
      toast.show((err as Error).message || 'Could not update settings.', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="panel p-4 space-y-3 bg-surface-2">
      <div className="flex items-center gap-3">
        <label className="text-sm text-ink-2 flex-1">
          Remind me every
          <input
            type="number"
            min={1}
            value={interval}
            onChange={(e) => setIntervalH(e.target.value)}
            className={`${INPUT_CLS} ml-2 w-16`}
          />
          <span className="ml-1.5 text-ink-3">hours</span>
        </label>
      </div>
      <div className="flex items-center gap-3">
        <label className="text-sm text-ink-2">
          Waking hours
          <input
            type="time"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className={`${INPUT_CLS} ml-2`}
          />
        </label>
        <span className="text-ink-4">to</span>
        <label className="text-sm text-ink-2">
          <input
            type="time"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className={INPUT_CLS}
          />
        </label>
      </div>
      <button type="button" className="btn btn-primary" onClick={save} disabled={saving}>
        {saving ? 'Saving…' : 'Save settings'}
      </button>
    </div>
  );
}
