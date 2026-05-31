import { useState } from 'react';
import { Modal } from '@/components/Modal';
import { MarkdownEditor } from '@/components/MarkdownEditor';
import { api, ApiError, type NewIntentRequest } from '@/api/client';

const TAG_RE = /^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$/;

function titleToFilename(title: string): string {
  return title
    .toUpperCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^A-Z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60);
}

interface Props {
  open: boolean;
  projectSlug: string;
  suggestedTags?: string[];
  onClose: () => void;
  onCreated?: () => void;
}

export function NewTaskModal({ open, projectSlug, suggestedTags, onClose, onCreated }: Props) {
  const [tag, setTag] = useState(suggestedTags?.length ? suggestedTags[0] : projectSlug);
  const [title, setTitle] = useState('');
  const [filename, setFilename] = useState('');
  const [filenameEdited, setFilenameEdited] = useState(false);
  const [description, setDescription] = useState('');
  const [deadline, setDeadline] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTag(suggestedTags?.length ? suggestedTags[0] : projectSlug);
    setTitle('');
    setFilename('');
    setFilenameEdited(false);
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

  function handleTitleChange(value: string) {
    setTitle(value);
    if (!filenameEdited) {
      setFilename(titleToFilename(value));
    }
  }

  function handleFilenameChange(value: string) {
    setFilename(value.toUpperCase());
    setFilenameEdited(value !== '' && value !== titleToFilename(title));
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
    const trimmedFilename = filename.trim();
    if (!TAG_RE.test(trimmedFilename)) {
      setError('File name must be UPPERCASE letters/digits, dash-separated (e.g. TRABAJO-PROYECTO-A).');
      return;
    }
    const req: NewIntentRequest = {
      project_slug: projectSlug,
      tag: trimmedTag,
      filename: trimmedFilename,
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

  const canSubmit = TAG_RE.test(tag.trim().toUpperCase()) && title.trim() !== '' && TAG_RE.test(filename.trim());

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
            className="btn btn-ghost px-4 py-1.5 text-sm font-semibold disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={busy || !canSubmit}
            className="btn btn-primary px-4 py-1.5 text-sm font-semibold disabled:opacity-50"
          >
            {busy ? 'Creating…' : 'Create task'}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Tag" hint="UPPERCASE, dash-separated. Groups related tasks (e.g. VISA-SETUP). Multiple tasks can share the same tag.">
          <input
            value={tag}
            onChange={(e) => setTag(e.target.value)}
            placeholder="MYAPP-TASK"
            autoFocus
            disabled={busy}
            className="w-full font-mono text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none uppercase"
          />
        </Field>

        <Field label="Title">
          <input
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            placeholder="Short description of the task"
            disabled={busy}
            className="w-full text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />
        </Field>

        <Field label="File name" hint={`The .md file that will be created (e.g. ${filename || 'TRABAJO-PROYECTO-A'}.md). Auto-filled from title — edit to customise.`}>
          <div className="flex items-center gap-1">
            <input
              value={filename}
              onChange={(e) => handleFilenameChange(e.target.value)}
              placeholder="TRABAJO-PROYECTO-A"
              disabled={busy}
              className="flex-1 font-mono text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none uppercase"
            />
            <span className="text-sm text-ink-4 select-none">.md</span>
          </div>
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
            className="w-full text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />
        </Field>

        {error && (
          <div className="rounded-md bg-critical-bg border border-critical/30 px-3 py-2 text-sm text-critical">
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
      <div className="text-xs font-semibold text-ink-2 mb-1">{label}</div>
      {children}
      {hint && <div className="text-[11px] text-ink-4 mt-1">{hint}</div>}
    </label>
  );
}
