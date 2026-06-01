import { Link, useOutletContext } from 'react-router-dom';
import { useEffect, useState, type MouseEvent } from 'react';
import { useFetch } from '@/hooks/useFetch';
import { api, slashCommands, type ProjectListItem, type PressingItem, type ManualPick, type EntityKind } from '@/api/client';
import { fromNow } from '@/lib/utils';
import { PromptPanel } from '@/components/PromptPanel';
import { RemindersWidget } from '@/components/RemindersWidget';
import { FocusPickerModal } from '@/components/FocusPickerModal';

type Ctx = { viewMode: 'List' | 'Board' };

const FOCUS_POLL_MS = 5000;

const KIND_META: Record<EntityKind, { icon: string; label: string }> = {
  'project':      { icon: 'folder',        label: 'Project' },
  'project-task': { icon: 'task_alt',      label: 'Task'    },
  'note':         { icon: 'sticky_note_2', label: 'Note'    },
};

function KindBadge({ kind }: { kind: EntityKind }) {
  const meta = KIND_META[kind];
  return (
    <span className="chip chip-count" title={meta.label}>
      <span className="material-icons" style={{ fontSize: 12 }}>{meta.icon}</span>
      {meta.label}
    </span>
  );
}

function RevealButton({ id }: { id: string }) {
  const onClick = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    api.reveal(id).catch(() => { /* best-effort: the OS will surface its own error */ });
  };
  return (
    <button
      type="button"
      onClick={onClick}
      title="Reveal in Finder"
      aria-label="Reveal in Finder"
      className="text-ink-4 hover:text-accent shrink-0"
    >
      <span className="material-icons" style={{ fontSize: 14 }}>folder_open</span>
    </button>
  );
}

/** Map a deadline date string ('YYYY-MM-DD') to a board urgency bucket so
 *  ProjectCard can render the same red alarm chip as PressingCard when the
 *  project itself is overdue or imminently due. */
function classifyDeadline(deadline: string | null | undefined): 'overdue' | 'critical' | 'urgent' | null {
  if (!deadline) return null;
  const dl = new Date(deadline);
  if (Number.isNaN(dl.getTime())) return null;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diffDays = Math.floor((dl.getTime() - today.getTime()) / 86400000);
  if (diffDays < 0) return 'overdue';
  if (diffDays === 0) return 'critical';
  if (diffDays <= 1) return 'urgent';
  return null;
}

