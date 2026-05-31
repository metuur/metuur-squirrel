import { Link, useOutletContext } from 'react-router-dom';
import { useState } from 'react';
import { useFetch } from '@/hooks/useFetch';
import { api, slashCommands, type ProjectListItem, type PressingItem, type ManualPick } from '@/api/client';
import { fromNow } from '@/lib/utils';
import { PromptPanel } from '@/components/PromptPanel';
import { RemindersWidget } from '@/components/RemindersWidget';

type Ctx = { viewMode: 'List' | 'Board' };

export default function HomePage() {
  const { viewMode } = useOutletContext<Ctx>();
  const { data, isLoading, mutate } = useFetch('home', () => api.home());

  if (isLoading && !data) {
    return (
      <div className="space-y-3">
        <div className="h-24 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
        <div className="h-48 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="max-w-6xl">
      <Header parakeet={data.parakeet} focus={data.focus} manualFocus={data.manual_focus} onRefresh={mutate} />
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

  const renderFocusCard = (pick: ManualPick | null, label: string, slot: string) => {
    if (!pick) return (
      <div className="bg-surface-light dark:bg-surface-dark border border-dashed border-border-light dark:border-border-dark rounded-2xl p-5">
        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">{label}</div>
        <p className="text-slate-400 text-sm">Not set</p>
      </div>
    );
    const isActive = activeSession?.slug === pick.intent_slug;
    const timeStr = formatTime(pick.time_invested_minutes);
    return (
      <div className={`bg-surface-light dark:bg-surface-dark border rounded-2xl shadow-sm p-5 ${isActive ? 'border-primary ring-1 ring-primary/20' : 'border-border-light dark:border-border-dark'}`}>
        <div className="flex items-center justify-between mb-2">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</div>
          {isActive && <span className="flex items-center gap-1 text-xs text-primary font-medium"><span className="w-2 h-2 rounded-full bg-primary animate-pulse inline-block" />Active</span>}
        </div>
        <Link to={`/projects/${pick.project_slug}`} className="text-lg font-bold text-slate-900 dark:text-slate-100 hover:text-primary block leading-tight">
          {pick.intent_title}
        </Link>
        {pick.next_action && <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{pick.next_action}</p>}
        {timeStr && <p className="text-xs text-slate-400 mt-2">⏱ {timeStr} invested</p>}
        <div className="mt-3">
          {isActive ? (
            <button onClick={handleCheckout} disabled={checkingOut}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-all">
              <span className="material-icons text-base">stop</span>
              Check out
            </button>
          ) : (
            <button onClick={() => handleCheckin(pick, slot)} disabled={checkingIn || !!activeSession}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold border-2 border-primary text-primary rounded-lg hover:bg-primary hover:text-white disabled:opacity-50 transition-all">
              <span className="material-icons text-base">play_arrow</span>
              Check in
            </button>
          )}
        </div>
      </div>
    );
  };

  const hasPm = manualFocus?.today_pm != null;
  const hasToday = manualFocus?.today != null;

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100">Today</h1>
        <button onClick={onRefresh} className="text-xs font-semibold text-slate-400 hover:text-primary flex items-center gap-1">
          <span className="material-icons text-sm">refresh</span>
          Refresh
        </button>
      </div>
      {(hasToday || hasPm) ? (
        <div className={`grid gap-4 ${hasPm ? 'grid-cols-2' : 'grid-cols-1'}`}>
          {renderFocusCard(manualFocus!.today, 'AM focus', 'today')}
          {hasPm && renderFocusCard(manualFocus!.today_pm, 'PM focus', 'today_pm')}
        </div>
      ) : (
        <div className="bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm p-5">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Today's focus</div>
          {focus ? (
            <>
              <Link to={`/projects/${focus.slug}`} className="text-2xl font-bold text-slate-900 dark:text-slate-100 hover:text-primary block leading-tight">{focus.title}</Link>
              {focus.next_action && <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">{focus.next_action}</p>}
            </>
          ) : (
            <>
              <p className="text-slate-500 dark:text-slate-400">{parakeet || 'Nothing pressing right now.'}</p>
              <div className="mt-3">
                <button onClick={() => setShowStartPanel(true)} className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-semibold border-2 border-primary text-primary rounded-lg hover:bg-primary hover:text-white transition-all">
                  <span className="material-icons text-base">terminal</span>
                  Help me start
                </button>
                <PromptPanel open={showStartPanel} title="Start a session" command={slashCommands.start()} helpText="Run this in your AI agent — it picks the next concrete action for you from the active project." onClose={() => setShowStartPanel(false)} />
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Board view ─────────────────────────────────────────────────────────────
function BoardView({ projects, pressing }: { projects: ProjectListItem[]; pressing: PressingItem[] }) {
  // Group projects by deadline proximity
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
    { key: 'pressing', label: 'PRESSING', accent: 'border-red-300 dark:border-red-700/50', count: cols.pressing.length },
    { key: 'thisWeek', label: 'THIS WEEK', accent: 'border-orange-300 dark:border-orange-700/50', count: cols.thisWeek.length },
    { key: 'active', label: 'ACTIVE', accent: 'border-blue-300 dark:border-blue-700/50', count: cols.active.length },
    { key: 'later', label: 'LATER', accent: 'border-slate-200 dark:border-slate-700', count: cols.later.length },
    { key: 'done', label: 'DELIVERED', accent: 'border-emerald-300 dark:border-emerald-700/50', count: cols.done.length },
  ] as const;

  return (
    <div className="flex h-full overflow-x-auto gap-6 pb-6 select-none">
      {columns.map((col) => (
        <div key={col.key} className="flex-shrink-0 w-72 flex flex-col">
          <div className={`flex items-center justify-between mb-4 border-b-2 ${col.accent} pb-2 px-1`}>
            <h3 className="text-xs font-bold text-slate-700 dark:text-slate-300 tracking-wider">{col.label}</h3>
            <span className="flex items-center justify-center min-w-5 h-5 px-1.5 bg-slate-300 dark:bg-slate-700 text-slate-600 dark:text-slate-400 text-[10px] font-bold rounded-full">
              {col.count}
            </span>
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
              <div className="h-24 border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-lg flex items-center justify-center">
                <span className="text-[10px] text-slate-400 uppercase font-bold tracking-widest">Empty</span>
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
      className="block bg-white dark:bg-slate-800 p-4 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-all group"
    >
      <div className="text-[10px] font-mono text-slate-400 mb-1">{item.id}</div>
      <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 leading-tight mb-2 group-hover:text-primary">
        {item.title}
      </h4>
      <div className="flex items-center gap-1.5 text-red-500 font-medium text-[11px]">
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
      className="block bg-white dark:bg-slate-800 p-4 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-all group"
    >
      <div className="text-[10px] font-mono text-slate-400 mb-1">{p.slug}</div>
      <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 leading-tight mb-3 group-hover:text-primary">
        {p.title}
      </h4>
      <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
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
        <div className="mt-2 text-[10px] text-slate-400">Last activity {fromNow(p.last_activity as any)}</div>
      )}
    </Link>
  );
}

// ─── List view ──────────────────────────────────────────────────────────────
function ListView({ projects, pressing }: { projects: ProjectListItem[]; pressing: PressingItem[] }) {
  return (
    <div className="space-y-6">
      {pressing.length > 0 && (
        <section>
          <h2 className="text-xs font-bold tracking-wider text-slate-500 dark:text-slate-400 uppercase mb-3">
            Pressing
          </h2>
          <div className="space-y-2">
            {pressing.map((it) => (
              <Link
                key={it.id}
                to={`/notes/${it.id}`}
                className="block bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm hover:shadow-md transition-all p-4 group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-[10px] font-mono text-slate-400 mb-0.5">{it.id}</div>
                    <h3 className="font-semibold text-slate-900 dark:text-slate-100 group-hover:text-primary">{it.title}</h3>
                    {it.deadline && (
                      <div className="text-xs text-slate-500 mt-1">Due {it.deadline}</div>
                    )}
                  </div>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 whitespace-nowrap">
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
        <h2 className="text-xs font-bold tracking-wider text-slate-500 dark:text-slate-400 uppercase mb-3">
          My projects
        </h2>
        {projects.length === 0 ? (
          <div className="text-center py-12 bg-surface-light dark:bg-surface-dark border border-dashed border-border-light dark:border-border-dark rounded-lg">
            <span className="material-icons text-slate-300 text-4xl mb-2">folder_open</span>
            <p className="text-slate-500">No projects yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {projects.map((p) => (
              <Link
                key={p.slug}
                to={`/projects/${p.slug}`}
                className="block bg-surface-light dark:bg-surface-dark border border-border-light dark:border-border-dark rounded-2xl shadow-sm hover:shadow-md transition-all p-5 group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-[10px] font-mono text-slate-400 mb-1">{p.slug}</div>
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-2 group-hover:text-primary">
                      {p.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
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
                  <span className="material-icons text-slate-300 dark:text-slate-600 group-hover:text-primary mt-1">arrow_forward</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
