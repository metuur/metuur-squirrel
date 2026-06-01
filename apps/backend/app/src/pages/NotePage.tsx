import { Link, useParams } from 'react-router-dom';
import { useFetch } from '@/hooks/useFetch';
import { api } from '@/api/client';
import { Markdown } from '@/components/Markdown';

export default function NotePage() {
  const { id = '' } = useParams();
  const { data: note, error, isLoading } = useFetch(`note:${id}`, () => api.note(id));
  const { data: projects } = useFetch('projects-list', () => api.projects());

  if (isLoading && !note) return <div className="h-64 animate-pulse rounded-2xl bg-surface-2" />;
  if (error || !note) {
    return (
      <div className="max-w-3xl">
        <div className="mb-4 text-sm">
          <Link to="/" className="text-ink-3 hover:text-accent flex items-center gap-1">
            <span className="material-icons text-base">arrow_back</span> Back to dashboard
          </Link>
        </div>
        <div className="panel p-8 text-center">
          <span className="material-icons text-warning text-5xl">help_outline</span>
          <h1 className="mt-3 title">
            We couldn't load that note
          </h1>
          <p className="mt-2 text-sm text-ink-3 max-w-md mx-auto">
            <code className="font-mono text-xs bg-surface-2 px-1.5 py-0.5 rounded">{id}</code>{' '}
            wasn't found in the active vault. It may have been moved, renamed, or removed.{' '}
            <Link to="/history" className="text-accent hover:underline">Open Recent activity</Link>{' '}
            or use search (Cmd+K) to find it.
          </p>
        </div>
      </div>
    );
  }

  const parentIsProject = !!projects?.some((p) => p.slug === note.project_slug);

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center gap-2 text-sm text-ink-3 flex-wrap">
        <Link to="/" className="hover:text-accent flex items-center gap-1">
          <span className="material-icons text-base">arrow_back</span>
          Back to dashboard
        </Link>
        <span className="text-ink-4">|</span>
        {parentIsProject ? (
          <>
            <Link to={`/projects/${note.project_slug}`} className="hover:text-accent">
              {note.project_slug}
            </Link>
            <span className="text-ink-4">/</span>
            <span className="text-ink-2 font-medium">{note.kind === 'project-task' ? 'Task' : 'Note'}</span>
          </>
        ) : (
          <span className="text-ink-2 font-medium">Note</span>
        )}
      </div>

      <article className="panel overflow-hidden">
        <div className="px-6 py-5 border-b border-hairline-2 bg-focus-tint/40 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[10px] font-mono text-ink-4 mb-1">{note.id}</div>
            <h1 className="text-sm font-semibold text-ink-2 leading-snug">{note.title}</h1>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => {
                api.reveal(id).catch((err: unknown) => {
                  console.error('Reveal failed for id=' + id + ':', err);
                  const msg = err instanceof Error ? err.message : 'Unknown error';
                  window.alert('Could not reveal in Finder: ' + msg);
                });
              }}
              title="Reveal in Finder"
              aria-label="Reveal in Finder"
              className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
            >
              <span className="material-icons text-base">folder_open</span> Reveal
            </button>
            <Link
              to={`/notes/${id}/edit`}
              className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
            >
              <span className="material-icons text-base">edit</span> Edit
            </Link>
          </div>
        </div>
        <div className="px-6 py-5">
          {note.body ? (
            <div className="prose prose-slate max-w-none text-sm leading-relaxed prose-h1:text-2xl prose-h1:mt-0 prose-h2:text-lg prose-h3:text-base">
              <Markdown>{note.body}</Markdown>
            </div>
          ) : (
            <p className="text-ink-3 italic">This note is empty.</p>
          )}
        </div>
      </article>
    </div>
  );
}
