import { Link, useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { useFetch } from '@/hooks/useFetch';
import { ConflictDialog } from '@/components/ConflictDialog';
import { useToast } from '@/components/Toast';

export default function ProjectEditPage() {
  const { slug = '' } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { data: project } = useFetch(`project-edit:${slug}`, () => api.project(slug));
  const [body, setBody] = useState('');
  const [mtime, setMtime] = useState(0);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState<{ current_body: string; current_mtime: number } | null>(null);

  useEffect(() => {
    if (project) { setBody(project.raw_body); setMtime(project.mtime); }
  }, [project]);

  async function save() {
    setSaving(true);
    try {
      const r = await api.projectSave(slug, body, mtime);
      if (r.mtime) setMtime(r.mtime);
      toast.show('Saved.', 'success');
      nav(`/projects/${slug}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setConflict(e.payload);
      else toast.show(e instanceof Error ? e.message : 'Could not save.', 'error');
    } finally { setSaving(false); }
  }

  if (!project) return <div className="h-64 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />;

  return (
    <div className="max-w-3xl space-y-4">
      <div className="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400">
        <Link to={`/projects/${slug}`} className="hover:text-primary flex items-center gap-1">
          <span className="material-icons text-base">close</span> Cancel
        </Link>
      </div>
      <div className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm">
        <div className="px-6 py-4 border-b border-border-light dark:border-border-dark">
          <div className="text-[10px] font-mono text-slate-400 mb-1">{project.slug}</div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Edit {project.title}</h1>
        </div>
        <div className="px-6 py-5">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={20}
            className="w-full px-4 py-3 font-mono text-sm border border-border-light dark:border-border-dark rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:border-primary focus:ring-0 outline-none"
          />
        </div>
        <div className="px-6 py-4 border-t border-border-light dark:border-border-dark flex items-center justify-end gap-2">
          <Link
            to={`/projects/${slug}`}
            className="px-4 py-1.5 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md"
          >
            Cancel
          </Link>
          <button
            onClick={save}
            disabled={saving}
            className="bg-primary hover:bg-primary-dark text-white text-sm font-semibold px-4 py-1.5 rounded shadow-sm flex items-center gap-1"
          >
            <span className="material-icons text-lg">save</span>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
      <ConflictDialog
        open={!!conflict}
        payload={conflict}
        onTakeTheirs={() => {
          if (conflict) { setBody(conflict.current_body); setMtime(conflict.current_mtime); }
          setConflict(null);
          toast.show('Loaded their version. Save again to keep it.', 'info');
        }}
        onForceMine={() => {
          if (conflict) setMtime(conflict.current_mtime);
          setConflict(null);
          setTimeout(save, 0);
        }}
        onCancel={() => setConflict(null)}
      />
    </div>
  );
}
