// Squirrel JSON API client — all calls hit /api/* on the Python server.
// In dev (vite), /api/* is proxied to http://127.0.0.1:3939 (vite.config.ts).
// In prod (squirrel web start), the SPA is served BY the Python server, so
// /api/* is same-origin.

const BASE = '/api';

export class ApiError extends Error {
  status: number;
  payload: any;
  constructor(status: number, message: string, payload?: any) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  window.dispatchEvent(new CustomEvent('squirrel:api-start', { detail: { id, path } }));
  try {
    const resp = await fetch(BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
    const text = await resp.text();
    let data: any = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      /* not JSON */
    }
    if (!resp.ok) {
      const msg = (data && (data.error || data.message)) || `Request failed (${resp.status})`;
      throw new ApiError(resp.status, msg, data);
    }
    return data as T;
  } finally {
    window.dispatchEvent(new CustomEvent('squirrel:api-end', { detail: { id, path } }));
  }
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface Workspace {
  name: string;
  path: string;
  default: boolean;
}
export interface Me {
  active_workspace: Workspace;
  workspaces: Workspace[];
  multi_vault: boolean;
  theme: 'auto' | 'light' | 'dark';
  version: string;
  notifications?: { in_app: boolean; os_popups: boolean; sound: 'Glass' | 'Funk' | 'Silent' };
}
export interface FocusItem {
  slug: string;
  title: string;
  next_action: string;
  reason: string;
}
export type EntityKind = 'project' | 'project-task' | 'note';
export interface PressingItem {
  id: string;
  title: string;
  deadline: string;
  urgency: string;
  urgency_label: string;
  is_overdue: boolean;
  hours_left: number | null;
  days_overdue: number | null;
  kind: EntityKind;
  /** Present only when `kind === 'project'` — the project's folder/slug,
   *  so the UI can route to `/projects/{slug}` instead of `/notes/{id}`. */
  slug?: string;
}
export interface ProjectListItem {
  slug: string;
  title: string;
  percent_done?: number;
  deadline?: string | null;
  active_intent?: string | null;
  last_activity?: string | null;
  kind: 'project';
}
export interface ManualPick {
  project_slug: string;
  project_title: string;
  intent_slug: string;
  intent_title: string;
  next_action: string | null;
  picked_on: string;
  time_invested_minutes: number;
}
export interface ManualFocusPayload {
  today: ManualPick | null;
  today_pm: ManualPick | null;
  week: ManualPick | null;
}
export interface CheckinResult {
  session_id: number;
}
export interface CheckoutResult {
  session_id: number;
  duration_minutes: number;
  time_invested_minutes: number;
}
export interface FocusPick {
  id: number;
  vault: string;
  slot: string;
  date: string;
  project_slug: string;
  intent_slug: string;
  picked_at: string;
  cleared_at: string | null;
}
export interface WorkSession {
  id: number;
  vault: string;
  slot: string;
  date: string;
  project_slug: string;
  intent_slug: string;
  checkin_at: string;
  checkout_at: string | null;
  duration_minutes: number | null;
}
export interface FocusHistoryPayload {
  picks: FocusPick[];
  sessions: WorkSession[];
}
export interface HomePayload {
  focus: FocusItem | null;
  pressing: PressingItem[];
  projects: ProjectListItem[];
  parakeet: string;
  manual_focus?: ManualFocusPayload;
}
export interface NoteSummary {
  id: string;
  title: string;
  modified_at: number;
}
export interface ProjectDetail {
  slug: string;
  title: string;
  body: string;
  raw_body: string;
  mtime: number;
  notes: NoteSummary[];
}
export interface NoteDetail {
  id: string;
  title: string;
  body: string;
  raw_body: string;
  mtime: number;
  project_slug: string;
}
export interface DeadlineGroup {
  label: string;
  items: Array<{
    id: string;
    title: string;
    deadline: string;
    is_overdue: boolean;
    hours_left: number | null;
    days_overdue: number | null;
  }>;
}
export interface HistoryItem {
  kind: 'project' | 'note';
  slug: string | null;
  note_id: string | null;
  title: string;
  modified_at: number;
}
export interface SearchHit {
  id: string;
  title: string;
  snippet_lines: string[];
  project_slug: string;
}
export interface SaveResult { success: true; id?: string; slug?: string; mtime?: number; }
export interface CaptureResult { success: true; id: string; project_slug: string; }
export interface NewProjectRequest {
  tag: string;
  tipo: 'A' | 'B' | 'C';
  deadline?: string;
  stakeholders?: string;
  description?: string;
  first_intent_tag?: string;
  first_intent_title?: string;
  force?: boolean;
}
export interface NewProjectResult {
  success: true;
  slug: string;
  tipo: string;
  deadline: string | null;
  wip_count: number;
  wip_max: number;
  over_cap: boolean;
  intent_id: string | null;
}
export interface NewIntentRequest {
  project_slug: string;
  tag: string;
  filename: string;
  title: string;
  description?: string;
  deadline?: string;
}
export interface NewIntentResult {
  success: true;
  path: string;
}
export interface ReminderItem {
  id: string;
  title: string;
  path: string;
  reminder_date: string;
  proyecto: string | null;
}
export interface RemindersPayload {
  approaching: ReminderItem[];
  active: ReminderItem[];
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  me: () => call<Me>('/me'),
  home: () => call<HomePayload>('/home'),
  projects: () => call<ProjectListItem[]>('/projects'),
  project: (slug: string) => call<ProjectDetail>(`/projects/${slug}`),
  projectSave: (slug: string, body: string, mtime: number) =>
    call<SaveResult>(`/projects/${slug}`, {
      method: 'POST',
      body: JSON.stringify({ body, mtime }),
    }),
  note: (id: string) => call<NoteDetail>(`/notes/${id}`),
  noteSave: (id: string, body: string, mtime: number) =>
    call<SaveResult>(`/notes/${id}`, {
      method: 'POST',
      body: JSON.stringify({ body, mtime }),
    }),
  noteCreate: (text: string, project_slug: string | null) =>
    call<CaptureResult>('/notes', {
      method: 'POST',
      body: JSON.stringify({ text, project_slug }),
    }),
  projectCreate: (req: NewProjectRequest) =>
    call<NewProjectResult>('/projects', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
  intentCreate: (req: NewIntentRequest) =>
    call<NewIntentResult>('/intents', {
      method: 'POST',
      body: JSON.stringify(req),
    }),
  reveal: (id: string) =>
    call<{ success: true; path: string }>('/reveal', {
      method: 'POST',
      body: JSON.stringify({ id }),
    }),
  reminders: () => call<RemindersPayload>('/reminders'),
  reminderDismiss: (id: string) =>
    call<void>(`/reminder/${encodeURIComponent(id)}/dismiss`, { method: 'PATCH' }),
  reminderSnooze: (id: string, until: string) =>
    call<void>(`/reminder/${encodeURIComponent(id)}/snooze`, {
      method: 'PATCH',
      body: JSON.stringify({ until }),
    }),
  deadlines: () => call<DeadlineGroup[]>('/deadlines'),
  history: () => call<HistoryItem[]>('/history'),
  search: (q: string) =>
    call<SearchHit[]>(`/search?q=${encodeURIComponent(q)}`),
  parakeet: () => call<{ message: string }>('/parakeet'),
  setVault: (name: string) =>
    call<{ success: true; name: string }>('/vault', {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  setTheme: (theme: 'auto' | 'light' | 'dark') =>
    call<{ success: true; theme: string }>('/theme', {
      method: 'POST',
      body: JSON.stringify({ theme }),
    }),
  setNotificationSettings: (settings: { in_app: boolean; os_popups: boolean; sound?: 'Glass' | 'Funk' | 'Silent' }) =>
    call<{ success: true }>('/settings/notifications', {
      method: 'POST',
      body: JSON.stringify(settings),
    }),
  previewNotificationSound: (sound: 'Glass' | 'Funk' | 'Silent') =>
    call<{ success: true }>('/notifications/preview', {
      method: 'POST',
      body: JSON.stringify({ sound }),
    }),
  focusGet: () => call<ManualFocusPayload>('/focus'),
  focusSet: (
    slot: 'today' | 'today_pm' | 'week',
    body: { project_slug: string; intent_slug: string } | { clear: true },
  ) => {
    if (slot === 'week') {
      return call<ManualFocusPayload>('/focus/week', { method: 'PUT', body: JSON.stringify(body) });
    }
    const half = slot === 'today_pm' ? 'pm' : 'am';
    return call<ManualFocusPayload>('/focus/today', { method: 'PUT', body: JSON.stringify({ ...body, slot: half }) });
  },
  checkin: (body: { project_slug: string; intent_slug: string; slot: string }) =>
    call<CheckinResult>('/focus/checkin', { method: 'POST', body: JSON.stringify(body) }),
  checkout: () => call<CheckoutResult>('/focus/checkout', { method: 'POST' }),
  focusHistory: (params: { date?: string; from?: string; to?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.date) qs.set('date', params.date);
    if (params.from) qs.set('from', params.from);
    if (params.to) qs.set('to', params.to);
    const q = qs.toString();
    return call<FocusHistoryPayload>(`/focus/history${q ? `?${q}` : ''}`);
  },
};

// ── Slash-command builders ────────────────────────────────────────────────
// Pure client-side string composition: the UI shows the user the command
// they should paste into Claude Code / Codex / Cursor (or run headless via
// `claude -p "<cmd>"`). No server round-trip, no subprocess, no timeout.

export const slashCommands = {
  brief: (slug: string, stakeholder?: string) => {
    const base = `/squirrel:sq-brief ${slug.toUpperCase()}`;
    const to = (stakeholder ?? '').trim();
    return to ? `${base} --email ${to}` : base;
  },
  start: () => '/squirrel:sq-start',
};

export const headlessClaude = (cmd: string) => `claude -p "${cmd.replace(/"/g, '\\"')}"`;
