import { useEffect, useState } from 'react';
import { headlessClaude } from '@/api/client';
import { useToast } from '@/components/Toast';
import { Modal } from '@/components/Modal';

interface Props {
  open: boolean;
  title: string;
  command: string;
  helpText?: string;
  preface?: React.ReactNode;
  onClose: () => void;
}

export function PromptPanel({ open, title, command, helpText, preface, onClose }: Props) {
  const toast = useToast();
  const [copiedSlash, setCopiedSlash] = useState(false);
  const [copiedHeadless, setCopiedHeadless] = useState(false);
  const [showHeadless, setShowHeadless] = useState(false);
  const headless = headlessClaude(command);

  useEffect(() => {
    if (!open) setShowHeadless(false);
  }, [open]);

  async function copy(text: string, which: 'slash' | 'headless') {
    try {
      await navigator.clipboard.writeText(text);
      if (which === 'slash') {
        setCopiedSlash(true);
        window.setTimeout(() => setCopiedSlash(false), 1500);
      } else {
        setCopiedHeadless(true);
        window.setTimeout(() => setCopiedHeadless(false), 1500);
      }
      toast.show('Copied to clipboard.', 'success');
    } catch {
      toast.show('Could not copy. Select the text manually.', 'error');
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      subtitle="Copy the command, run it in your AI agent"
      icon="terminal"
    >
      <div className="space-y-5">
        {helpText && (
          <div className="flex gap-3 p-3.5 rounded-xl bg-focus-tint border border-focus-edge">
            <span className="material-icons text-accent text-lg mt-0.5 shrink-0">info</span>
            <p className="text-xs leading-relaxed text-ink-2">{helpText}</p>
          </div>
        )}

        {preface && <div>{preface}</div>}

        <div className="rounded-xl overflow-hidden border border-hairline shadow-sm">
          <div className="flex items-center justify-between px-4 py-2 bg-surface-2 border-b border-hairline">
            <div className="flex items-center gap-2">
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-critical/70" />
                <span className="w-2.5 h-2.5 rounded-full bg-warning/70" />
                <span className="w-2.5 h-2.5 rounded-full bg-ok/70" />
              </div>
              <span className="eyebrow ml-2">
                Paste in Claude Code · Cursor · Codex
              </span>
            </div>
            <button
              onClick={() => copy(command, 'slash')}
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-md inline-flex items-center gap-1 transition-all ${
                copiedSlash
                  ? 'bg-ok text-surface'
                  : 'bg-surface text-ink-2 border border-hairline hover:bg-surface-2'
              }`}
            >
              <span className="material-icons text-sm">{copiedSlash ? 'check' : 'content_copy'}</span>
              {copiedSlash ? 'Copied' : 'Copy'}
            </button>
          </div>
          <pre className="px-4 py-3.5 bg-ink text-ok text-sm font-mono leading-relaxed whitespace-pre-wrap break-all m-0">
            <span className="text-ink-4 select-none">$ </span>{command}
          </pre>
        </div>

        <div>
          <button
            onClick={() => setShowHeadless((v) => !v)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-full transition-all ${
              showHeadless
                ? 'bg-surface-2 text-ink border border-hairline'
                : 'bg-surface text-ink-3 border border-hairline hover:bg-surface-2'
            }`}
          >
            <span className="material-icons text-sm">{showHeadless ? 'expand_less' : 'code'}</span>
            {showHeadless ? 'Hide headless variant' : 'Show headless variant'}
          </button>

          {showHeadless && (
            <div className="mt-3 space-y-2.5">
              <p className="text-xs text-ink-3 leading-relaxed">
                Run from any terminal without an interactive session. Output goes to stdout — handy for piping.
              </p>
              <div className="rounded-xl overflow-hidden border border-hairline">
                <div className="flex items-center justify-between px-4 py-2 bg-surface-2 border-b border-hairline">
                  <span className="eyebrow">
                    Headless · any shell
                  </span>
                  <button
                    onClick={() => copy(headless, 'headless')}
                    className={`px-2.5 py-1 text-[11px] font-semibold rounded-md inline-flex items-center gap-1 transition-all ${
                      copiedHeadless
                        ? 'bg-ok text-surface'
                        : 'bg-surface text-ink-2 border border-hairline hover:bg-surface-2'
                    }`}
                  >
                    <span className="material-icons text-sm">{copiedHeadless ? 'check' : 'content_copy'}</span>
                    {copiedHeadless ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <pre className="px-4 py-3 bg-ink text-ok text-xs font-mono leading-relaxed whitespace-pre-wrap break-all m-0">
                  <span className="text-ink-4 select-none">$ </span>{headless}
                </pre>
              </div>
              <pre className="px-4 py-3 rounded-xl bg-surface-2 border border-hairline font-mono text-[11px] leading-relaxed text-ink-3 overflow-x-auto whitespace-pre-wrap break-all">
{`# Result straight to clipboard (macOS)
${headless} | pbcopy

# Pipe to a file
${headless} > brief.md`}
              </pre>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
