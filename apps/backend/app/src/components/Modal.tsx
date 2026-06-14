import { useEffect, useId, useRef } from 'react';

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

const FOCUSABLE = 'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function Modal({ open, onClose, title, subtitle, icon = 'bolt', children, footer, size = 'md' }: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  // Hold the latest onClose so the focus-management effect can depend only on
  // `open` — otherwise a new onClose identity each render would re-run the
  // effect and yank focus back into the dialog on every keystroke.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;

    // Restore focus to whatever was focused before the dialog opened.
    const previouslyFocused = document.activeElement as HTMLElement | null;
    // Move focus into the dialog (first focusable, falling back to the panel).
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel)?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { onCloseRef.current(); return; }
      if (e.key !== 'Tab' || !panel) return;
      // Minimal focus trap: wrap Tab/Shift+Tab at the dialog's edges.
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE));
      if (items.length === 0) { e.preventDefault(); return; }
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstItem) {
        e.preventDefault(); lastItem.focus();
      } else if (!e.shiftKey && document.activeElement === lastItem) {
        e.preventDefault(); firstItem.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      previouslyFocused?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-ink/40 backdrop-blur-md sq-fade-in"
      onClick={onClose}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
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
                <h2 id={titleId} className="text-lg font-bold text-ink leading-tight truncate">
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
