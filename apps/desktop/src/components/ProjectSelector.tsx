// Phase 2 ProjectSelector — chip row that picks the destination project
// for a new capture. Inbox = null (default). Today's focus project is
// highlighted so it's a single-click target without scanning the list.
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
      <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
        Save to
      </div>
      <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
        <Chip
          label="Inbox"
          isActive={selectedSlug === null}
          isFocus={false}
          onClick={() => onSelect(null)}
        />
        {sorted.map((p) => (
          <Chip
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

interface ChipProps {
  label: string;
  isActive: boolean;
  isFocus: boolean;
  onClick: () => void;
}

function Chip({ label, isActive, isFocus, onClick }: ChipProps) {
  let cls =
    "px-2 py-1 text-[11px] font-mono rounded-md border transition-colors cursor-pointer";
  if (isActive) {
    cls += " bg-primary/15 border-primary text-primary dark:bg-primary/25";
  } else if (isFocus) {
    cls +=
      " bg-amber-50 border-amber-300 text-amber-800 hover:bg-amber-100 dark:bg-amber-900/20 dark:border-amber-700/60 dark:text-amber-200";
  } else {
    cls +=
      " bg-white border-slate-200 text-slate-700 hover:bg-slate-50 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700";
  }
  return (
    <button type="button" onClick={onClick} className={cls}>
      {label}
    </button>
  );
}
