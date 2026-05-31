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
      className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        aria-hidden
      >
        <line x1="12" x2="12" y1="5" y2="19" />
        <line x1="5" x2="19" y1="12" y2="12" />
      </svg>
      Add a note
    </button>
  );
}
