import { createContext, useContext, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { api } from '@/api/client';
import { useFetch } from '@/hooks/useFetch';
import { useToast } from '@/components/Toast';
import { Modal } from '@/components/Modal';
import { MarkdownEditor } from '@/components/MarkdownEditor';

interface CaptureCtx { open: (defaultProject?: string) => void }
const Ctx = createContext<CaptureCtx>({ open: () => {} });
export const useCapture = () => useContext(Ctx);

export function CaptureProvider({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const [defaultProject, setDefaultProject] = useState('');
  return (
    <Ctx.Provider value={{ open: (slug) => { setDefaultProject(slug ?? ''); setOpen(true); } }}>
      {children}
      <CaptureDialog open={open} onClose={() => setOpen(false)} defaultProject={defaultProject} />
    </Ctx.Provider>
  );
}

type Mode = 'note' | 'email';

function CaptureDialog({ open, onClose, defaultProject }: { open: boolean; onClose: () => void; defaultProject: string }) {
  const location = useLocation();
  const toast = useToast();
  const [mode, setMode] = useState<Mode>('note');
  const [text, setText] = useState('');
  const [emailFrom, setEmailFrom] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [project, setProject] = useState('');
  const [saving, setSaving] = useState(false);
  const { data: projects } = useFetch(open ? 'projects-list' : null, () => api.projects());

  useEffect(() => {
    if (!open) return;
    if (defaultProject) { setProject(defaultProject); return; }
    const m = location.pathname.match(/^\/projects\/([A-Z0-9_-]+)/);
    setProject(m ? m[1] : 'unfiled');
    setMode('note');
    setText('');
    setEmailFrom('');
    setEmailSubject('');
  }, [open, defaultProject, location.pathname]);

  function buildPayload(): string {
    if (mode === 'note') return text.trim();
    const today = new Date().toISOString().slice(0, 10);
    const header = [
      emailFrom.trim() && `**From:** ${emailFrom.trim()}`,
      emailSubject.trim() && `**Subject:** ${emailSubject.trim()}`,
      `**Received:** ${today}`,
    ].filter(Boolean).join('  \n');
    return `📧 Email\n\n${header}\n\n---\n\n${text.trim()}`;
  }

  async function submit() {
    if (!text.trim()) {
      toast.show(mode === 'email' ? 'Paste the email body first.' : 'Write something first.', 'error');
      return;
    }
    if (mode === 'email' && !emailSubject.trim() && !emailFrom.trim()) {
      toast.show('Add at least a From or Subject so you can find this later.', 'error');
      return;
    }
    setSaving(true);
    try {
      await api.noteCreate(buildPayload(), project === 'unfiled' ? null : project);
      toast.show('Saved.', 'success');
      onClose();
      setTimeout(() => window.location.reload(), 250);
    } catch (e: any) {
      toast.show(e?.message ?? 'Could not save.', 'error');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={mode === 'email' ? 'Save an email to notes' : 'Add a note'}
      subtitle={mode === 'email' ? 'Capture an incoming email into the right project' : 'Quick capture into the project of your choice'}
      icon={mode === 'email' ? 'mail' : 'edit_note'}
      footer={
        <>
          <button
            onClick={onClose}
            disabled={saving}
            className="btn btn-ghost px-4 py-1.5 text-sm font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={submit}
            disabled={saving}
            className="btn btn-primary text-sm font-semibold px-4 py-1.5 flex items-center gap-1"
          >
            {saving ? (
              <span className="w-4 h-4 border-2 border-surface/40 border-t-surface rounded-full animate-spin" />
            ) : (
              <span className="material-icons text-lg">save</span>
            )}
            {saving ? 'Saving…' : 'Save'}
          </button>
        </>
      }
    >
      <div className="space-y-5">
        <div className="inline-flex bg-surface-2 p-0.5 rounded-full border border-hairline">
          {(['note', 'email'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-full inline-flex items-center gap-1 transition-all ${
                mode === m
                  ? 'text-accent bg-surface shadow-sm'
                  : 'text-ink-3 hover:text-ink-2'
              }`}
            >
              <span className="material-icons text-sm">{m === 'note' ? 'edit_note' : 'mail'}</span>
              {m === 'note' ? 'Quick note' : 'Paste email'}
            </button>
          ))}
        </div>

        {mode === 'email' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block eyebrow mb-1">From</label>
              <input
                value={emailFrom}
                onChange={(e) => setEmailFrom(e.target.value)}
                placeholder="sarah@acme.com"
                className="w-full px-3 py-2 border border-hairline rounded-lg bg-surface text-sm text-ink placeholder-ink-4 focus:border-accent focus:ring-0 outline-none"
              />
            </div>
            <div>
              <label className="block eyebrow mb-1">Subject</label>
              <input
                value={emailSubject}
                onChange={(e) => setEmailSubject(e.target.value)}
                placeholder="API timeout on /orders"
                className="w-full px-3 py-2 border border-hairline rounded-lg bg-surface text-sm text-ink placeholder-ink-4 focus:border-accent focus:ring-0 outline-none"
              />
            </div>
          </div>
        )}

        <MarkdownEditor
          value={text}
          onChange={setText}
          placeholder={mode === 'email' ? 'Paste the email body here…' : 'Type your note here…'}
          minHeight={mode === 'email' ? '12rem' : '9rem'}
        />

        <div>
          <label className="block eyebrow mb-1">
            Add to project
          </label>
          <select
            value={project}
            onChange={(e) => setProject(e.target.value)}
            className="w-full px-3 py-2 border border-hairline rounded-lg bg-surface text-sm text-ink-2 focus:border-accent focus:ring-0 outline-none"
          >
            <option value="unfiled">Unfiled (Inbox)</option>
            {(projects ?? []).map((p) => (
              <option key={p.slug} value={p.slug}>{p.title}</option>
            ))}
          </select>
        </div>
      </div>
    </Modal>
  );
}
