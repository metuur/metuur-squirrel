import { Link, useOutletContext } from 'react-router-dom';
import { useState } from 'react';
import { useFetch } from '@/hooks/useFetch';
import { api, slashCommands, type ProjectListItem, type PressingItem, type ManualPick } from '@/api/client';
import { fromNow } from '@/lib/utils';
import { PromptPanel } from '@/components/PromptPanel';
import { RemindersWidget } from '@/components/RemindersWidget';
import { FocusPickerModal } from '@/components/FocusPickerModal';

type Ctx = { viewMode: 'List' | 'Board' };

export default function HomePage() {
  const { viewMode } = useOutletContext<Ctx>();
  const { data, isLoading, mutate } = useFetch('home', () => api.home());

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

function Header({ parakeet, focus, manualFocus, onRefresh }: {
  parakeet: string;
  focus: { slug: string; title: string; next_action: string } | null;
  manualFocus?: { today: ManualPick | null; today_pm: ManualPick | null; week: ManualPick | null } | null;
  onRefresh: () => void;
}) {
  const [showStartPanel, setShowStartPanel] = useState(false);
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
    const slugText = pick.next_action
      ? `${pick.project_slug} · ${pick.intent_slug}`
      : pick.project_slug;
    const titleText = pick.next_action || pick.intent_title;
    return (
      <div key={slot} className={`flex items-start gap-3 ${separator ? 'mt-3 pt-3 border-t border-hairline-2' : ''}`}>
        <span className={`chip ${chipClass} shrink-0 mt-0.5`}>{badge}</span>
        <div className="min-w-0 flex-1">
          <p className="slug truncate mb-1">{slugText}</p>
          <Link to={`/projects/${pick.project_slug}`} className="title text-[15px] leading-snug hover:text-accent block">
            {titleText}
          </Link>
          {pick.next_action && (
            <p className="text-xs text-ink-3 mt-1 italic">"{pick.intent_title}"</p>
          )}
          <div className="mt-2 flex items-center gap-3">
            {isActive ? (
              <button onClick={handleCheckout} disabled={checkingOut} className="btn btn-primary text-xs px-2.5 py-1 disabled:opacity-50">
                <span className="material-icons text-sm">stop</span>
                Check out
              </button>
            ) : (
              <button onClick={() => handleCheckin(pick, slot)} disabled={checkingIn || !!activeSession} className="btn btn-primary text-xs px-2.5 py-1 disabled:opacity-50">
                <span className="material-icons text-sm">play_arrow</span>
                Check in
              </button>
            )}
            {timeStr && <span className="text-[11px] text-ink-4 tabular">⏱ {timeStr} invested</span>}
            {isActive && <span className="flex items-center gap-1 text-[11px] text-accent font-medium"><span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse inline-block" />Active</span>}
          </div>
        </div>
      </div>
    );
  };

  const amPick = manualFocus?.today ?? null;
  const pmPick = manualFocus?.today_pm ?? null;
  const weekPick = manualFocus?.week ?? null;
  const isAllDay = !!(amPick && pmPick && amPick.intent_slug === pmPick.intent_slug);
  const hasTodayFocus = !!(amPick || pmPick);

  return (
    <div className="mb-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="title">Today</h1>
        <button onClick={onRefresh} className="text-xs font-semibold text-ink-4 hover:text-accent flex items-center gap-1">
          <span className="material-icons text-sm">refresh</span>
          Refresh
        </button>
      </div>

      {hasTodayFocus ? (
        <div className="card-focus p-4">
          <div className="eyebrow mb-3">Today's focus</div>
          {isAllDay ? (
            renderFocusRow(amPick!, 'Today', 'chip-am', 'today', false)
          ) : (
            <>
              {amPick && renderFocusRow(amPick, 'AM', 'chip-am', 'today', false)}
              {pmPick && renderFocusRow(pmPick, 'PM', 'chip-pm', 'today_pm', !!amPick)}
            </>
          )}
        </div>
      ) : (
        <div className="card-focus p-4">
          <div className="eyebrow mb-3">Today's focus</div>
          {focus ? (
            <>
              <p className="slug mb-1">{focus.slug}</p>
              <Link to={`/projects/${focus.slug}`} className="title text-[15px] leading-snug hover:text-accent block">{focus.title}</Link>
              {focus.next_action && <p className="text-xs text-ink-3 mt-2 italic">"{focus.next_action}"</p>}
            </>
          ) : (
            <>
              <p className="text-sm text-ink-3">{parakeet || 'Nothing pressing right now.'}</p>
              <div className="mt-3">
                <button onClick={() => setShowStartPanel(true)} className="btn btn-primary text-xs px-2.5 py-1">
                  <span className="material-icons text-sm">terminal</span>
                  Help me start
                </button>
                <PromptPanel open={showStartPanel} title="Start a session" command={slashCommands.start()} helpText="Run this in your AI agent — it picks the next concrete action for you from the active project." onClose={() => setShowStartPanel(false)} />
              </div>
            </>
          )}
        </div>
      )}

      {weekPick && (
        <div className="card-focus p-4">
          <div className="eyebrow mb-3">This week</div>
          {renderFocusRow(weekPick, 'Week', 'chip-week', 'week', false)}
        </div>
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
  return (
    <Link
      to={`/notes/${item.id}`}
      className="block panel p-4 hover:shadow-md transition-all group"
    >
      <div className="text-[10px] font-mono text-ink-4 mb-1">{item.id}</div>
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
  return (
    <Link
      to={`/projects/${p.slug}`}
      className="block panel p-4 hover:shadow-md transition-all group"
    >
      <div className="text-[10px] font-mono text-ink-4 mb-1">{p.slug}</div>
      <h4 className="text-sm font-bold text-ink leading-tight mb-3 group-hover:text-accent">
        {p.title}
      </h4>
      <div className="flex items-center justify-between text-[11px] text-ink-3">
        <span className="inline-flex items-center gap-1">
          <span className="material-icons text-sm">trending_up</span>
          {pct}%
        </span>
        {p.deadline && (
          <span className="inline-flex items-center gap-1">
            <span className="material-icons text-sm">event</span>
            {p.deadline}
          </span>
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
            {pressing.map((it) => (
              <Link
                key={it.id}
                to={`/notes/${it.id}`}
                className="block panel p-4 group hover:shadow-md transition-all stripe stripe-critical"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[10px] font-mono text-ink-4 mb-0.5">{it.id}</div>
                    <h3 className="font-semibold text-ink group-hover:text-accent">{it.title}</h3>
                    {it.deadline && (
                      <div className="text-xs text-ink-3 mt-1">Due {it.deadline}</div>
                    )}
                  </div>
                  <span className="chip chip-critical whitespace-nowrap">
                    <span className="material-icons text-sm">alarm</span>
                    {it.urgency_label}
                  </span>
                </div>
              </Link>
            ))}
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
            {projects.map((p) => (
              <Link
                key={p.slug}
                to={`/projects/${p.slug}`}
                className="block panel p-5 group hover:shadow-md transition-all"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] font-mono text-ink-4 mb-1">{p.slug}</div>
                    <h3 className="text-lg font-semibold text-ink mb-2 group-hover:text-accent">
                      {p.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-ink-3">
                      <span className="inline-flex items-center gap-1">
                        <span className="material-icons text-sm">trending_up</span>
                        {p.percent_done ?? 0}%
                      </span>
                      {p.deadline && (
                        <span className="inline-flex items-center gap-1">
                          <span className="material-icons text-sm">event</span>
                          Deadline: {p.deadline}
                        </span>
                      )}
                      {p.last_activity && (
                        <span className="inline-flex items-center gap-1">
                          <span className="material-icons text-sm">history</span>
                          {fromNow(p.last_activity as any)}
                        </span>
                      )}
                    </div>
                  </div>
                  <span className="material-icons text-ink-4 group-hover:text-accent mt-1">arrow_forward</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
