// Squirrel JSON API client — all calls hit /api/* on the Python server.
// In dev (vite), /api/* is proxied to http://127.0.0.1:3939 (vite.config.ts).
// In prod (squirrel web open-web), the SPA is served BY the Python server, so
// /api/* is same-origin.

const BASE = '/api';
const TOKEN_KEY = 'squirrel_auth_token';

// Read ?token= from the launch URL once, store in sessionStorage, strip from history.
(function bootstrapToken() {
  const params = new URLSearchParams(window.location.search);
  const t = params.get('token');
  if (t) {
    sessionStorage.setItem(TOKEN_KEY, t);
    params.delete('token');
    const rest = params.toString();
    const next = window.location.pathname + (rest ? `?${rest}` : '') + window.location.hash;
    window.history.replaceState(null, '', next);
  }
})();

function authHeaders(): Record<string, string> {
  const t = sessionStorage.getItem(TOKEN_KEY);
  return t ? { 'X-Squirrel-Token': t } : {};
}

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
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
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
  /** True when the backend runs without token auth (local/dev). */
  dev?: boolean;
}

// ── Vault recovery ─────────────────────────────────────────────────────────
// When a vault is configured but its directory is missing / empty / not yet a
// Squirrel vault, the backend answers /api/me with 409 (or 503 for NO_VAULT)
// whose JSON body carries a machine-readable `code` so the UI can guide setup.
export type VaultRecoveryCode =
  | 'NO_VAULT'
  | 'VAULT_MISSING'
  | 'VAULT_EMPTY'
  | 'VAULT_LEGACY'
  | 'VAULT_UNSTRUCTURED';

export interface VaultRecoveryPayload {
  error: string;
  code: VaultRecoveryCode;
  vault?: { name: string; path: string };
  vault_status?: 'missing' | 'empty' | 'legacy' | 'unstructured';
  migrate_command?: string;
  repair_command?: string;
}

/** Narrow an unknown error to a vault-recovery payload, or null. */
export function asVaultRecovery(err: unknown): VaultRecoveryPayload | null {
  if (!(err instanceof ApiError)) return null;
  const p = err.payload as Partial<VaultRecoveryPayload> | undefined;
  const code = p?.code;
  if (
    code === 'NO_VAULT' ||
    code === 'VAULT_MISSING' ||
    code === 'VAULT_EMPTY' ||
    code === 'VAULT_LEGACY' ||
    code === 'VAULT_UNSTRUCTURED'
  ) {
    return p as VaultRecoveryPayload;
  }
  return null;
}

export interface VaultRepairResult {
  repaired: { from: string; to: string; action: 'rename' | 'merge' }[];
  path: string;
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
  delivered?: boolean;
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
  // Estimate↔actual reconciliation (derived on read; null when absent).
  estimate_minutes: number | null;
  estimate_user_minutes: number | null;
  variance_minutes: number | null;
  variance_ratio: number | null;
  has_variance: boolean;
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
  deadline: string | null;
  mtime: number;
  project_slug: string;
  kind: 'note' | 'project-task';
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
  name: string;
  tag: string;
  type: 'A' | 'B' | 'C';
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
  type: string;
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
  project: string | null;
}
export interface RemindersPayload {
  approaching: ReminderItem[];
  active: ReminderItem[];
}
export type Mood = 'happy' | 'neutral' | 'sad';
export interface JournalEntry {
  timestamp: string;
  mood: Mood;
  mind: string;
  doing: string;
}
export interface JournalPayload {
  exists: boolean;
  task?: { id: string; title: string; path: string };
  entries?: JournalEntry[];
  due?: boolean;
  next_due?: string | null;
  interval_hours?: number;
  waking?: { start: string; end: string };
}
export interface JournalConfig {
  interval_hours?: number;
  waking_start?: string;
  waking_end?: string;
}

// `GET /api/notifications` — shape mirrored from apps/backend/server.py::api_notifications
export interface NotificationItem {
  id: number;
  type: string;
  item_id: string;
  title: string;
  body: string;
  item_url: string | null;
  fired_at: string;
  read_at: string | null;
  dismissed_at: string | null;
}
export interface NotificationsPayload {
  items: NotificationItem[];
  unread_count: number;
  total_count: number;
}

export interface PostItLayout {
  x: number;
  y: number;
  rotation: number;
  z: number;
}

export interface PostIt {
  id: string;
  text: string;
  color: string;
  label: string;
  pinned: boolean;
  state: string;
  created: string | null;
  converted_to: string;
  layout: PostItLayout | null;
}

export interface QuickTask {
  id: string;
  text: string;
  qt_snoozed_until?: string;
  return_blocked?: boolean;
}

