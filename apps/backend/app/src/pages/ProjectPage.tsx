import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { marked } from 'marked';
import { useFetch } from '@/hooks/useFetch';
import { api, slashCommands } from '@/api/client';
import { fromNow } from '@/lib/utils';
import { useCapture } from '@/components/CaptureModal';
import { PromptPanel } from '@/components/PromptPanel';
import { NewTaskModal } from '@/components/NewTaskModal';

export default function ProjectPage() {
  const { slug = '' } = useParams();
  const { data: project, error, isLoading, mutate: refreshProject } = useFetch(`project:${slug}`, () => api.project(slug));
  const { open: openCapture } = useCapture();
  const [briefPanelOpen, setBriefPanelOpen] = useState(false);
  const [stakeholder, setStakeholder] = useState('');
  const [searchParams] = useSearchParams();
  const [showNewTask, setShowNewTask] = useState(() => searchParams.get('newTask') === 'true');

  const suggestedTags = useMemo(() => {
    const tags = new Set<string>([slug]);
    for (const note of project?.notes ?? []) {
      tags.add(note.id.replace(/-\d+$/, ''));
    }
    return [...tags];
  }, [project?.notes, slug]);

  if (isLoading && !project) return <div className="h-64 animate-pulse rounded-lg bg-surface-2" />;
  if (error || !project) {
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
            We couldn't find that project
          </h1>
          <p className="mt-2 text-sm text-ink-3 max-w-md mx-auto">
            <code className="font-mono text-xs bg-surface-2 px-1.5 py-0.5 rounded">{slug}</code>{' '}
            isn't a registered project. Notes outside <code className="font-mono text-xs">01-Proyectos-Activos/</code>{' '}
            don't have a project page. Open one of your real projects from{' '}
            <Link to="/" className="text-accent hover:underline">My projects</Link> instead.
          </p>
        </div>
      </div>
    );
  }

  const briefCommand = slashCommands.brief(slug, stakeholder);

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center gap-2 text-sm text-ink-3">
        <Link to="/" className="hover:text-accent flex items-center gap-1">
          <span className="material-icons text-base">arrow_back</span> Back
        </Link>
      </div>

      <header className="panel overflow-hidden">
        <div className="px-6 py-5 border-b border-hairline-2 bg-focus-tint/40">
          <div className="text-[10px] font-mono text-ink-4 mb-1">{project.slug}</div>
          <h1 className="text-2xl font-bold text-ink leading-tight">{project.title}</h1>
        </div>
        <div className="px-6 py-3 flex flex-wrap items-center gap-2">
          <Link
            to={`/projects/${slug}/edit`}
            className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
          >
            <span className="material-icons text-base">edit</span> Edit
          </Link>
          <button
            onClick={() => { api.reveal(slug).catch(() => {}); }}
            title="Reveal in Finder"
            aria-label="Reveal in Finder"
            className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
          >
            <span className="material-icons text-base">folder_open</span> Reveal
          </button>
          <button
            onClick={() => openCapture(slug)}
            className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
          >
            <span className="material-icons text-base">add</span> Note
          </button>
          <button
            onClick={() => setShowNewTask(true)}
            className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold"
          >
            <span className="material-icons text-base">add_task</span> New Task
          </button>
          <button
            onClick={() => setBriefPanelOpen(true)}
            className="btn inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold border-2 border-accent text-accent hover:bg-accent hover:text-surface"
          >
            <span className="material-icons text-base">terminal</span>
            Get brief command
          </button>
        </div>
        <div className="px-6 py-5 border-t border-hairline-2">
          {project.body ? (
            <div
              className="prose prose-slate max-w-none text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: marked.parse(project.body) as string }}
            />
          ) : (
            <p className="text-ink-3 italic">No description yet.</p>
          )}
        </div>
      </header>

      <PromptPanel
        open={briefPanelOpen}
        title={`Brief: ${project.slug}`}
        command={briefCommand}
        helpText="Run this in Claude Code / Cursor / Codex. The skill loads the project's intents, decisions, deadlines and produces the 6-section brief (NOW / DONE / NEXT / DECISIONS / STEPS / CONTEXT). Add a recipient below to format it as an email."
        preface={
          <div>
            <label className="block eyebrow mb-1">
              Recipient (optional — adds <code className="font-mono text-[10px]">--email &lt;to&gt;</code>)
            </label>
            <input
              type="email"
              value={stakeholder}
              onChange={(e) => setStakeholder(e.target.value)}
              placeholder="sarah@acme.com"
              className="w-full px-3 py-2 border border-hairline rounded-lg bg-surface text-sm text-ink placeholder-ink-4 focus:border-accent focus:ring-0 outline-none"
            />
          </div>
        }
        onClose={() => setBriefPanelOpen(false)}
      />

      <section>
        <h2 className="eyebrow mb-3 px-1">Recent notes</h2>
        {project.notes.length === 0 ? (
          <div className="text-center py-10 panel border-dashed">
            <span className="material-icons text-ink-4 text-3xl">note_add</span>
            <p className="text-ink-3 text-sm mt-2">No notes yet.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {project.notes.map((n) => (
              <Link
                key={n.id}
                to={`/notes/${n.id}`}
                className="flex items-center justify-between gap-3 px-4 py-3 panel hover:shadow-md transition-all group"
              >
                <div className="min-w-0">
                  <div className="text-[10px] font-mono text-ink-4 mb-0.5">{n.id}</div>
                  <div className="text-sm font-medium text-ink truncate group-hover:text-accent">{n.title}</div>
                </div>
                <div className="text-xs text-ink-4 whitespace-nowrap">{fromNow(n.modified_at)}</div>
              </Link>
            ))}
          </div>
        )}
      </section>
      <NewTaskModal
        open={showNewTask}
        projectSlug={slug}
        suggestedTags={suggestedTags}
        onClose={() => setShowNewTask(false)}
        onCreated={() => {
          setShowNewTask(false);
          refreshProject();
        }}
      />
    </div>
  );
}
