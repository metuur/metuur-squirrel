import { Link, useParams } from 'react-router-dom';
import { useFetch } from '@/hooks/useFetch';
import { api } from '@/api/client';
import { Markdown } from '@/components/Markdown';

// Read the flat `key: value` frontmatter into ordered pairs for display.
function readFrontmatter(raw: string): { key: string; value: string }[] {
  const m = raw.match(/^---\n([\s\S]*?)\n---/);
  if (!m) return [];
  const props: { key: string; value: string }[] = [];
  for (const line of m[1].split('\n')) {
    if (!line.trim() || line.startsWith(' ') || line.trimStart().startsWith('#')) continue;
    const i = line.indexOf(':');
    if (i < 0) continue;
    // Strip a YAML inline comment (whitespace + `#…`); `#` without a leading
    // space stays (e.g. a hex colour).
    const value = line.slice(i + 1).replace(/\s+#.*$/, '').trim();
    props.push({ key: line.slice(0, i).trim(), value });
  }
  return props;
}

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
  const props = readFrontmatter(note.raw_body);
  const tagList = (() => {
    const t = props.find((p) => p.key.trim().toLowerCase() === 'tags');
    if (!t) return [];
    return t.value.trim().replace(/^\[|\]$/g, '').split(',').map((s) => s.trim()).filter(Boolean);
  })();

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
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <h1 className="text-sm font-semibold text-ink-2 leading-snug">{note.title}</h1>
              {tagList.map((t) => (
                <span key={t} className="inline-flex items-center rounded bg-surface-2 px-1.5 py-0.5 text-[11px] text-ink-3">{t}</span>
              ))}
            </div>
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
        {props.length > 0 && (
          <div className="px-6 py-4 border-b border-hairline-2">
            <div className="text-xs font-semibold text-ink-2 mb-2">Properties</div>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1.5 text-sm">
              {props.map((p) => {
                const isList = p.key.trim().toLowerCase() === 'tags' || /^\[[\s\S]*\]$/.test(p.value.trim());
                const tags = isList
                  ? p.value.trim().replace(/^\[|\]$/g, '').split(',').map((s) => s.trim()).filter(Boolean)
                  : [];
                return (
                <div key={p.key} className={`flex gap-3 ${isList ? 'sm:col-span-2' : ''}`}>
                  <dt className="font-mono text-xs text-ink-4 w-28 shrink-0 self-center">{p.key}</dt>
                  <dd className="text-ink-2 break-words flex-1 min-w-0">
                    {isList ? (
                      tags.length ? (
                        <span className="flex flex-wrap gap-1">
                          {tags.map((t) => (
                            <span key={t} className="inline-flex items-center rounded bg-surface-2 px-1.5 py-0.5 text-xs text-ink-2">{t}</span>
                          ))}
                        </span>
                      ) : <span className="text-ink-4 italic">empty</span>
                    ) : (
                      p.value || <span className="text-ink-4 italic">empty</span>
                    )}
                  </dd>
                </div>
                );
              })}
            </dl>
          </div>
        )}
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
