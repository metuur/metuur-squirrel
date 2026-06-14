import { Link, useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api, ApiError } from '@/api/client';
import { useFetch } from '@/hooks/useFetch';
import { ConflictDialog } from '@/components/ConflictDialog';
import { useToast } from '@/components/Toast';
import { MarkdownEditor } from '@/components/MarkdownEditor';

interface Prop {
  key: string;
  value: string;
  isNew?: boolean; // newly-added row → key is editable; existing keys are locked
}

// A value is a list when it's the `tags` key or looks like `[a, b, c]`.
function isListProp(p: Prop): boolean {
  return p.key.trim().toLowerCase() === 'tags' || /^\[[\s\S]*\]$/.test(p.value.trim());
}
function toTags(value: string): string[] {
  return value.trim().replace(/^\[|\]$/g, '').split(',').map((s) => s.trim()).filter(Boolean);
}
function fromTags(tags: string[]): string {
  return `[${tags.join(', ')}]`;
}

const STATUS_OPTIONS = ['pending', 'wip', 'done', 'blocked', 'paused'];

// Structural frontmatter fields (VAULT-002 required) — cannot be deleted.
const MANDATORY_KEYS = new Set(['id', 'type', 'project', 'status', 'created', 'tags']);

// Comma-separated chip editor (Enter or comma commits; × removes).
function TagsField({ tags, onChange, disabled }: { tags: string[]; onChange: (t: string[]) => void; disabled?: boolean }) {
  const [draft, setDraft] = useState('');
  function commit() {
    const parts = draft.split(',').map((s) => s.trim()).filter(Boolean);
    if (parts.length) onChange([...tags, ...parts.filter((p) => !tags.includes(p))]);
    setDraft('');
  }
  return (
    <div className="flex-1 flex flex-wrap items-center gap-1 border border-hairline rounded-md px-2 py-1 bg-surface min-h-[2.25rem]">
      {tags.map((t, i) => (
        <span key={i} className="inline-flex items-center gap-0.5 rounded bg-surface-2 px-1.5 py-0.5 text-xs text-ink-2">
          {t}
          <button
            type="button"
            disabled={disabled}
            onClick={() => onChange(tags.filter((_, j) => j !== i))}
            aria-label={`Remove ${t}`}
            className="text-ink-4 hover:text-critical"
          >
            <span className="material-icons text-[14px] leading-none">close</span>
          </button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); commit(); }
          else if (e.key === 'Backspace' && draft === '' && tags.length) onChange(tags.slice(0, -1));
        }}
        onBlur={commit}
        disabled={disabled}
        placeholder={tags.length ? '' : 'add tag…'}
        className="flex-1 min-w-[6rem] text-sm bg-transparent outline-none text-ink"
      />
    </div>
  );
}

// Split YAML frontmatter into ordered key/value pairs (flat `key: value` lines
// only — squirrel vault frontmatter is flat) and the markdown body that follows.
function parseFrontmatter(raw: string): { props: Prop[]; content: string } {
  const m = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!m) return { props: [], content: raw };
  const props: Prop[] = [];
  for (const line of m[1].split('\n')) {
    if (!line.trim() || line.startsWith(' ') || line.trimStart().startsWith('#')) continue;
    const i = line.indexOf(':');
    if (i < 0) continue;
    // Strip a YAML inline comment (whitespace + `#…`); `#` without a leading
    // space is part of the value (e.g. a hex colour), so it's kept.
    const value = line.slice(i + 1).replace(/\s+#.*$/, '').trim();
    props.push({ key: line.slice(0, i).trim(), value });
  }
  return { props, content: m[2] };
}

// Rebuild the frontmatter block from edited props. Drops rows with a blank key;
// emits nothing when there are no props (free notes stay frontmatter-free).
function serializeFrontmatter(props: Prop[]): string {
  const rows = props.filter((p) => p.key.trim() !== '');
  if (rows.length === 0) return '';
  return '---\n' + rows.map((p) => `${p.key.trim()}: ${p.value}`).join('\n') + '\n---\n';
}

// Keys we render with a native date picker. Anything else is a text field.
const DATE_KEYS = new Set(['deadline', 'created', 'reminder']);

