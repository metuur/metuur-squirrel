import { Link } from 'react-router-dom';
import { useFetch } from '@/hooks/useFetch';
import { api } from '@/api/client';

const LABEL_ICONS: Record<string, string> = {
  'Today / Tomorrow': 'alarm',
  'Today / Overdue': 'priority_high',
  'This week': 'event',
  'Later': 'event_note',
};
const LABEL_COLORS: Record<string, string> = {
  'Today / Tomorrow': 'text-critical',
  'Today / Overdue': 'text-critical',
  'This week': 'text-warning',
  'Later': 'text-ink-4',
};
const LABEL_STRIPE: Record<string, string> = {
  'Today / Tomorrow': 'stripe-critical',
  'Today / Overdue': 'stripe-critical',
  'This week': 'stripe-warning',
  'Later': '',
};

export default function DeadlinesPage() {
  const { data, isLoading } = useFetch('deadlines', () => api.deadlines());
  if (isLoading && !data) return <div className="h-64 animate-pulse rounded-lg bg-surface-2" />;
  const hasItems = !!data && data.some((g) => g.items.length > 0);
  return (
    <div className="max-w-3xl">
      <h1 className="title mb-6">Deadlines</h1>
      {!hasItems ? (
        <div className="text-center py-12 panel border-dashed">
          <span className="material-icons text-ink-4 text-4xl">event_available</span>
          <p className="text-ink-3 mt-2">Nothing due. ✨</p>
        </div>
      ) : (
        <div className="space-y-6">
          {data!.filter(g => g.items.length).map((g) => (
            <section key={g.label}>
              <div className="flex items-center gap-2 mb-3">
                <span className={`material-icons text-base ${LABEL_COLORS[g.label] ?? 'text-ink-4'}`}>
                  {LABEL_ICONS[g.label] ?? 'event'}
                </span>
                <h2 className="eyebrow text-ink-2">{g.label}</h2>
                <span className="text-[10px] font-bold text-ink-4">({g.items.length})</span>
              </div>
              <div className="space-y-2">
                {g.items.map((it) => (
                  <Link
                    key={it.id}
                    to={`/notes/${it.id}`}
                    className={`block panel p-4 group hover:shadow-md transition-all ${LABEL_STRIPE[g.label] ? `stripe ${LABEL_STRIPE[g.label]}` : ''}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-[10px] font-mono text-ink-4 mb-0.5">{it.id}</div>
                        <h3 className="font-medium text-ink truncate group-hover:text-accent">{it.title}</h3>
                        {it.deadline && (
                          <div className="text-xs text-ink-3 mt-1">{it.deadline}</div>
                        )}
                      </div>
                      {it.is_overdue ? (
                        <span className="chip chip-critical whitespace-nowrap">
                          {it.days_overdue ?? 0}d overdue
                        </span>
                      ) : it.hours_left != null && it.hours_left < 24 ? (
                        <span className="chip chip-warning whitespace-nowrap">
                          {Math.round(it.hours_left)}h left
                        </span>
                      ) : null}
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
