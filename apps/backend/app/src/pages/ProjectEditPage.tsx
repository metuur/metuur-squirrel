import { Link, useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { useFetch } from '@/hooks/useFetch';
import { ConflictDialog } from '@/components/ConflictDialog';
import { useToast } from '@/components/Toast';
import { MarkdownEditor } from '@/components/MarkdownEditor';

function splitFrontmatter(raw: string): { front: string; content: string } {
  const m = raw.match(/^(---\n[\s\S]*?\n---\n?)([\s\S]*)$/);
  return m ? { front: m[1], content: m[2] } : { front: '', content: raw };
}

export default function ProjectEditPage() {
  const { slug = '' } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { data: project } = useFetch(`project-edit:${slug}`, () => api.project(slug));
  const [front, setFront] = useState('');
  const [body, setBody] = useState('');
  const [mtime, setMtime] = useState(0);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState<{ current_body: string; current_mtime: number } | null>(null);

  useEffect(() => {
    if (project) {
      const { front: f, content: c } = splitFrontmatter(project.raw_body);
      setFront(f);
      setBody(c);
      setMtime(project.mtime);
    }
  }, [project]);

  async function save() {
    setSaving(true);
    try {
      const r = await api.projectSave(slug, front + body, mtime);
      if (r.mtime) setMtime(r.mtime);
      toast.show('Saved.', 'success');
      nav(`/projects/${slug}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setConflict(e.payload);
      else toast.show(e instanceof Error ? e.message : 'Could not save.', 'error');
    } finally { setSaving(false); }
  }

  if (!project) return <div className="h-64 animate-pulse rounded-lg bg-surface-2" />;

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex items-center gap-3 text-sm text-ink-3">
        <Link to={`/projects/${slug}`} className="hover:text-accent flex items-center gap-1">
          <span className="material-icons text-base">close</span> Cancel
        </Link>
      </div>
      <div className="panel">
        <div className="px-6 py-4 border-b border-hairline-2">
          <div className="text-[10px] font-mono text-ink-4 mb-1">{project.slug}</div>
          <h1 className="title">Edit {project.title}</h1>
        </div>
        <div className="px-6 py-5">
          <MarkdownEditor
            key={slug}
            value={body}
            onChange={setBody}
            disabled={saving}
            minHeight="32rem"
            showSourceToggle
          />
        </div>
        <div className="px-6 py-4 border-t border-hairline-2 flex items-center justify-end gap-2">
          <Link
            to={`/projects/${slug}`}
            className="btn btn-ghost px-4 py-1.5 text-sm font-semibold"
          >
            Cancel
          </Link>
          <button
            onClick={save}
            disabled={saving}
            className="btn btn-primary text-sm font-semibold px-4 py-1.5 flex items-center gap-1"
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
          if (conflict) {
            const { front: f, content: c } = splitFrontmatter(conflict.current_body);
            setFront(f); setBody(c); setMtime(conflict.current_mtime);
          }
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
