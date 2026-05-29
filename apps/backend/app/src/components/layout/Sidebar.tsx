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
    <aside className="w-64 bg-surface-light dark:bg-surface-dark border-r border-border-light dark:border-border-dark flex-shrink-0 hidden md:flex flex-col py-6 px-4 transition-colors duration-200">
      <div className="flex items-center justify-between mb-4 px-2">
        <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          Dashboard
        </h3>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowNewTask(true)}
            title="New task"
            aria-label="New task"
            className="w-6 h-6 flex items-center justify-center rounded-md text-slate-400 hover:text-primary hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
          >
            <span className="material-icons text-base">add_task</span>
          </button>
          <button
            onClick={() => setShowNewProject(true)}
            title="New project"
            aria-label="New project"
            className="w-6 h-6 flex items-center justify-center rounded-md text-slate-400 hover:text-primary hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
          >
            <span className="material-icons text-base">add</span>
          </button>
        </div>
      </div>
      <nav className="space-y-1">
        <Link
          to="/"
          className="flex items-center justify-between px-2 py-2 text-sm font-medium text-primary bg-blue-50 dark:bg-blue-900/20 rounded-md group"
        >
          <span>My projects</span>
          <span className="bg-white dark:bg-slate-700 px-2 py-0.5 rounded text-xs font-bold shadow-sm">{total}</span>
        </Link>
        <Link
          to="/deadlines"
          className="flex items-center justify-between px-2 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors"
        >
          <span>Pressing</span>
          <span className={`font-bold ${pressing > 0 ? 'text-orange-500' : 'text-slate-400'}`}>{pressing}</span>
        </Link>
        <Link
          to="/history"
          className="flex items-center justify-between px-2 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md transition-colors"
        >
          <span>Recent activity</span>
          <span className="text-slate-400">{(history ?? []).length}</span>
        </Link>
      </nav>

      <div className="mt-8">
        <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2 px-2">
          Recents
        </h3>
        <div className="space-y-1">
          {recent.length === 0 && (
            <div className="text-xs text-slate-400 px-2">Nothing yet.</div>
          )}
          {recent.map((it) => (
            <button
              key={(it.note_id ?? it.slug ?? '') + it.modified_at}
              onClick={() =>
                navigate(
                  it.kind === 'project' ? `/projects/${it.slug}` : `/notes/${it.note_id}`,
                )
              }
              className="w-full text-left px-2 py-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors group"
            >
              <div className="text-xs font-medium truncate text-slate-700 dark:text-slate-300 group-hover:text-primary">
                {it.title}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5 truncate">
                {it.kind === 'project' ? 'Project' : 'Note'} • {fromNow(it.modified_at)}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-auto pt-6 border-t border-border-light dark:border-border-dark space-y-1">
        <button
          onClick={() => navigate('/settings')}
          className="w-full flex items-center gap-3 px-2 py-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center">
            <span className="material-icons text-slate-500 text-base">settings</span>
          </div>
          <div className="text-sm font-medium text-slate-700 dark:text-slate-300">Settings</div>
        </button>
        <div className="px-2 pt-2 text-[10px] text-slate-400 dark:text-slate-500">
          v{me?.version ?? '?'}
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
