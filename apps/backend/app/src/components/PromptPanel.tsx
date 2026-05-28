import { useEffect, useState } from 'react';
import { headlessClaude } from '@/api/client';
import { useToast } from '@/components/Toast';
import { Modal } from '@/components/Modal';

interface Props {
  open: boolean;
  title: string;
  command: string;
  helpText?: string;
  /** Optional content (e.g. a recipient input) rendered above the command. */
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
          <div className="flex gap-3 p-3.5 rounded-xl bg-blue-50/70 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-900/40">
            <span className="material-icons text-blue-500 dark:text-blue-300 text-lg mt-0.5 shrink-0">info</span>
            <p className="text-xs leading-relaxed text-blue-900 dark:text-blue-100">{helpText}</p>
          </div>
        )}

        {preface && <div>{preface}</div>}

        {/* Slash command — terminal-style card with window chrome */}
        <div className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 shadow-sm">
          <div className="flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-400/70" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400/70" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400/70" />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 ml-2">
                Paste in Claude Code · Cursor · Codex
              </span>
            </div>
            <button
              onClick={() => copy(command, 'slash')}
              className={`px-2.5 py-1 text-[11px] font-semibold rounded-md inline-flex items-center gap-1 transition-all ${
                copiedSlash
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-200/60 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-300/70 dark:hover:bg-slate-600'
              }`}
            >
              <span className="material-icons text-sm">{copiedSlash ? 'check' : 'content_copy'}</span>
              {copiedSlash ? 'Copied' : 'Copy'}
            </button>
          </div>
          <pre className="px-4 py-3.5 bg-slate-900 text-emerald-300 text-sm font-mono leading-relaxed whitespace-pre-wrap break-all m-0">
            <span className="text-slate-500 select-none">$ </span>{command}
          </pre>
        </div>

        {/* Headless variant — collapsible chip */}
        <div>
          <button
            onClick={() => setShowHeadless((v) => !v)}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-full transition-all ${
              showHeadless
                ? 'bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-slate-100'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            <span className="material-icons text-sm">{showHeadless ? 'expand_less' : 'code'}</span>
            {showHeadless ? 'Hide headless variant' : 'Show headless variant'}
          </button>

          {showHeadless && (
            <div className="mt-3 space-y-2.5">
              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                Run from any terminal without an interactive session. Output goes to stdout — handy for piping.
              </p>
              <div className="rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between px-4 py-2 bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-700">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Headless · any shell
                  </span>
                  <button
                    onClick={() => copy(headless, 'headless')}
                    className={`px-2.5 py-1 text-[11px] font-semibold rounded-md inline-flex items-center gap-1 transition-all ${
                      copiedHeadless
                        ? 'bg-emerald-500 text-white'
                        : 'bg-slate-200/60 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-300/70 dark:hover:bg-slate-600'
                    }`}
                  >
                    <span className="material-icons text-sm">{copiedHeadless ? 'check' : 'content_copy'}</span>
                    {copiedHeadless ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <pre className="px-4 py-3 bg-slate-900 text-emerald-300 text-xs font-mono leading-relaxed whitespace-pre-wrap break-all m-0">
                  <span className="text-slate-500 select-none">$ </span>{headless}
                </pre>
              </div>
              <pre className="px-4 py-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 font-mono text-[11px] leading-relaxed text-slate-600 dark:text-slate-300 overflow-x-auto whitespace-pre-wrap break-all">
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