export interface QuickTasksPayload {
  active: QuickTask[];
  snoozed: QuickTask[];
  active_count: number;
  snoozed_count: number;
  limit: number;
  return_blocked: boolean;
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  me: () => call<Me>('/me'),
  home: () => call<HomePayload>('/home'),
  projects: () => call<ProjectListItem[]>('/projects'),
  project: (slug: string) => call<ProjectDetail>(`/projects/${slug}`),
  projectSetStatus: (slug: string, body: { deadline?: string | null; delivered?: boolean }) =>
    call<{ success: true; slug: string; deadline: string | null; delivered: boolean }>(
      `/projects/${slug}/status`,
      { method: 'PATCH', body: JSON.stringify(body) },
    ),
  // Push any item's deadline out (defer / snooze) so it leaves the computed
  // PRESSING lane. Works for notes, tasks, and projects alike.
  itemDefer: (id: string, until: string) =>
    call<{ success: true; id: string; deadline: string }>(
      `/item/${encodeURIComponent(id)}/defer`,
      { method: 'PATCH', body: JSON.stringify({ until }) },
    ),
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
  journal: () => call<JournalPayload>('/journal'),
  journalCreate: () => call<JournalPayload>('/journal', { method: 'POST' }),
  journalEntry: (body: { mind: string; doing: string; mood: Mood }) =>
    call<{ success: true }>('/journal/entry', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  journalConfig: (body: JournalConfig) =>
    call<{ success: true }>('/journal/config', {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  notifications: (params: { limit?: number; unread?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.limit !== undefined) qs.set('limit', String(params.limit));
    if (params.unread) qs.set('unread', 'true');
    const query = qs.toString();
    return call<NotificationsPayload>(`/notifications${query ? `?${query}` : ''}`);
  },
  notificationsMarkAllRead: () =>
    call<{ updated: number }>('/notifications/read-all', { method: 'POST' }),
  notificationRead: (id: number) =>
    call<{ success: true }>(`/notification/${id}/read`, { method: 'PATCH' }),
  notificationDismiss: (id: number) =>
    call<{ success: true }>(`/notification/${id}/dismiss`, { method: 'PATCH' }),
  reminders: () => call<RemindersPayload>('/reminders'),
  reminderDismiss: (id: string) =>
    call<void>(`/reminder/${encodeURIComponent(id)}/dismiss`, { method: 'PATCH' }),
  reminderSnooze: (id: string, until: string) =>
    call<void>(`/reminder/${encodeURIComponent(id)}/snooze`, {
      method: 'PATCH',
      body: JSON.stringify({ until }),
    }),
  quickTasks: () => call<QuickTasksPayload>('/quick-tasks'),
  quickTaskCreate: (text: string) =>
    call<{ success: true; id: string }>('/quick-tasks', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),
  quickTaskComplete: (id: string) =>
    call<{ success: true }>(`/quick-task/${encodeURIComponent(id)}/complete`, { method: 'PATCH' }),
  quickTaskDelete: (id: string) =>
    call<{ success: true }>(`/quick-task/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  quickTaskSnooze: (id: string, until: string) =>
    call<{ success: true; snoozed_until: string }>(`/quick-task/${encodeURIComponent(id)}/snooze`, {
      method: 'PATCH',
      body: JSON.stringify({ until }),
    }),
  postItsList: (includeArchived = false) =>
    call<PostIt[]>(`/post-its${includeArchived ? "?include=archived" : ""}`),
  postItCreate: (payload: { text: string; color?: string; label?: string }) =>
    call<PostIt>("/post-its", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  postItUpdateLayout: (id: string, layout: { x: number; y: number; rotation: number; z?: number }) =>
    call<{ success: boolean }>(`/post-it/${id}/layout`, {
      method: "PATCH",
      body: JSON.stringify(layout),
    }),
  postItUpdate: (id: string, fields: Partial<{ text: string; color: string; label: string; pinned: boolean }>) =>
    call<{ success: boolean }>(`/post-it/${id}`, {
      method: "PATCH",
      body: JSON.stringify(fields),
    }),
  postItArchive: (id: string) =>
    call<{ success: boolean }>(`/post-it/${id}/archive`, { method: "PATCH" }),
  postItRestore: (id: string) =>
    call<{ success: boolean }>(`/post-it/${id}/restore`, { method: "PATCH" }),
  postItDelete: (id: string) =>
    call<{ success: boolean }>(`/post-it/${id}`, { method: "DELETE" }),
  postItConvert: (id: string, target: string, projectSlug?: string) =>
    call<{ success: boolean; ref: string }>(`/post-it/${id}/convert`, {
      method: "POST",
      body: JSON.stringify({ target, project_slug: projectSlug }),
    }),
  projectsList: () => call<{ slug: string; name: string }[]>("/projects"),
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
  // Set/repair the default vault in config.toml. `create: true` makes the folder
  // (and scaffolds the Squirrel structure) when it's missing or empty.
  setVaultConfig: (body: { name?: string; path: string; create?: boolean }) =>
    call<{ name: string; path: string; default: boolean }>('/config/vault', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  // Rename an old (legacy/Spanish) vault's folders to the canonical names in place.
  repairVault: () =>
    call<VaultRepairResult>('/vault/repair', { method: 'POST' }),
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
  setEstimate: (
    body:
      | { project_slug: string; intent_slug: string; minutes: number }
      | { project_slug: string; intent_slug: string; clear: true },
  ) =>
    call<{ ok: true; estimate: unknown }>('/intent/estimate', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),
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