export default function HomePage() {
  const { viewMode } = useOutletContext<Ctx>();
  const { data, isLoading, mutate } = useFetch('home', () => api.home());

  // Poll /api/home so focus stays in sync with the Tauri app (and external
  // edits to the vault). Pauses while the tab is hidden.
  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === 'visible') mutate();
    };
    const id = window.setInterval(tick, FOCUS_POLL_MS);
    const onVisible = () => { if (document.visibilityState === 'visible') mutate(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [mutate]);

  if (isLoading && !data) {
    return (
      <div className="space-y-3">
        <div className="h-24 animate-pulse rounded-lg bg-surface-2" />
        <div className="h-48 animate-pulse rounded-lg bg-surface-2" />
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="max-w-6xl">
      <Header parakeet={data.parakeet} focus={data.focus} manualFocus={data.manual_focus} projects={data.projects} onRefresh={mutate} />
      <RemindersWidget />
      {viewMode === 'Board' ? (
        <BoardView projects={data.projects} pressing={data.pressing} />
      ) : (
        <ListView projects={data.projects} pressing={data.pressing} />
      )}
    </div>
  );
}

function Header({ parakeet, focus, manualFocus, projects, onRefresh }: {
  parakeet: string;
  focus: { slug: string; title: string; next_action: string } | null;
  manualFocus?: { today: ManualPick | null; today_pm: ManualPick | null; week: ManualPick | null } | null;
  projects: ProjectListItem[];
  onRefresh: () => void;
}) {
  const [showStartPanel, setShowStartPanel] = useState(false);
  const [pickerSlot, setPickerSlot] = useState<'today' | 'week' | null>(null);
  const [activeSession, setActiveSession] = useState<{ sessionId: number; slug: string } | null>(null);
  const [checkingIn, setCheckingIn] = useState(false);
  const [checkingOut, setCheckingOut] = useState(false);

  const handleCheckin = async (pick: ManualPick, slot: string) => {
    setCheckingIn(true);
    try {
      const res = await api.checkin({ project_slug: pick.project_slug, intent_slug: pick.intent_slug, slot });
      setActiveSession({ sessionId: res.session_id, slug: pick.intent_slug });
      onRefresh();
    } catch { /* ignore */ } finally { setCheckingIn(false); }
  };

  const handleCheckout = async () => {
    setCheckingOut(true);
    try {
      await api.checkout();
      setActiveSession(null);
      onRefresh();
    } catch { /* ignore */ } finally { setCheckingOut(false); }
  };

  const formatTime = (minutes: number) => {
    if (!minutes) return null;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  };

  const renderFocusRow = (pick: ManualPick, badge: string, chipClass: string, slot: string, separator: boolean) => {
    const isActive = activeSession?.slug === pick.intent_slug;
    const timeStr = formatTime(pick.time_invested_minutes);
    const slugText = pick.next_action ? `${pick.project_slug} · ${pick.intent_slug}` : pick.project_slug;
    const titleText = pick.next_action || pick.intent_title;
    return (
      <div key={slot} className={`flex items-start gap-2.5 ${separator ? 'mt-2 pt-2 border-t border-hairline-2' : ''}`}>
        <span className={`chip ${chipClass} shrink-0 mt-0.5`}>{badge}</span>
        <div className="min-w-0 flex-1">
          <p className="slug truncate">{slugText}</p>
          <Link to={`/projects/${pick.project_slug}`} className="title text-[13.5px] leading-snug hover:text-accent block truncate">
            {titleText}
          </Link>
          {(timeStr || isActive) && (
            <div className="mt-0.5 flex items-center gap-2 text-[10.5px]">
              {timeStr && <span className="text-ink-4 tabular">⏱ {timeStr}</span>}
              {isActive && <span className="flex items-center gap-1 text-accent font-medium"><span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse inline-block" />Active</span>}
            </div>
          )}
        </div>
        {isActive ? (
          <button
            onClick={handleCheckout}
            disabled={checkingOut}
            title="Check out"
            aria-label="Check out"
            className="btn-tactile is-critical shrink-0"
          >
            <span className="material-icons text-[15px]">stop</span>
            Check out
          </button>
        ) : (
          <button
            onClick={() => handleCheckin(pick, slot)}
            disabled={checkingIn || !!activeSession}
            title="Check in"
            aria-label="Check in"
            className="btn-tactile shrink-0"
          >
            <span className="material-icons text-[15px]">play_arrow</span>
            Check in
          </button>
        )}
      </div>
    );
  };

  const renderActions = (slot: 'today' | 'week') => (
    <span className="text-[10.5px] font-semibold inline-flex items-center gap-1.5">
      <button type="button" onClick={() => setPickerSlot(slot)} className="text-ink-3 hover:text-ink hover:underline underline-offset-2">Change</button>
      <span className="text-ink-4">·</span>
      <button type="button" onClick={() => handleClearFocus(slot)} className="text-critical hover:underline underline-offset-2">Clear</button>
    </span>
  );

  const handleClearFocus = async (slot: 'today' | 'week') => {
    try {
      if (slot === 'today') {
        await Promise.all([
          api.focusSet('today', { clear: true }),
          api.focusSet('today_pm', { clear: true }),
        ]);
      } else {
        await api.focusSet(slot, { clear: true });
      }
      onRefresh();
    } catch {
      /* best-effort */
    }
  };

  const amPick = manualFocus?.today ?? null;
  const pmPick = manualFocus?.today_pm ?? null;
  const weekPick = manualFocus?.week ?? null;
  const isAllDay = !!(amPick && pmPick && amPick.intent_slug === pmPick.intent_slug);
  const hasTodayFocus = !!(amPick || pmPick);

  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-2">
        <h1 className="title">What matters now:</h1>
        <button onClick={onRefresh} className="text-xs font-semibold text-ink-4 hover:text-accent flex items-center gap-1">
          <span className="material-icons text-sm">refresh</span>
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* ── Today's focus ─────────────────────────────────────────── */}
        <div className="card-focus p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="eyebrow">Today's focus</span>
            {hasTodayFocus && renderActions('today')}
          </div>
          {hasTodayFocus ? (
            <>
              {isAllDay
                ? renderFocusRow(amPick!, 'Today', 'chip-am', 'today', false)
                : (
                  <>
                    {amPick && renderFocusRow(amPick, 'AM', 'chip-am', 'today', false)}
                    {pmPick && renderFocusRow(pmPick, 'PM', 'chip-pm', 'today_pm', !!amPick)}
                  </>
                )}
              {amPick && !pmPick && (
                <button
                  type="button"
                  onClick={() => setPickerSlot('today')}
                  className="mt-2 inline-flex items-center gap-1.5 text-[11px] font-semibold text-ink-3 hover:text-ink"
                >
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#8B5CF6' }} />
                  Add afternoon focus
                </button>
              )}
            </>
          ) : focus ? (
            <div className="flex items-start gap-2.5">
              <span className="chip chip-am shrink-0 mt-0.5">Auto</span>
              <div className="min-w-0 flex-1">
                <p className="slug truncate">{focus.slug}</p>
                <Link to={`/projects/${focus.slug}`} className="title text-[13.5px] leading-snug hover:text-accent block truncate">{focus.title}</Link>
                {focus.next_action && <p className="text-[10.5px] text-ink-3 mt-0.5 italic truncate">"{focus.next_action}"</p>}
              </div>
              <button type="button" onClick={() => setPickerSlot('today')} className="shrink-0 text-[10.5px] font-semibold text-ink-3 hover:text-ink hover:underline underline-offset-2">Pin</button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setPickerSlot('today')}
              className="w-full flex items-center gap-2.5 text-left text-ink-3 hover:text-ink"
            >
              <span className="w-2 h-2 rounded-full bg-accent" />
              <span className="text-[12.5px] font-semibold">Pick today's focus</span>
              <span className="text-[10.5px] text-ink-4 truncate">— {parakeet || 'nothing pressing'}</span>
            </button>
          )}
        </div>

        {/* ── This week ─────────────────────────────────────────────── */}
        <div className="card-focus p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="eyebrow">This week</span>
            {weekPick && renderActions('week')}
          </div>
          {weekPick ? (
            renderFocusRow(weekPick, 'Week', 'chip-week', 'week', false)
          ) : (
            <button
              type="button"
              onClick={() => setPickerSlot('week')}
              className="w-full flex items-center gap-2.5 text-left text-ink-3 hover:text-ink"
            >
              <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-ok)' }} />
              <span className="text-[12.5px] font-semibold">Pick this week's focus</span>
            </button>
          )}
        </div>
      </div>

      <PromptPanel open={showStartPanel} title="Start a session" command={slashCommands.start()} helpText="Run this in your AI agent — it picks the next concrete action for you from the active project." onClose={() => setShowStartPanel(false)} />

      {pickerSlot && (
        <FocusPickerModal
          slot={pickerSlot}
          projects={projects}
          currentAmPick={amPick}
          currentPmPick={pmPick}
          onClose={() => setPickerSlot(null)}
          onPicked={() => { setPickerSlot(null); onRefresh(); }}
        />
      )}
    </div>
  );
}

