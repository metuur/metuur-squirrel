import { useEffect } from 'react';

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  icon?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
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
      className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-ink/40 backdrop-blur-md sq-fade-in"
      onClick={onClose}
    >
      <div
        className={`w-full ${SIZE_CLASS[size]} panel max-h-[90vh] flex flex-col overflow-hidden sq-pop shadow-2xl`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative px-7 py-5 border-b border-hairline-2 bg-focus-tint/40 shrink-0">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-10 h-10 rounded-xl bg-focus-tint flex items-center justify-center shrink-0">
                <span className="material-icons text-accent">{icon}</span>
              </div>
              <div className="min-w-0">
                <h2 className="text-lg font-bold text-ink leading-tight truncate">
                  {title}
                </h2>
                {subtitle && (
                  <p className="text-xs text-ink-3 mt-0.5">{subtitle}</p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-2 text-ink-4 hover:text-ink-2 transition-colors shrink-0"
              aria-label="Close"
            >
              <span className="material-icons text-lg">close</span>
            </button>
          </div>
        </div>

        <div className="px-7 py-6 overflow-y-auto">
          {children}
        </div>

        <div className="px-7 py-4 bg-surface-2 border-t border-hairline-2 flex items-center justify-between shrink-0">
          <span className="text-[11px] text-ink-4">
            Press <kbd className="px-1.5 py-0.5 rounded bg-surface border border-hairline font-mono text-[10px]">Esc</kbd> to close
          </span>
          <div className="flex items-center gap-2">
            {footer ?? (
              <button
                onClick={onClose}
                className="btn btn-ghost px-4 py-1.5 text-sm font-semibold"
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
