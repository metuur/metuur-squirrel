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
  'Today / Tomorrow': 'text-red-500',
  'Today / Overdue': 'text-red-600',
  'This week': 'text-orange-500',
  'Later': 'text-slate-400',
};

export default function DeadlinesPage() {
  const { data, isLoading } = useFetch('deadlines', () => api.deadlines());
  if (isLoading && !data) return <div className="h-64 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />;
  const hasItems = !!data && data.some((g) => g.items.length > 0);
  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-6">Deadlines</h1>
      {!hasItems ? (
        <div className="text-center py-12 bg-surface-light dark:bg-surface-dark border border-dashed border-border-light dark:border-border-dark rounded-2xl">
          <span className="material-icons text-slate-300 text-4xl">event_available</span>
          <p className="text-slate-500 mt-2">Nothing due. ✨</p>
        </div>
      ) : (
        <div className="space-y-6">
          {data!.filter(g => g.items.length).map((g) => (
            <section key={g.label}>
              <div className="flex items-center gap-2 mb-3">
                <span className={`material-icons text-base ${LABEL_COLORS[g.label] ?? 'text-slate-400'}`}>
                  {LABEL_ICONS[g.label] ?? 'event'}
                </span>
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">{g.label}</h2>
                <span className="text-[10px] font-bold text-slate-400">({g.items.length})</span>
              </div>
              <div className="space-y-2">
                {g.items.map((it) => (
                  <Link
                    key={it.id}
                    to={`/notes/${it.id}`}
                    className="block bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-xl hover:shadow-md hover:border-primary/30 transition-all p-4 group"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="text-[10px] font-mono text-slate-400 mb-0.5">{it.id}</div>
                        <h3 className="font-medium text-slate-900 dark:text-slate-100 truncate group-hover:text-primary">{it.title}</h3>
                        {it.deadline && (
                          <div className="text-xs text-slate-500 mt-1">{it.deadline}</div>
                        )}
                      </div>
                      {it.is_overdue ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 whitespace-nowrap">
                          {it.days_overdue ?? 0}d overdue
                        </span>
                      ) : it.hours_left != null && it.hours_left < 24 ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300 whitespace-nowrap">
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
