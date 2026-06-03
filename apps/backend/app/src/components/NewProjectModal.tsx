import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Modal } from '@/components/Modal';
import { MarkdownEditor } from '@/components/MarkdownEditor';
import { api, ApiError, type NewProjectRequest } from '@/api/client';
import { useToast } from '@/components/Toast';

const TAG_RE = /^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$/;

function toTag(name: string): string {
  return name.trim().toUpperCase().replace(/[^A-Z0-9]+/g, '-').replace(/^-|-$/g, '');
}

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated?: (slug: string) => void;
}

export function NewProjectModal({ open, onClose, onCreated }: Props) {
  const navigate = useNavigate();
  const { show: toast } = useToast();
  const [name, setName] = useState('');
  const [tag, setTag] = useState('');
  const [tagManuallyEdited, setTagManuallyEdited] = useState(false);
  const [projectType, setProjectType] = useState<'A' | 'B' | 'C'>('C');
  const [deadline, setDeadline] = useState('');
  const [description, setDescription] = useState('');
  const [stakeholders, setStakeholders] = useState('');
  const [firstIntentTag, setFirstIntentTag] = useState('');
  const [firstIntentTitle, setFirstIntentTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wipPrompt, setWipPrompt] = useState<string | null>(null);

  function reset() {
    setName('');
    setTag('');
    setTagManuallyEdited(false);
    setProjectType('C');
    setDeadline('');
    setDescription('');
    setStakeholders('');
    setFirstIntentTag('');
    setFirstIntentTitle('');
    setBusy(false);
    setError(null);
    setWipPrompt(null);
  }

  function close() {
    if (busy) return;
    reset();
    onClose();
  }

  async function submit(force: boolean) {
    setError(null);
    const trimmedName = name.trim();
    if (!trimmedName) {
      setError('Project name is required.');
      return;
    }
    const trimmed = tag.trim().toUpperCase();
    if (!TAG_RE.test(trimmed)) {
      setError('Tag must be UPPERCASE letters/digits, dash-separated (e.g. MYAPP or VISA-FAMILIA).');
      return;
    }
    const trimmedIntentTag = firstIntentTag.trim().toUpperCase();
    if (trimmedIntentTag) {
      if (!TAG_RE.test(trimmedIntentTag)) {
        setError('First intent tag must be UPPERCASE letters/digits, dash-separated (e.g. MYAPP-TASK).');
        return;
      }
      if (!firstIntentTitle.trim()) {
        setError('First intent title is required when a first intent tag is set.');
        return;
      }
    }
    const req: NewProjectRequest = {
      name: trimmedName,
      tag: trimmed,
      type: projectType,
      deadline: deadline || undefined,
      description: description.trim() || undefined,
      stakeholders: stakeholders.trim() || undefined,
      first_intent_tag: trimmedIntentTag || undefined,
      first_intent_title: firstIntentTitle.trim() || undefined,
      force: force || undefined,
    };
    setBusy(true);
    try {
      const res = await api.projectCreate(req);
      toast(`Created ${res.slug}` + (res.over_cap ? ' (over WIP cap)' : ''), 'success');
      reset();
      onClose();
      if (onCreated) onCreated(res.slug);
      navigate(`/projects/${res.slug}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409 && e.payload?.code === 'WIP_CAPACITY') {
        setWipPrompt(e.payload.error || 'Vault is at WIP capacity.');
      } else if (e instanceof ApiError && e.status === 409 && e.payload?.code === 'PROJECT_EXISTS') {
        setError(`A project named ${trimmed} already exists.`);
      } else if (e instanceof ApiError) {
        setError(e.payload?.error || e.message);
      } else {
        setError('Could not create the project. Please try again.');
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="New project"
      subtitle="Scaffolds the project page under 01-Proyectos-Activos/."
      icon="folder_special"
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
            onClick={() => submit(false)}
            disabled={busy || !name.trim() || !tag.trim()}
            className="btn btn-primary px-4 py-1.5 text-sm font-semibold disabled:opacity-50"
          >
            {busy ? 'Creating…' : 'Create project'}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        <Field label="Name">
          <input
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!tagManuallyEdited) setTag(toTag(e.target.value));
            }}
            placeholder="My Cool App"
            autoFocus
            disabled={busy}
            className="w-full text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />
        </Field>

        <Field label="Tag" hint="UPPERCASE, dash-separated. Auto-generated from name, editable.">
          <input
            value={tag}
            onChange={(e) => {
              setTagManuallyEdited(true);
              setTag(e.target.value);
            }}
            placeholder="MYAPP"
            disabled={busy}
            className="w-full font-mono text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none uppercase"
          />
        </Field>

        <Field label="Type" hint="A=mission-critical, B=important, C=experimental.">
          <div className="flex gap-2">
            {(['A', 'B', 'C'] as const).map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setProjectType(opt)}
                disabled={busy}
                className={`flex-1 py-2 text-sm font-semibold rounded-md border transition-all ${
                  projectType === opt
                    ? 'bg-accent text-surface border-accent shadow-sm'
                    : 'bg-surface text-ink-2 border-hairline hover:border-accent'
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
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

        <Field label="Description (optional)" hint="One line shown under the H1 in the project page.">
          <MarkdownEditor
            value={description}
            onChange={setDescription}
            disabled={busy}
            placeholder="Short summary"
            minHeight="5rem"
          />
        </Field>

        <Field label="Stakeholders (optional)" hint="Comma-separated names or @handles.">
          <input
            value={stakeholders}
            onChange={(e) => setStakeholders(e.target.value)}
            disabled={busy}
            placeholder="@alice, @bob"
            className="w-full text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />
        </Field>

        <Field label="First intent tag (optional)" hint="Creates an initial task file. UPPERCASE, dash-separated (e.g. MYAPP-SETUP).">
          <input
            value={firstIntentTag}
            onChange={(e) => setFirstIntentTag(e.target.value)}
            disabled={busy}
            placeholder="MYAPP-SETUP"
            className="w-full font-mono text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none uppercase"
          />
        </Field>

        <Field label="First intent title" hint="Required when a first intent tag is provided.">
          <input
            value={firstIntentTitle}
            onChange={(e) => setFirstIntentTitle(e.target.value)}
            disabled={busy}
            placeholder="Set up the initial project scaffold"
            className="w-full text-sm border border-hairline rounded-md px-3 py-2 bg-surface text-ink focus:border-accent focus:ring-1 focus:ring-accent outline-none"
          />
        </Field>

        {error && (
          <div className="rounded-md bg-critical-bg border border-critical/30 px-3 py-2 text-sm text-critical">
            {error}
          </div>
        )}

        {wipPrompt && (
          <div className="rounded-md bg-warning-bg border border-warning/30 px-3 py-3 text-sm text-warning space-y-2">
            <div>{wipPrompt}</div>
            <div className="flex gap-2">
              <button
                onClick={() => submit(true)}
                disabled={busy}
                className="px-3 py-1 text-xs font-semibold bg-warning hover:opacity-90 text-surface rounded transition-colors disabled:opacity-50"
              >
                Create anyway
              </button>
              <button
                onClick={() => setWipPrompt(null)}
                disabled={busy}
                className="px-3 py-1 text-xs font-semibold bg-surface text-warning border border-warning/30 rounded hover:bg-warning-bg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
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
