import { Link } from 'react-router-dom';
import { useFetch } from '@/hooks/useFetch';
import { api } from '@/api/client';
import { fromNow } from '@/lib/utils';

export default function HistoryPage() {
  const { data, isLoading } = useFetch('history', () => api.history());
  if (isLoading && !data) return <div className="h-64 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />;
  return (
    <div className="max-w-3xl">
      <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 mb-6">Recent activity</h1>
      {!data || data.length === 0 ? (
        <div className="text-center py-12 bg-surface-light dark:bg-surface-dark border border-dashed border-border-light dark:border-border-dark rounded-2xl">
          <span className="material-icons text-slate-300 text-4xl">history</span>
          <p className="text-slate-500 mt-2">Nothing yet.</p>
        </div>
      ) : (
        <div className="space-y-1">
          {data.map((it, i) => {
            const href = it.kind === 'project' ? `/projects/${it.slug}` : `/notes/${it.note_id}`;
            const icon = it.kind === 'project' ? 'folder' : 'description';
            return (
              <Link
                key={`${it.kind}-${it.slug ?? it.note_id ?? i}`}
                to={href}
                className="flex items-center justify-between gap-3 px-4 py-2.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="material-icons text-base text-slate-400 group-hover:text-primary">{icon}</span>
                  <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate group-hover:text-primary">
                    {it.title}
                  </span>
                </div>
                <span className="text-xs text-slate-400 whitespace-nowrap">{fromNow(it.modified_at)}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
