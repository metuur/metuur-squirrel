import { Link, useParams } from 'react-router-dom';
import { marked } from 'marked';
import { useFetch } from '@/hooks/useFetch';
import { api } from '@/api/client';

export default function NotePage() {
  const { id = '' } = useParams();
  const { data: note, error, isLoading } = useFetch(`note:${id}`, () => api.note(id));
  const { data: projects } = useFetch('projects-list', () => api.projects());

  if (isLoading && !note) return <div className="h-64 animate-pulse rounded-2xl bg-slate-100 dark:bg-slate-800" />;
  if (error || !note) {
    return (
      <div className="max-w-3xl">
        <div className="mb-4 text-sm">
          <Link to="/" className="text-slate-500 hover:text-primary flex items-center gap-1">
            <span className="material-icons text-base">arrow_back</span> Back to dashboard
          </Link>
        </div>
        <div className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm p-8 text-center">
          <span className="material-icons text-amber-500 text-5xl">help_outline</span>
          <h1 className="mt-3 text-xl font-bold text-slate-900 dark:text-slate-100">
            We couldn't load that note
          </h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            <code className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{id}</code>{' '}
            wasn't found in the active vault. It may have been moved, renamed, or removed.{' '}
            <Link to="/history" className="text-primary hover:underline">Open Recent activity</Link>{' '}
            or use search (Cmd+K) to find it.
          </p>
        </div>
      </div>
    );
  }

  // Only link "Back to project" when the parent is actually a registered
  // project. Notes that live in 03-Areas, 99-Resources, etc. have a
  // project_slug that points to a folder, not a real project — linking
  // there leads to a blank /projects/<folder-name> page.
  const parentIsProject = !!projects?.some((p) => p.slug === note.project_slug);

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
        {parentIsProject ? (
          <Link to={`/projects/${note.project_slug}`} className="hover:text-primary flex items-center gap-1">
            <span className="material-icons text-base">arrow_back</span>
            Back to project
          </Link>
        ) : (
          <Link to="/" className="hover:text-primary flex items-center gap-1">
            <span className="material-icons text-base">arrow_back</span>
            Back to dashboard
          </Link>
        )}
      </div>

      <article className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 bg-gradient-to-br from-primary/5 via-transparent to-transparent border-b border-border-light dark:border-border-dark flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[10px] font-mono text-slate-400 mb-1">{note.id}</div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 leading-tight">{note.title}</h1>
          </div>
          <Link
            to={`/notes/${id}/edit`}
            className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold border border-border-light dark:border-border-dark rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
          >
            <span className="material-icons text-base">edit</span> Edit
          </Link>
        </div>
        <div className="px-6 py-5">
          {note.body ? (
            <div
              className="prose prose-slate dark:prose-invert max-w-none text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: marked.parse(note.body) as string }}
            />
          ) : (
            <p className="text-slate-500 italic">This note is empty.</p>
          )}
        </div>
      </article>
    </div>
  );
}
