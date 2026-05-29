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

  if (isLoading && !project) return <div className="h-64 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />;
  if (error || !project) {
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
            We couldn't find that project
          </h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
            <code className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{slug}</code>{' '}
            isn't a registered project. Notes outside <code className="font-mono text-xs">01-Proyectos-Activos/</code>{' '}
            don't have a project page. Open one of your real projects from{' '}
            <Link to="/" className="text-primary hover:underline">My projects</Link> instead.
          </p>
        </div>
      </div>
    );
  }

  const briefCommand = slashCommands.brief(slug, stakeholder);

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <Link to="/" className="hover:text-primary flex items-center gap-1">
          <span className="material-icons text-base">arrow_back</span> Back
        </Link>
      </div>

      <header className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm overflow-hidden">
        <div className="px-6 py-5 bg-gradient-to-br from-primary/5 via-transparent to-transparent border-b border-border-light dark:border-border-dark">
          <div className="text-[10px] font-mono text-slate-400 mb-1">{project.slug}</div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100 leading-tight">{project.title}</h1>
        </div>
        <div className="px-6 py-3 flex flex-wrap items-center gap-2">
          <Link
            to={`/projects/${slug}/edit`}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold border border-border-light dark:border-border-dark rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            <span className="material-icons text-base">edit</span> Edit
          </Link>
          <button
            onClick={() => openCapture(slug)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold border border-border-light dark:border-border-dark rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            <span className="material-icons text-base">add</span> Note
          </button>
          <button
            onClick={() => setShowNewTask(true)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold border border-border-light dark:border-border-dark rounded-lg text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800"
          >
            <span className="material-icons text-base">add_task</span> New Task
          </button>
          <button
            onClick={() => setBriefPanelOpen(true)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-semibold border-2 border-primary text-primary rounded-lg hover:bg-primary hover:text-white transition-all"
          >
            <span className="material-icons text-base">terminal</span>
            Get brief command
          </button>
        </div>
        <div className="px-6 py-5 border-t border-border-light dark:border-border-dark">
          {project.body ? (
            <div
              className="prose prose-slate dark:prose-invert max-w-none text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: marked.parse(project.body) as string }}
            />
          ) : (
            <p className="text-slate-500 italic">No description yet.</p>
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
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-1">
              Recipient (optional — adds <code className="font-mono text-[10px]">--email &lt;to&gt;</code>)
            </label>
            <input
              type="email"
              value={stakeholder}
              onChange={(e) => setStakeholder(e.target.value)}
              placeholder="sarah@acme.com"
              className="w-full px-3 py-2 border border-border-light dark:border-border-dark rounded-lg bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:border-primary focus:ring-0 outline-none"
            />
          </div>
        }
        onClose={() => setBriefPanelOpen(false)}
      />

      <section>
        <h2 className="text-xs font-bold tracking-wider text-slate-500 dark:text-slate-400 uppercase mb-3 px-1">
          Recent notes
        </h2>
        {project.notes.length === 0 ? (
          <div className="text-center py-10 bg-surface-light dark:bg-surface-dark border border-dashed border-border-light dark:border-border-dark rounded-2xl">
            <span className="material-icons text-slate-300 text-3xl">note_add</span>
            <p className="text-slate-500 text-sm mt-2">No notes yet.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {project.notes.map((n) => (
              <Link
                key={n.id}
                to={`/notes/${n.id}`}
                className="flex items-center justify-between gap-3 px-4 py-3 bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-xl hover:border-primary/30 hover:shadow-sm transition-all group"
              >
                <div className="min-w-0">
                  <div className="text-[10px] font-mono text-slate-400 mb-0.5">{n.id}</div>
                  <div className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate group-hover:text-primary">{n.title}</div>
                </div>
                <div className="text-xs text-slate-400 whitespace-nowrap">{fromNow(n.modified_at)}</div>
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
