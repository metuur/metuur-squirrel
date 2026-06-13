import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMe } from '@/hooks/useMe';
import { useFetch } from '@/hooks/useFetch';
import { api } from '@/api/client';
import { fromNow } from '@/lib/utils';
import { NewProjectModal } from '@/components/NewProjectModal';
import { ProjectSelectorModal } from '@/components/ProjectSelectorModal';

export function Sidebar() {
  const navigate = useNavigate();
  const { data: me } = useMe();
  const { data: home, mutate: refreshHome } = useFetch('sidebar-home', () => api.home());
  const { data: history } = useFetch('sidebar-history', () => api.history());
  const [showNewProject, setShowNewProject] = useState(false);
  const [showNewTask, setShowNewTask] = useState(false);

  const total = home?.projects.length ?? 0;
  const pressing = home?.pressing.length ?? 0;
  const recent = (history ?? []).slice(0, 3);

  return (
    <aside className="w-64 h-full bg-paper-2 border-r border-hairline flex-shrink-0 hidden md:flex flex-col py-6 px-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4 px-2">
        <h3 className="eyebrow">Dashboard</h3>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowNewTask(true)}
            title="New task"
            aria-label="New task"
            className="w-6 h-6 flex items-center justify-center rounded-md text-ink-4 hover:text-accent hover:bg-focus-tint transition-colors"
          >
            <span className="material-icons text-base">add_task</span>
          </button>
          <button
            onClick={() => setShowNewProject(true)}
            title="New project"
            aria-label="New project"
            className="w-6 h-6 flex items-center justify-center rounded-md text-ink-4 hover:text-accent hover:bg-focus-tint transition-colors"
          >
            <span className="material-icons text-base">add</span>
          </button>
        </div>
      </div>
      <nav className="space-y-1">
        <Link
          to="/"
          className="flex items-center justify-between px-2 py-2 text-sm font-medium text-accent bg-focus-tint rounded-md group"
        >
          <span>My projects</span>
          <span className="chip chip-count">{total}</span>
        </Link>
        <Link
          to="/deadlines"
          className="flex items-center justify-between px-2 py-2 text-sm font-medium text-ink-2 hover:bg-surface-2 rounded-md transition-colors"
        >
          <span>Pressing</span>
          <span className={`font-bold ${pressing > 0 ? 'text-warning' : 'text-ink-4'}`}>{pressing}</span>
        </Link>
        <Link
          to="/post-its"
          className="flex items-center justify-between px-2 py-2 text-sm font-medium text-ink-2 hover:bg-surface-2 rounded-md transition-colors"
        >
          <span>Post-its</span>
          <span className="material-icons text-base text-ink-4">sticky_note_2</span>
        </Link>
        <Link
          to="/history"
          className="flex items-center justify-between px-2 py-2 text-sm font-medium text-ink-2 hover:bg-surface-2 rounded-md transition-colors"
        >
          <span>Recent activity</span>
          <span className="text-ink-4">{(history ?? []).length}</span>
        </Link>
      </nav>

      <div className="mt-8">
        <h3 className="eyebrow mb-2 px-2">Recents</h3>
        <div className="space-y-1">
          {recent.length === 0 && (
            <div className="text-xs text-ink-3 px-2">Nothing yet.</div>
          )}
          {recent.map((it) => (
            <button
              key={(it.note_id ?? it.slug ?? '') + it.modified_at}
              onClick={() =>
                navigate(
                  it.kind === 'project' ? `/projects/${it.slug}` : `/notes/${it.note_id}`,
                )
              }
              className="w-full text-left px-2 py-2 rounded-md hover:bg-surface-2 transition-colors group"
            >
              <div className="text-xs font-medium truncate text-ink-2 group-hover:text-accent">
                {it.title}
              </div>
              <div className="text-[10px] text-ink-3 mt-0.5 truncate">
                {it.kind === 'project' ? 'Project' : 'Note'} • {fromNow(it.modified_at)}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-auto pt-6 border-t border-hairline space-y-1">
        <button
          onClick={() => navigate('/guide')}
          className="w-full flex items-center gap-3 px-2 py-2 rounded-md hover:bg-surface-2 transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-surface-2 flex items-center justify-center">
            <span className="material-icons text-ink-3 text-base">menu_book</span>
          </div>
          <div className="text-sm font-medium text-ink-2">Guide</div>
        </button>
        <button
          onClick={() => navigate('/settings')}
          className="w-full flex items-center gap-3 px-2 py-2 rounded-md hover:bg-surface-2 transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-surface-2 flex items-center justify-center">
            <span className="material-icons text-ink-3 text-base">settings</span>
          </div>
          <div className="text-sm font-medium text-ink-2">Settings</div>
        </button>
        <div className="px-2 pt-2 text-[10px] leading-relaxed text-ink-3">
          <div>
            © 2026 Squirrel <span className="tabular">v{me?.version ?? '?'}</span>. Made with ❤️ by @javierhbr.
          </div>
          <a
            href="https://buymeacoffee.com/javierhbr"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 mt-1 text-accent hover:underline"
          >
            ☕ Buy me a coffee
          </a>
        </div>
      </div>

      <NewProjectModal
        open={showNewProject}
        onClose={() => setShowNewProject(false)}
        onCreated={() => refreshHome()}
      />
      <ProjectSelectorModal
        open={showNewTask}
        onClose={() => setShowNewTask(false)}
      />
    </aside>
  );
}
