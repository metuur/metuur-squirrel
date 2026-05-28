import { useEffect } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  /** Title shown in the header. */
  title: string;
  /** Optional small line under the title (e.g. "Copy the command, run it in your AI agent"). */
  subtitle?: string;
  /** Material-icons name for the header chip. */
  icon?: string;
  /** Body content. Pad it yourself if you need custom layout — the modal gives you space. */
  children: React.ReactNode;
  /** Right-aligned footer actions (buttons). If omitted, footer shows just a Close button. */
  footer?: React.ReactNode;
  /** Modal width. Defaults to max-w-2xl. */
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_CLASS: Record<NonNullable<ModalProps['size']>, string> = {
  sm: 'max-w-md',
  md: 'max-w-2xl',
  lg: 'max-w-3xl',
};

export function Modal({ open, onClose, title, subtitle, icon = 'bolt', children, footer, size = 'md' }: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-md sq-fade-in"
      onClick={onClose}
    >
      <div
        className={`w-full ${SIZE_CLASS[size]} bg-white dark:bg-surface-dark rounded-2xl shadow-2xl border border-border-light dark:border-border-dark max-h-[90vh] flex flex-col overflow-hidden sq-pop`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative px-7 py-5 bg-gradient-to-br from-primary/5 via-transparent to-transparent border-b border-border-light dark:border-border-dark shrink-0">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-primary/10 dark:bg-primary/20 flex items-center justify-center shrink-0">
                <span className="material-icons text-primary">{icon}</span>
              </div>
              <div className="min-w-0">
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100 leading-tight truncate">
                  {title}
                </h2>
                {subtitle && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-200/60 dark:hover:bg-slate-700/60 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors shrink-0"
              aria-label="Close"
            >
              <span className="material-icons text-lg">close</span>
            </button>
          </div>
        </div>

        <div className="px-7 py-6 overflow-y-auto">
          {children}
        </div>

        <div className="px-7 py-4 bg-slate-50/50 dark:bg-slate-800/30 border-t border-border-light dark:border-border-dark flex items-center justify-between shrink-0">
          <span className="text-[11px] text-slate-400 dark:text-slate-500">
            Press <kbd className="px-1.5 py-0.5 rounded bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 font-mono text-[10px]">Esc</kbd> to close
          </span>
          <div className="flex items-center gap-2">
            {footer ?? (
              <button
                onClick={onClose}
                className="px-4 py-1.5 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-md transition-colors"
              >
                Close
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
