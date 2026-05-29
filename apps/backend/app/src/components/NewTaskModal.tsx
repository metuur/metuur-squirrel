import { useState } from 'react';
import { Modal } from '@/components/Modal';
import { MarkdownEditor } from '@/components/MarkdownEditor';
import { api, ApiError, type NewIntentRequest } from '@/api/client';

const TAG_RE = /^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$/;

interface Props {
  open: boolean;
  projectSlug: string;
  suggestedTags?: string[];
  onClose: () => void;
  onCreated?: () => void;
}

export function NewTaskModal({ open, projectSlug, suggestedTags, onClose, onCreated }: Props) {
  const initTags = () => suggestedTags?.length ? suggestedTags : [projectSlug];
  const [localTags, setLocalTags] = useState<string[]>(initTags);
  const [tag, setTag] = useState(projectSlug);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [deadline, setDeadline] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setLocalTags(initTags());
    setTag(projectSlug);
    setTitle('');
    setDescription('');
    setDeadline('');
    setBusy(false);
    setError(null);
  }

  function close() {
    if (busy) return;
    reset();
    onClose();
  }

  function removeTag(t: string) {
    setLocalTags((prev) => prev.filter((x) => x !== t));
    if (tag === t) setTag(projectSlug);
  }

  function addTagChip() {
    const trimmed = tag.trim().toUpperCase();
    if (!trimmed || !TAG_RE.test(trimmed)) return;
    if (!localTags.includes(trimmed)) {
      setLocalTags((prev) => [...prev, trimmed]);
    }
    setTag(trimmed);
  }

  async function submit() {
    setError(null);
    const trimmedTag = tag.trim().toUpperCase();
    if (!TAG_RE.test(trimmedTag)) {
      setError('Tag must be UPPERCASE letters/digits, dash-separated (e.g. MYAPP-TASK).');
      return;
    }
    if (!title.trim()) {
      setError('Title is required.');
      return;
    }
    const req: NewIntentRequest = {
      project_slug: projectSlug,
      tag: trimmedTag,
      title: title.trim(),
      description: description.trim() || undefined,
      deadline: deadline || undefined,
    };
    setBusy(true);
    try {
      await api.intentCreate(req);
      reset();
      onClose();
      if (onCreated) onCreated();
    } catch (e) {
      if (e instanceof ApiError) {
        setError(e.payload?.error || e.message);
      } else {
        setError('Could not create the task. Please try again.');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="New task"
      subtitle={`Creates a task file in project ${projectSlug}.`}
      icon="task_alt"
      size="md"
      footer={
        <>
          <button
            onClick={close}
            disabled={busy}
            className="px-4 py-1.5 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-md transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy || !tag.trim() || !title.trim()}
            className="px-4 py-1.5 text-sm font-semibold bg-primary hover:bg-primary-dark text-white rounded-md shadow-sm transition-colors disabled:opacity-50"
          >
            {busy ? 'Creating…' : 'Create task'}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Tag" hint="UPPERCASE, dash-separated. e.g. MYAPP-TASK, VISA-SETUP. Press Enter to add a new tag.">
          {localTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {localTags.map((t) => (
                <span
                  key={t}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono rounded border transition-colors ${
                    tag.toUpperCase() === t
                      ? 'bg-primary text-white border-primary'
                      : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-300 dark:border-slate-600'
                  }`}
                >
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => setTag(t)}
                    className="hover:underline"
                  >
                    {t}
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => removeTag(t)}
                    className="opacity-60 hover:opacity-100 leading-none"
                    aria-label={`Remove ${t}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-1.5">
            <input
              value={tag}
              onChange={(e) => setTag(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTagChip(); } }}
              placeholder="TYPE-NEW-TAG"
              autoFocus
              disabled={busy}
              className="flex-1 font-mono text-sm border border-slate-300 dark:border-slate-600 rounded-md px-3 py-2 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:border-primary focus:ring-1 focus:ring-primary outline-none uppercase"
            />
            <button
              type="button"
              disabled={busy}
              onClick={addTagChip}
              className="px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-md text-slate-600 dark:text-slate-300 hover:border-primary hover:text-primary transition-colors"
              aria-label="Add tag"
            >
              <span className="material-icons text-base leading-none">add</span>
            </button>
          </div>
        </Field>

        <Field label="Title">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Short description of the task"
            disabled={busy}
            className="w-full text-sm border border-slate-300 dark:border-slate-600 rounded-md px-3 py-2 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:border-primary focus:ring-1 focus:ring-primary outline-none"
          />
        </Field>

        <Field label="Description (optional)">
          <MarkdownEditor
            value={description}
            onChange={setDescription}
            disabled={busy}
            placeholder="Additional context"
            minHeight="6rem"
          />
        </Field>

        <Field label="Deadline (optional)">
          <input
            type="date"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            disabled={busy}
            className="w-full text-sm border border-slate-300 dark:border-slate-600 rounded-md px-3 py-2 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:border-primary focus:ring-1 focus:ring-primary outline-none"
          />
        </Field>

        {error && (
          <div className="rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-3 py-2 text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        )}
      </div>
    </Modal>
  );
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-1">{label}</div>
      {children}
      {hint && <div className="text-[11px] text-slate-400 dark:text-slate-500 mt-1">{hint}</div>}
    </label>
  );
}