function BoardView({ projects, pressing }: { projects: ProjectListItem[]; pressing: PressingItem[] }) {
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const cols = {
    pressing: [] as Array<{ kind: 'pressing'; item: PressingItem }>,
    thisWeek: [] as ProjectListItem[],
    active: [] as ProjectListItem[],
    later: [] as ProjectListItem[],
    done: [] as ProjectListItem[],
  };
  pressing.forEach((p) => cols.pressing.push({ kind: 'pressing', item: p }));
  for (const p of projects) {
    const pct = p.percent_done ?? 0;
    if (pct >= 100) { cols.done.push(p); continue; }
    if (p.deadline) {
      const dl = new Date(p.deadline);
      const diffDays = (dl.getTime() - today.getTime()) / 86400000;
      if (diffDays <= 7) { cols.thisWeek.push(p); continue; }
      if (diffDays <= 30) { cols.active.push(p); continue; }
      cols.later.push(p); continue;
    }
    cols.active.push(p);
  }

  const columns = [
    { key: 'pressing', label: 'PRESSING', accent: 'border-critical', count: cols.pressing.length },
    { key: 'thisWeek', label: 'THIS WEEK', accent: 'border-warning', count: cols.thisWeek.length },
    { key: 'active', label: 'ACTIVE', accent: 'border-accent', count: cols.active.length },
    { key: 'later', label: 'LATER', accent: 'border-hairline', count: cols.later.length },
    { key: 'done', label: 'DELIVERED', accent: 'border-ok', count: cols.done.length },
  ] as const;

  return (
    <div className="flex h-full overflow-x-auto gap-6 pb-6 select-none">
      {columns.map((col) => (
        <div key={col.key} className="flex-shrink-0 w-72 flex flex-col">
          <div className={`flex items-center justify-between mb-4 border-b-2 ${col.accent} pb-2 px-1`}>
            <h3 className="eyebrow text-ink-2">{col.label}</h3>
            <span className="chip chip-count">{col.count}</span>
          </div>
          <div className="flex-1 space-y-3 min-h-[200px] px-1">
            {col.key === 'pressing' && cols.pressing.map(({ item }) => (
              <PressingCard key={item.id} item={item} />
            ))}
            {col.key === 'thisWeek' && cols.thisWeek.map((p) => <ProjectCard key={p.slug} p={p} />)}
            {col.key === 'active' && cols.active.map((p) => <ProjectCard key={p.slug} p={p} />)}
            {col.key === 'later' && cols.later.map((p) => <ProjectCard key={p.slug} p={p} />)}
            {col.key === 'done' && cols.done.map((p) => <ProjectCard key={p.slug} p={p} />)}
            {col.count === 0 && (
              <div className="h-24 border-2 border-dashed border-hairline rounded-lg flex items-center justify-center">
                <span className="text-[10px] text-ink-4 uppercase font-bold tracking-widest">Empty</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function PressingCard({ item }: { item: PressingItem }) {
  const linkTarget = item.kind === 'project' && item.slug
    ? `/projects/${item.slug}`
    : `/notes/${item.id}`;
  const revealId = item.kind === 'project' && item.slug ? item.slug : item.id;
  return (
    <Link
      to={linkTarget}
      className="block panel p-4 hover:shadow-md transition-all group"
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="text-[10px] font-mono text-ink-4 truncate">{item.id}</div>
        <div className="flex items-center gap-1.5 shrink-0">
          <KindBadge kind={item.kind} />
          <RevealButton id={revealId} />
        </div>
      </div>
      <h4 className="text-sm font-bold text-ink leading-tight mb-2 group-hover:text-accent">
        {item.title}
      </h4>
      <div className="flex items-center gap-1.5 text-critical font-medium text-[11px]">
        <span className="material-icons text-sm">alarm</span>
        {item.is_overdue
          ? `${item.days_overdue ?? 0}d overdue`
          : item.hours_left != null
          ? `${Math.round(item.hours_left)}h left`
          : item.urgency_label}
      </div>
    </Link>
  );
}

function ProjectCard({ p }: { p: ProjectListItem }) {
  const pct = p.percent_done ?? 0;
  const urgency = classifyDeadline(p.deadline);
  return (
    <Link
      to={`/projects/${p.slug}`}
      className="block panel p-4 hover:shadow-md transition-all group"
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <div className="text-[10px] font-mono text-ink-4 truncate">{p.slug}</div>
        <div className="flex items-center gap-1.5 shrink-0">
          <KindBadge kind="project" />
          <RevealButton id={p.slug} />
        </div>
      </div>
      <h4 className="text-sm font-bold text-ink leading-tight mb-3 group-hover:text-accent">
        {p.title}
      </h4>
      <div className="flex items-center justify-between text-[11px] text-ink-3">
        <span className="inline-flex items-center gap-1">
          <span className="material-icons text-sm">trending_up</span>
          {pct}%
        </span>
        {p.deadline && (
          urgency
            ? (
              <span className="inline-flex items-center gap-1 text-critical font-medium">
                <span className="material-icons text-sm">alarm</span>
                {urgency === 'overdue'
                  ? `${Math.abs(Math.floor((new Date(p.deadline).getTime() - new Date().setHours(0,0,0,0)) / 86400000))}d overdue`
                  : p.deadline}
              </span>
            )
            : (
              <span className="inline-flex items-center gap-1">
                <span className="material-icons text-sm">event</span>
                {p.deadline}
              </span>
            )
        )}
      </div>
      {p.last_activity && (
        <div className="mt-2 text-[10px] text-ink-4">Last activity {fromNow(p.last_activity as any)}</div>
      )}
    </Link>
  );
}

function ListView({ projects, pressing }: { projects: ProjectListItem[]; pressing: PressingItem[] }) {
  return (
    <div className="space-y-6">
      {pressing.length > 0 && (
        <section>
          <h2 className="eyebrow mb-3">Pressing</h2>
          <div className="space-y-2">
            {pressing.map((it) => {
              const linkTarget = it.kind === 'project' && it.slug
                ? `/projects/${it.slug}`
                : `/notes/${it.id}`;
              const revealId = it.kind === 'project' && it.slug ? it.slug : it.id;
              return (
                <Link
                  key={it.id}
                  to={linkTarget}
                  className="block panel p-4 group hover:shadow-md transition-all stripe stripe-critical"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <div className="text-[10px] font-mono text-ink-4 truncate">{it.id}</div>
                        <KindBadge kind={it.kind} />
                      </div>
                      <h3 className="font-semibold text-ink group-hover:text-accent">{it.title}</h3>
                      {it.deadline && (
                        <div className="text-xs text-ink-3 mt-1">Due {it.deadline}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="chip chip-critical whitespace-nowrap">
                        <span className="material-icons text-sm">alarm</span>
                        {it.urgency_label}
                      </span>
                      <RevealButton id={revealId} />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}
      <section>
        <h2 className="eyebrow mb-3">My projects</h2>
        {projects.length === 0 ? (
          <div className="text-center py-12 panel border-dashed">
            <span className="material-icons text-ink-4 text-4xl mb-2">folder_open</span>
            <p className="text-ink-3">No projects yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((p) => {
              const urgency = classifyDeadline(p.deadline);
              return (
                <Link
                  key={p.slug}
                  to={`/projects/${p.slug}`}
                  className="block panel p-5 group hover:shadow-md transition-all"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="text-[10px] font-mono text-ink-4 truncate">{p.slug}</div>
                        <KindBadge kind="project" />
                      </div>
                      <h3 className="text-lg font-semibold text-ink mb-2 group-hover:text-accent">
                        {p.title}
                      </h3>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-ink-3">
                        <span className="inline-flex items-center gap-1">
                          <span className="material-icons text-sm">trending_up</span>
                          {p.percent_done ?? 0}%
                        </span>
                        {p.deadline && (
                          urgency
                            ? (
                              <span className="inline-flex items-center gap-1 text-critical font-medium">
                                <span className="material-icons text-sm">alarm</span>
                                Deadline: {p.deadline}
                              </span>
                            )
                            : (
                              <span className="inline-flex items-center gap-1">
                                <span className="material-icons text-sm">event</span>
                                Deadline: {p.deadline}
                              </span>
                            )
                        )}
                        {p.last_activity && (
                          <span className="inline-flex items-center gap-1">
                            <span className="material-icons text-sm">history</span>
                            {fromNow(p.last_activity as any)}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 mt-1 shrink-0">
                      <RevealButton id={p.slug} />
                      <span className="material-icons text-ink-4 group-hover:text-accent">arrow_forward</span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
