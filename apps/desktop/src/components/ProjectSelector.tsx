// Phase 2 ProjectSelector — small button row that picks the destination
// project for a new capture. Inbox = null (default). Today's focus project
// is highlighted so it's a single-click target without scanning the list.
//
// Renders inside CaptureModal above the textarea. Hides itself entirely
// if no projects are available (e.g. backend offline at modal-open time).

import type { ProjectListItem } from "../api/client";

interface Props {
  projects: ProjectListItem[];
  focusSlug: string | null;
  selectedSlug: string | null;
  onSelect: (slug: string | null) => void;
}

export function ProjectSelector({ projects, focusSlug, selectedSlug, onSelect }: Props) {
  if (projects.length === 0) return null;

  // Focus project first, then alphabetical by slug.
  const sorted = [...projects].sort((a, b) => {
    if (a.slug === focusSlug) return -1;
    if (b.slug === focusSlug) return 1;
    return a.slug.localeCompare(b.slug);
  });

  return (
    <div className="space-y-1.5">
      <div className="eyebrow">Save to</div>
      <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
        <Pick
          label="Inbox"
          isActive={selectedSlug === null}
          isFocus={false}
          onClick={() => onSelect(null)}
        />
        {sorted.map((p) => (
          <Pick
            key={p.slug}
            label={p.slug}
            isActive={selectedSlug === p.slug}
            isFocus={p.slug === focusSlug}
            onClick={() => onSelect(p.slug)}
          />
        ))}
      </div>
    </div>
  );
}

interface PickProps {
  label: string;
  isActive: boolean;
  isFocus: boolean;
  onClick: () => void;
}

const ACTIVE_STYLE: React.CSSProperties = {
  background: "rgba(31, 58, 138, 0.10)",
  borderColor: "var(--color-accent)",
  color: "var(--color-accent)",
};
const FOCUS_STYLE: React.CSSProperties = {
  background: "var(--color-warning-bg)",
  borderColor: "rgba(197, 106, 20, 0.28)",
  color: "var(--color-warning)",
};

function Pick({ label, isActive, isFocus, onClick }: PickProps) {
  // Compact, mono-typed picker. Order of precedence: active > focus > default.
  let style: React.CSSProperties | undefined;
  let cls = "px-2 py-1 text-[11px] font-mono rounded-md border transition-colors cursor-pointer";
  if (isActive) {
    style = ACTIVE_STYLE;
  } else if (isFocus) {
    style = FOCUS_STYLE;
  } else {
    cls += " bg-surface border-hairline text-ink-2 hover:bg-surface-2";
  }
  return (
    <button type="button" onClick={onClick} className={cls} style={style}>
      {label}
    </button>
  );
}
