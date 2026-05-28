// Phase 2 CaptureButton — primary "+ Add a note" affordance.
// EARS R-3.1 (visible), R-3.2 (offline-disable), R-3.3 (click → modal).
// Sized to content; the parent footer handles layout + spacing.

interface Props {
  online: boolean;
  onClick: () => void;
}

export function CaptureButton({ online, onClick }: Props) {
  const disabled = !online;
  return (
    <button
      type="button"
      onClick={() => !disabled && onClick()}
      disabled={disabled}
      title={disabled ? "Backend offline — capture will fail" : undefined}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
        disabled
          ? "bg-slate-200 text-slate-400 cursor-not-allowed dark:bg-slate-700 dark:text-slate-500"
          : "bg-primary text-white hover:bg-primary-dark"
      }`}
    >
      <span aria-hidden className="text-base leading-none">+</span>
      Add a note
    </button>
  );
}
