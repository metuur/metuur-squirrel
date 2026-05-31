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
          className="btn btn-ghost px-4 py-1.5 text-sm font-semibold"
        >
          Cancel
        </button>
      }
    >
      <div className="space-y-1 max-h-72 overflow-y-auto">
        {isLoading && (
          <div className="py-6 text-center text-sm text-ink-4">Loading projects…</div>
        )}
        {!isLoading && (!projects || projects.length === 0) && (
          <div className="py-6 text-center text-sm text-ink-4">No active projects found.</div>
        )}
        {(projects ?? []).map((p: ProjectListItem) => (
          <button
            key={p.slug}
            onClick={() => select(p.slug)}
            className="w-full text-left px-3 py-2.5 rounded-lg border border-transparent hover:border-accent/30 hover:bg-focus-tint transition-all group"
          >
            <div className="text-[10px] font-mono text-ink-4 mb-0.5">{p.slug}</div>
            <div className="text-sm font-medium text-ink group-hover:text-accent">{p.title}</div>
          </button>
        ))}
      </div>
    </Modal>
  );
}