export default function NoteEditPage() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const toast = useToast();
  const { data: note } = useFetch(`note-edit:${id}`, () => api.note(id));
  const [props, setProps] = useState<Prop[]>([]);
  const [body, setBody] = useState('');
  const [mtime, setMtime] = useState(0);
  const [saving, setSaving] = useState(false);
  const [conflict, setConflict] = useState<{ current_body: string; current_mtime: number } | null>(null);

  useEffect(() => {
    if (note) {
      const { props: p, content } = parseFrontmatter(note.raw_body);
      setProps(p);
      setBody(content);
      setMtime(note.mtime);
    }
  }, [note]);

  function updateKey(idx: number, key: string) {
    setProps((prev) => prev.map((p, i) => (i === idx ? { ...p, key } : p)));
  }
  function updateValue(idx: number, value: string) {
    setProps((prev) => prev.map((p, i) => (i === idx ? { ...p, value } : p)));
  }
  function removeRow(idx: number) {
    setProps((prev) => prev.filter((_, i) => i !== idx));
  }
  function addRow() {
    setProps((prev) => [...prev, { key: '', value: '', isNew: true }]);
  }

  async function save() {
    setSaving(true);
    try {
      const r = await api.noteSave(id, serializeFrontmatter(props) + body, mtime);
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
          <section>
            <div className="text-xs font-semibold text-ink-2 mb-2">Properties</div>
            <div className="space-y-2">
              {props.map((p, idx) => {
                const keyLc = p.key.trim().toLowerCase();
                const dateClean = p.value.trim();
                const asDate = DATE_KEYS.has(keyLc) && (dateClean === '' || /^\d{4}-\d{2}-\d{2}$/.test(dateClean));
                const valueClass =
                  'flex-1 text-sm border border-hairline rounded-md px-2 py-1.5 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none';
                return (
                  <div key={idx} className="flex items-center gap-2">
                    {p.isNew ? (
                      <input
                        value={p.key}
                        onChange={(e) => updateKey(idx, e.target.value)}
                        placeholder="property"
                        disabled={saving}
                        className="w-40 shrink-0 font-mono text-xs border border-hairline rounded-md px-2 py-1.5 bg-surface text-ink-2 focus:border-accent focus:ring-1 focus:ring-accent outline-none"
                      />
                    ) : (
                      <span className="w-40 shrink-0 font-mono text-xs text-ink-4 truncate self-center" title={p.key}>{p.key}</span>
                    )}
                    {asDate ? (
                      <input
                        type="date"
                        value={dateClean}
                        onChange={(e) => updateValue(idx, e.target.value)}
                        disabled={saving}
                        className={valueClass}
                      />
                    ) : isListProp(p) ? (
                      <TagsField
                        tags={toTags(p.value)}
                        onChange={(t) => updateValue(idx, fromTags(t))}
                        disabled={saving}
                      />
                    ) : keyLc === 'status' ? (
                      <select
                        value={p.value}
                        onChange={(e) => updateValue(idx, e.target.value)}
                        disabled={saving}
                        className={valueClass}
                      >
                        {!STATUS_OPTIONS.includes(p.value.trim()) && p.value.trim() !== '' && (
                          <option value={p.value.trim()}>{p.value.trim()}</option>
                        )}
                        {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    ) : (
                      <input
                        value={p.value}
                        onChange={(e) => updateValue(idx, e.target.value)}
                        disabled={saving}
                        className={valueClass}
                      />
                    )}
                    {MANDATORY_KEYS.has(keyLc) ? (
                      <span className="w-10 shrink-0" aria-hidden />
                    ) : (
                      <button
                        type="button"
                        onClick={() => removeRow(idx)}
                        disabled={saving}
                        title="Remove property"
                        aria-label="Remove property"
                        className="btn btn-ghost shrink-0 px-2 py-1.5 text-ink-4 hover:text-critical"
                      >
                        <span className="material-icons text-base">close</span>
                      </button>
                    )}
                  </div>
                );
              })}
              <button
                type="button"
                onClick={addRow}
                disabled={saving}
                className="btn btn-ghost px-2 py-1 text-xs font-semibold text-ink-3 flex items-center gap-1"
              >
                <span className="material-icons text-base">add</span> Add property
              </button>
            </div>
          </section>
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
            const { props: p, content } = parseFrontmatter(conflict.current_body);
            setProps(p);
            setBody(content);
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
