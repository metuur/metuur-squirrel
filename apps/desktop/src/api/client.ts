// Phase 2 popup-scoped API client. Hard-coded origin per R-1.1.
// Types copied from apps/backend/app/src/api/client.ts to match the live
// shape verified by the Phase 2 smoke test on 2026-05-28.
//
// Scope: only the endpoints the popup consumes. The browser SPA owns the
// full surface (projects, notes, deadlines, history, search, settings,
// theme, vault). Do not import this client from the browser SPA.

export const BACKEND_ORIGIN = "http://127.0.0.1:3939";

const REQUEST_TIMEOUT_MS = 3000;

export class ApiError extends Error {
  status: number;
  payload: unknown;
  constructor(status: number, message: string, payload?: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
  try {
    const resp = await fetch(BACKEND_ORIGIN + path, {
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
      ...init,
    });
    const text = await resp.text();
    let data: unknown = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      /* not JSON */
    }
    if (!resp.ok) {
      const msg =
        (data && typeof data === "object" && "error" in data && typeof (data as { error: unknown }).error === "string"
          ? (data as { error: string }).error
          : null) ||
        (data && typeof data === "object" && "message" in data && typeof (data as { message: unknown }).message === "string"
          ? (data as { message: string }).message
          : null) ||
        `Request failed (${resp.status})`;
      throw new ApiError(resp.status, msg, data);
    }
    return data as T;
  } finally {
    clearTimeout(timer);
  }
}

// ── Types ────────────────────────────────────────────────────────────────────
// Mirror the live response shapes. Any drift from the browser SPA's
// client.ts is intentional (popup needs less; see LLD D3).

export interface Workspace {
  name: string;
  path: string;
  default: boolean;
}

export interface Me {
  active_workspace: Workspace;
  workspaces: Workspace[];
  multi_vault: boolean;
  theme: "auto" | "light" | "dark";
  version: string;
}

export interface FocusItem {
  slug: string;
  title: string;
  next_action: string;
  reason: string;
}

export type EntityKind = "project" | "project-task" | "note";

export interface PressingItem {
  id: string;
  title: string;
  deadline: string;
  urgency: string;
  urgency_label: string;
  is_overdue: boolean;
  hours_left: number | null;
  days_overdue: number | null;
  /** Unix epoch seconds of the most recent `/sq-end` shutdown note on this
   *  task. `null` when the task has never been formally worked on (no
   *  shutdown notes exist). Carries the "when did I last sit down with
   *  this" semantic — much more meaningful than file mtime, which fires
   *  on every save. */
  last_worked?: number | null;
  /** Vault classification: project page, project-task (intent), or a free
   *  standalone note. Present on every response since the kind-badge work
   *  on 2026-05-31; older builds may omit it, hence optional here. */
  kind?: EntityKind;
  /** Present only when `kind === 'project'` — the project's folder/slug. */
  slug?: string;
}

export interface ProjectListItem {
  slug: string;
  title: string;
  percent_done?: number;
  deadline?: string | null;
  active_intent?: string | null;
  last_activity?: string | null;
  kind?: "project";
}

export interface ManualPick {
  project_slug: string;
  project_title: string;
  intent_slug: string;
  intent_title: string;
  next_action: string | null;
  picked_on: string;
  note: string | null;
}

export interface ManualFocusPayload {
  today: ManualPick | null;
  today_pm: ManualPick | null;
  week: ManualPick | null;
}

export interface HomePayload {
  focus: FocusItem | null;
  pressing: PressingItem[];
  projects: ProjectListItem[];
  manual_focus: ManualFocusPayload;
  parakeet: string;
  journal?: { due: boolean; next_due: string | null };
}

export type Mood = "happy" | "neutral" | "sad";
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

export interface ParakeetPayload {
  message: string;
}

export interface CaptureResult {
  success: true;
  id: string;
  project_slug: string;
}

// `GET /api/projects/{slug}` — shape mirrored from
// apps/backend/server.py::api_project_detail. The `notes[]` collection is the
// project's intent files (every `*.md` inside the project dir except the
// project page itself, sorted by mtime desc).
export interface ProjectNote {
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
  notes: ProjectNote[];
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

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  me: () => call<Me>("/api/me"),
  home: () => call<HomePayload>("/api/home"),
  parakeet: () => call<ParakeetPayload>("/api/parakeet"),
  journal: () => call<JournalPayload>("/api/journal"),
  journalEntry: (body: { mind: string; doing: string; mood: Mood }) =>
    call<{ success: true }>("/api/journal/entry", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  noteCreate: (text: string, project_slug: string | null) =>
    call<CaptureResult>("/api/notes", {
      method: "POST",
      body: JSON.stringify({ text, project_slug }),
    }),
  projectDetail: (slug: string) =>
    call<ProjectDetail>(`/api/projects/${slug}`),
  focusSet: (
    slot: "today" | "today_pm" | "week",
    body:
      | { project_slug: string; intent_slug: string; note?: string | null }
      | { clear: true },
  ) => {
    if (slot === "week") {
      return call<ManualFocusPayload>("/api/focus/week", {
        method: "PUT",
        body: JSON.stringify(body),
      });
    }
    const half = slot === "today_pm" ? "pm" : "am";
    return call<ManualFocusPayload>("/api/focus/today", {
      method: "PUT",
      body: JSON.stringify({ ...body, slot: half }),
    });
  },
  notifications: (params: { limit?: number; unread?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    if (params.unread) qs.set("unread", "true");
    const query = qs.toString();
    return call<NotificationsPayload>(
      `/api/notifications${query ? `?${query}` : ""}`,
    );
  },
  notificationsMarkAllRead: () =>
    call<{ updated: number }>("/api/notifications/read-all", {
      method: "POST",
    }),
  notificationRead: (id: number) =>
    call<{ success: true }>(`/api/notification/${id}/read`, {
      method: "PATCH",
    }),
  notificationDismiss: (id: number) =>
    call<{ success: true }>(`/api/notification/${id}/dismiss`, {
      method: "PATCH",
    }),
};
