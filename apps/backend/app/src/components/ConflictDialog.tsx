import { Modal } from '@/components/Modal';

export function ConflictDialog({
  open,
  payload,
  onTakeTheirs,
  onForceMine,
  onCancel,
}: {
  open: boolean;
  payload: { current_body: string; current_mtime: number } | null;
  onTakeTheirs: () => void;
  onForceMine: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal
      open={open}
      onClose={onCancel}
      title="Someone else just edited this"
      subtitle="Pick which version to keep"
      icon="warning"
      size="sm"
      footer={
        <>
          <button
            onClick={onCancel}
            className="px-4 py-1.5 text-sm font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-md transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onForceMine}
            className="px-4 py-1.5 text-sm font-semibold border border-border-light dark:border-border-dark text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-md transition-colors"
          >
            Keep mine
          </button>
          <button
            onClick={onTakeTheirs}
            disabled={!payload}
            className="bg-primary hover:bg-primary-dark text-white text-sm font-semibold px-4 py-1.5 rounded-md shadow-sm disabled:opacity-50"
          >
            Show their version
          </button>
        </>
      }
    >
      <div className="flex gap-3 p-3.5 rounded-xl bg-amber-50/70 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-900/40">
        <span className="material-icons text-amber-500 dark:text-amber-300 text-lg mt-0.5 shrink-0">info</span>
        <p className="text-xs leading-relaxed text-amber-900 dark:text-amber-100">
          A newer version of this file is already saved on disk. Keep your edits, or pull theirs in for review before overwriting.
        </p>
      </div>
    </Modal>
  );
}
