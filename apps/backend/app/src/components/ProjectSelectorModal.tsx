import { useNavigate } from 'react-router-dom';
import { Modal } from '@/components/Modal';
import { useFetch } from '@/hooks/useFetch';
import { api, type ProjectListItem } from '@/api/client';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ProjectSelectorModal({ open, onClose }: Props) {
  const navigate = useNavigate();
  const { data: projects, isLoading } = useFetch('project-selector-list', () => api.projects());

  function select(slug: string) {
    onClose();
    navigate(`/projects/${slug}?newTask=true`);
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New task — select project"
      subtitle="Choose a project to create a task in."
      icon="add_task"
      size="md"
      footer={
        <button
          onClick={onClose}
          className="px-4 py-1.5 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-md transition-colors"
        >
          Cancel
        </button>
      }
    >
      <div className="space-y-1 max-h-72 overflow-y-auto">
        {isLoading && (
          <div className="py-6 text-center text-sm text-slate-400">Loading projects…</div>
        )}
        {!isLoading && (!projects || projects.length === 0) && (
          <div className="py-6 text-center text-sm text-slate-400">No active projects found.</div>
        )}
        {(projects ?? []).map((p: ProjectListItem) => (
          <button
            key={p.slug}
            onClick={() => select(p.slug)}
            className="w-full text-left px-3 py-2.5 rounded-lg border border-transparent hover:border-primary/30 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-all group"
          >
            <div className="text-[10px] font-mono text-slate-400 mb-0.5">{p.slug}</div>
            <div className="text-sm font-medium text-slate-800 dark:text-slate-100 group-hover:text-primary">{p.title}</div>
          </button>
        ))}
      </div>
    </Modal>
  );
}
