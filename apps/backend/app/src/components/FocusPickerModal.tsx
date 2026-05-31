import { useEffect, useState } from 'react';
import { api, ApiError, type ManualFocusPayload, type ManualPick, type ProjectListItem, type NoteSummary } from '@/api/client';

interface Props {
  slot: 'today' | 'week';
  projects: ProjectListItem[];
  currentAmPick?: ManualPick | null;
  currentPmPick?: ManualPick | null;
  onClose: () => void;
  onPicked?: (result: ManualFocusPayload) => void;
}

interface PendingIntent {
  projectSlug: string;
  projectTitle: string;
  intentSlug: string;
  intentTitle: string;
}

const VIOLET = '#8B5CF6';

const SLOT_NEUTRAL_BG: React.CSSProperties = {
  background: 'var(--color-surface-2)',
  borderColor: 'var(--color-hairline)',
};
const SLOT_NEUTRAL_BG_ACTIVE: React.CSSProperties = {
  background: 'rgba(14, 17, 22, 0.06)',
  borderColor: 'var(--color-ink-3)',
};
const SLOT_AM_BG: React.CSSProperties = {
  background: 'rgba(31, 58, 138, 0.06)',
  borderColor: 'rgba(31, 58, 138, 0.25)',
};
const SLOT_AM_BG_ACTIVE: React.CSSProperties = {
  background: 'rgba(31, 58, 138, 0.12)',
  borderColor: 'var(--color-accent)',
};
const SLOT_PM_BG: React.CSSProperties = {
  background: 'rgba(139, 92, 246, 0.06)',
  borderColor: 'rgba(139, 92, 246, 0.25)',
};
const SLOT_PM_BG_ACTIVE: React.CSSProperties = {
  background: 'rgba(139, 92, 246, 0.12)',
  borderColor: VIOLET,
};
const CURRENT_BADGE_STYLE: React.CSSProperties = {
  background: 'var(--color-ink)',
  color: 'var(--color-bg)',
};

