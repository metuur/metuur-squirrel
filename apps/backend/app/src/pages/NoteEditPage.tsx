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

// Set, replace, or remove the `deadline:` line inside a frontmatter block.
// Empty deadline removes the line; a value updates the existing line or inserts
// one before the closing `---`. If there's no frontmatter, only create one when
// a deadline is actually set (free notes stay frontmatter-free otherwise).
function applyDeadline(front: string, deadline: string): string {
  if (!front) return deadline ? `---\ndeadline: ${deadline}\n---\n` : front;
  const lines = front.split('\n');
  const dlIdx = lines.findIndex((l) => l.trim().startsWith('deadline:'));
  if (!deadline) {
    if (dlIdx >= 0) lines.splice(dlIdx, 1);
    return lines.join('\n');
  }
  if (dlIdx >= 0) {
    lines[dlIdx] = `deadline: ${deadline}`;
  } else {
    const closeIdx = lines.findIndex((l, i) => i > 0 && l.trim() === '---');
    if (closeIdx >= 0) lines.splice(closeIdx, 0, `deadline: ${deadline}`);
  }
  return lines.join('\n');
}

export default function NoteEditPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { data: note } = useFetch(`note-edit:${id}`, () => api.note(id));
  const [front, setFront] = useState('');
  const [body, setBody] = useState('');
  const [deadline, setDeadline] = useState('');
  const [hasFrontmatter, setHasFrontmatter] = useState(false);
  const [mtime, setMtime] = useState(0);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState<{ current_body: string; current_mtime: number } | null>(null);

  useEffect(() => {
    if (note) {
      const { front: f, content: c } = splitFrontmatter(note.raw_body);
      setFront(f);
      setBody(c);
      setDeadline(note.deadline ?? '');
      setHasFrontmatter(f !== '');
      setMtime(note.mtime);
    }
  }, [note]);

  async function save() {
    setSaving(true);
    try {
      const r = await api.noteSave(id, applyDeadline(front, deadline) + body, mtime);
      if (r.mtime) setMtime(r.mtime);
      toast.show('Saved.', 'success');
      nav(`/notes/${id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setConflict(e.payload);
      else toast.show(e instanceof Error ? e.message : 'Could not save.', 'error');
    } finally { setSaving(false); }
  }

  if (!note) return <div className="h-64 animate-pulse rounded-lg bg-surface-2" />;

  return (
    <div className="max-w-4xl space-y-4">
      <div className="flex items-center gap-3 text-sm text-ink-3">
        <Link to={`/notes/${id}`} className="hover:text-accent flex items-center gap-1">
          <span className="material-icons text-base">close</span> Cancel
        </Link>
      </div>
      <div className="panel">
        <div className="px-6 py-4 border-b border-hairline-2">
          <div className="text-[10px] font-mono text-ink-4 mb-1">{note.id}</div>
          <h1 className="title">Edit note</h1>
        </div>
        <div className="px-6 py-5 space-y-4">
          {hasFrontmatter && (
            <label className="block">
              <div className="text-xs font-semibold text-ink-2 mb-1">Deadline (optional)</div>
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
                disabled={saving}
                className="text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none"
              />
            </label>
          )}
          <MarkdownEditor
            key={id}
            value={body}
            onChange={setBody}
            disabled={saving}
            minHeight="32rem"
            showSourceToggle
          />
        </div>
        <div className="px-6 py-4 border-t border-hairline-2 flex items-center justify-end gap-2">
          <Link
            to={`/notes/${id}`}
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
            const dl = f.match(/^deadline:\s*(.+)$/m);
            setFront(f); setBody(c);
            setDeadline(dl ? dl[1].split('#')[0].trim() : '');
            setHasFrontmatter(f !== '');
            setMtime(conflict.current_mtime);
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
