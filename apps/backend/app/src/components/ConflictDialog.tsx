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
            className="btn btn-ghost px-4 py-1.5 text-sm font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={onForceMine}
            className="btn px-4 py-1.5 text-sm font-semibold"
          >
            Keep mine
          </button>
          <button
            onClick={onTakeTheirs}
            disabled={!payload}
            className="btn btn-primary px-4 py-1.5 text-sm font-semibold disabled:opacity-50"
          >
            Show their version
          </button>
        </>
      }
    >
      <div className="flex gap-3 p-3.5 rounded-xl bg-warning-bg border border-warning/30">
        <span className="material-icons text-warning text-lg mt-0.5 shrink-0">info</span>
        <p className="text-xs leading-relaxed text-ink-2">
          A newer version of this file is already saved on disk. Keep your edits, or pull theirs in for review before overwriting.
        </p>
      </div>
    </Modal>
  );
}