export function FocusPickerModal({
  slot,
  projects,
  currentAmPick,
  currentPmPick,
  onClose,
  onPicked,
}: Props) {
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
  const [intentsBySlug, setIntentsBySlug] = useState<Record<string, NoteSummary[]>>({});
  const [loadingSlug, setLoadingSlug] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState<PendingIntent | null>(null);

  const onStep2 = slot === 'today' && pending !== null;
  const hasAM = !!currentAmPick;
  const hasPM = !!currentPmPick;
  const isAllDay = !!(
    currentAmPick && currentPmPick &&
    currentAmPick.intent_slug === currentPmPick.intent_slug
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) {
        if (onStep2) setPending(null);
        else onClose();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose, submitting, onStep2]);

  const handleExpand = async (slug: string) => {
    if (submitting) return;
    if (expandedSlug === slug) { setExpandedSlug(null); return; }
    setExpandedSlug(slug);
    if (intentsBySlug[slug]) return;
    setLoadingSlug(slug);
    setError(null);
    try {
      const detail = await api.project(slug);
      setIntentsBySlug((prev) => ({ ...prev, [slug]: detail.notes }));
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingSlug((cur) => (cur === slug ? null : cur));
    }
  };

  const handleIntentClick = (p: ProjectListItem, intent: NoteSummary) => {
    if (submitting) return;
    if (slot === 'week') {
      submitFocus('week', p.slug, intent.id);
    } else {
      setPending({ projectSlug: p.slug, projectTitle: p.title, intentSlug: intent.id, intentTitle: intent.title });
    }
  };

  const submitFocus = async (
    focusSlot: 'today' | 'today_pm' | 'week' | 'all_day',
    projectSlug: string,
    intentSlug: string,
  ) => {
    setSubmitting(true);
    setError(null);
    try {
      if (focusSlot === 'all_day') {
        await api.focusSet('today', { clear: true });
        await api.focusSet('today_pm', { clear: true });
        await api.focusSet('today', { project_slug: projectSlug, intent_slug: intentSlug });
        const result = await api.focusSet('today_pm', { project_slug: projectSlug, intent_slug: intentSlug });
        onPicked?.(result);
      } else {
        const result = await api.focusSet(focusSlot, { project_slug: projectSlug, intent_slug: intentSlug });
        onPicked?.(result);
      }
      onClose();
    } catch (err) {
      setError(err instanceof ApiError || err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  };

  const handleSlotChoice = (half: 'all' | 'am' | 'pm') => {
    if (!pending) return;
    if (half === 'all') submitFocus('all_day', pending.projectSlug, pending.intentSlug);
    else if (half === 'am') submitFocus('today', pending.projectSlug, pending.intentSlug);
    else submitFocus('today_pm', pending.projectSlug, pending.intentSlug);
  };

  const backdropClass = 'fixed inset-0 z-[200] flex items-center justify-center p-4 backdrop-blur-md sq-fade-in';
  const backdropStyle: React.CSSProperties = { background: 'rgba(14, 17, 22, 0.45)' };
  const cardClass = 'panel w-full max-w-md flex flex-col max-h-[90vh] sq-pop shadow-2xl';

  // Step 2: When? (AM / PM / All day)
  if (onStep2 && pending) {
    const allDayNote = isAllDay
      ? 'Replaces current all-day focus — sets both slots to this task'
      : hasAM || hasPM
        ? 'Replaces current focus — sets both morning and afternoon'
        : 'Sets both morning and afternoon for today';
    const amNote = isAllDay
      ? 'Splits all-day — morning becomes this task, afternoon stays'
      : hasAM
        ? `Replaces morning focus${hasPM ? ' (afternoon stays)' : ''}`
        : `Sets morning focus${hasPM ? ' (afternoon stays)' : ''}`;
    const pmNote = isAllDay
      ? 'Splits all-day — afternoon becomes this task, morning stays'
      : hasPM
        ? `Replaces afternoon focus${hasAM ? ' (morning stays)' : ''}`
        : `Sets afternoon focus${hasAM ? ' (morning stays)' : ''}`;

    return (
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Choose when to focus"
        className={backdropClass}
        style={backdropStyle}
        onClick={(e) => { if (e.target === e.currentTarget && !submitting) setPending(null); }}
      >
        <div className={cardClass} onClick={(e) => e.stopPropagation()}>
          <div className="px-4 py-3 border-b border-hairline">
            <h2 className="title text-sm">When will you work on this?</h2>
          </div>
          <div className="px-4 py-4 flex flex-col gap-3">
            {error && (
              <div className="bg-critical-bg text-critical px-2.5 py-1.5 rounded text-[11px] border border-critical/30">
                {error}
              </div>
            )}
            <p className="text-xs text-ink-2 leading-relaxed">
              <span className="font-semibold">{pending.projectTitle}</span>
              {' — '}
              {pending.intentTitle}
            </p>
            <div className="flex flex-col gap-2">
              <button
                type="button"
                onClick={() => handleSlotChoice('all')}
                disabled={submitting}
                className="w-full px-3 py-2.5 rounded-xl border-2 text-left disabled:opacity-50 transition-colors"
                style={isAllDay ? SLOT_NEUTRAL_BG_ACTIVE : SLOT_NEUTRAL_BG}
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-bold text-ink inline-flex items-center gap-1.5">
                    <span className="material-icons text-sm">calendar_today</span>
                    All day
                  </span>
                  {isAllDay && (
                    <span className="text-[9px] font-bold rounded px-1 py-0.5 leading-none" style={CURRENT_BADGE_STYLE}>
                      current
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-ink-3 mt-0.5">{allDayNote}</div>
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleSlotChoice('am')}
                  disabled={submitting}
                  className="flex-1 px-3 py-2.5 rounded-xl border-2 text-left disabled:opacity-50 transition-colors"
                  style={hasAM && !isAllDay ? SLOT_AM_BG_ACTIVE : SLOT_AM_BG}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-bold text-accent inline-flex items-center gap-1.5">
                      <span className="material-icons text-sm">wb_sunny</span>
                      Morning
                    </span>
                    {hasAM && !isAllDay && (
                      <span
                        className="text-[9px] font-bold rounded px-1 py-0.5 leading-none"
                        style={{ background: 'var(--color-accent)', color: 'var(--color-bg)' }}
                      >
                        current
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] mt-0.5" style={{ color: 'rgba(31, 58, 138, 0.65)' }}>{amNote}</div>
                </button>
                <button
                  type="button"
                  onClick={() => handleSlotChoice('pm')}
                  disabled={submitting}
                  className="flex-1 px-3 py-2.5 rounded-xl border-2 text-left disabled:opacity-50 transition-colors"
                  style={hasPM && !isAllDay ? SLOT_PM_BG_ACTIVE : SLOT_PM_BG}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-bold inline-flex items-center gap-1.5" style={{ color: VIOLET }}>
                      <span className="material-icons text-sm">bedtime</span>
                      Afternoon
                    </span>
                    {hasPM && !isAllDay && (
                      <span
                        className="text-[9px] font-bold rounded px-1 py-0.5 leading-none"
                        style={{ background: VIOLET, color: 'var(--color-bg)' }}
                      >
                        current
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] mt-0.5" style={{ color: 'rgba(139, 92, 246, 0.7)' }}>{pmNote}</div>
                </button>
              </div>
            </div>
          </div>
          <div className="px-4 py-3 bg-surface-2 border-t border-hairline-2 flex justify-end">
            <button type="button" onClick={() => setPending(null)} disabled={submitting} className="btn btn-ghost disabled:opacity-50">
              ← Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Step 1: pick intent
  const title = slot === 'today' ? "Pick today's focus" : "Pick this week's focus";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className={backdropClass}
      style={backdropStyle}
      onClick={(e) => { if (e.target === e.currentTarget && !submitting) onClose(); }}
    >
      <div className={cardClass} onClick={(e) => e.stopPropagation()}>
        <div className="px-4 py-3 border-b border-hairline">
          <h2 className="title text-sm">{title}</h2>
        </div>
        <div className="px-4 py-3 flex flex-col gap-2 overflow-y-auto">
          {error && (
            <div className="bg-critical-bg text-critical px-2.5 py-1.5 rounded text-[11px] border border-critical/30">
              {error}
            </div>
          )}
          {projects.length === 0 ? (
            <div className="text-xs text-ink-3 px-1 py-2">No active projects.</div>
          ) : (
            <ul className="flex flex-col gap-1">
              {projects.map((p) => {
                const expanded = expandedSlug === p.slug;
                const intents = intentsBySlug[p.slug];
                const loading = loadingSlug === p.slug;
                return (
                  <li key={p.slug} className="border border-hairline rounded-lg overflow-hidden">
                    <button
                      type="button"
                      onClick={() => handleExpand(p.slug)}
                      disabled={submitting}
                      aria-expanded={expanded}
                      className="w-full px-3 py-2 text-left flex items-center justify-between gap-2 text-xs font-semibold text-ink hover:bg-surface-2 disabled:opacity-50"
                    >
                      <span className="truncate">{p.title}</span>
                      <span className="text-ink-4 text-[10px]">{expanded ? '▾' : '▸'}</span>
                    </button>
                    {expanded && (
                      <div className="border-t border-hairline bg-surface-2">
                        {loading ? (
                          <div className="px-3 py-2 text-[11px] text-ink-3">Loading…</div>
                        ) : intents && intents.length > 0 ? (
                          <ul>
                            {intents.map((intent) => (
                              <li key={intent.id}>
                                <button
                                  type="button"
                                  onClick={() => handleIntentClick(p, intent)}
                                  disabled={submitting}
                                  className="w-full px-3 py-1.5 text-left text-[11px] text-ink-2 hover:bg-surface disabled:opacity-50 flex items-center gap-2"
                                >
                                  <span className="text-ink-4">›</span>
                                  <span className="truncate">{intent.title}</span>
                                </button>
                              </li>
                            ))}
                          </ul>
                        ) : intents ? (
                          <div className="px-3 py-2 text-[11px] text-ink-3">No intents.</div>
                        ) : null}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
        <div className="px-4 py-3 bg-surface-2 border-t border-hairline-2 flex justify-end">
          <button type="button" onClick={onClose} disabled={submitting} className="btn btn-ghost disabled:opacity-50">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
