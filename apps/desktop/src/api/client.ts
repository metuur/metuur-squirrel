// Phase 2 popup-scoped API client. Hard-coded origin per R-1.1.
// Types copied from apps/backend/app/src/api/client.ts to match the live
// shape verified by the Phase 2 smoke test on 2026-05-28.
//
// Scope: only the endpoints the popup consumes. The browser SPA owns the
// full surface (projects, notes, deadlines, history, search, settings,
// theme, vault). Do not import this client from the browser SPA.

import { invoke } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";

// Backend origin. Defaults to :3939; the dev build overrides it to :3940 via the
// Vite env var `VITE_SQUIRREL_BACKEND_ORIGIN` (set in package.json dev scripts),
// kept in lockstep with the Rust side (backend_supervisor::BACKEND_PORT) so the
// dev app never collides with an installed prod app on the same port.
export const BACKEND_ORIGIN =
  import.meta.env.VITE_SQUIRREL_BACKEND_ORIGIN ?? "http://127.0.0.1:3939";

const REQUEST_TIMEOUT_MS = 3000;

// Per-launch shared secret minted by the Tauri shell (R-1.1). The installed
// backend rejects unauthenticated requests with 401; the popup must present it
// via `X-Squirrel-Token`. Fetched once and cached. Outside a Tauri host (plain
// browser dev, vitest) `invoke` is unavailable/throws — we degrade to no token
// so dev and tests keep working against a token-less backend.
let tokenPromise: Promise<string | null> | undefined;
function runtimeToken(): Promise<string | null> {
  if (!tokenPromise) {
    tokenPromise = invoke<string>("runtime_token").catch(() => null);
  }
  return tokenPromise;
}

// Open a Squirrel web-UI URL in the external browser, carrying the per-launch
// runtime token as `?token=…`. The backend gates `/api/*` on `X-Squirrel-Token`
// and the SPA reads that token from its launch URL; opening the web UI without
// it leaves every API call 401 and the page empty. Accepts an absolute web path
// ("/notes/VISA-001"), "" for the dashboard root, or a full BACKEND_ORIGIN URL
// (e.g. a notification's item_url). Degrades to the un-tokened URL in dev/tests.
export async function openWebUrl(pathOrUrl = ""): Promise<void> {
  const token = await runtimeToken();
  const base = pathOrUrl.startsWith("http") ? pathOrUrl : `${BACKEND_ORIGIN}${pathOrUrl}`;
  const sep = base.includes("?") ? "&" : "?";
  const url = token ? `${base}${sep}token=${encodeURIComponent(token)}` : base;
  await openUrl(url);
}

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
    const token = await runtimeToken();
    const resp = await fetch(BACKEND_ORIGIN + path, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "X-Squirrel-Token": token } : {}),
        ...(init?.headers as Record<string, string> | undefined),
      },
      signal: ctrl.signal,
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
  } catch (e) {
    // An ApiError is a real HTTP response we already classified — rethrow as-is.
    if (e instanceof ApiError) throw e;
    // Otherwise `fetch` itself rejected: the backend sidecar isn't reachable
    // (connection refused → WebKit's opaque "Load failed") or it didn't answer
    // before REQUEST_TIMEOUT_MS (AbortError). Map both to a clear, actionable
    // message so callers never surface the raw transport error to the user.
    const aborted = e instanceof DOMException && e.name === "AbortError";
    throw new ApiError(
      0,
      aborted
        ? "Squirrel’s backend didn’t respond in time — it may still be starting up. Please try again in a moment."
        : "Couldn’t reach Squirrel’s backend — it may still be starting up. Please try again in a moment.",
      e,
    );
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
  /** True when the backend runs without token auth (local/dev), so the UI can
   *  badge this as a non-installed build. */
  dev?: boolean;
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
  // Estimate↔actual reconciliation (derived on read; null when absent).
  estimate_minutes: number | null;
  estimate_user_minutes: number | null;
  time_invested_minutes: number;
  variance_minutes: number | null;
  variance_ratio: number | null;
  has_variance: boolean;
}

export interface ManualFocusPayload {
  today: ManualPick | null;
  today_pm: ManualPick | null;
  week: ManualPick | null;
}

// The single open work session for the vault (checked in, not yet checked out).
// `checkin_at` is a UTC ISO-8601 string written by the backend; the desktop
// derives the live timer from it against the computer's local clock.
export interface OpenSession {
  project_slug: string;
  intent_slug: string;
  checkin_at: string;
}

export interface QuickTask {
  id: string;
  text: string;
  path?: string;
  qt_created_at?: string;
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

export interface HomeQuickTasks {
  active: QuickTask[];
  active_count: number;
  snoozed_count: number;
  oldest: QuickTask | null;
  return_blocked: boolean;
}

export interface HomePayload {
  focus: FocusItem | null;
  pressing: PressingItem[];
  projects: ProjectListItem[];
  manual_focus: ManualFocusPayload;
  parakeet: string;
  journal?: { due: boolean; next_due: string | null };
  quick_tasks?: HomeQuickTasks;
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

// `GET /api/env/obsidian` — onboarding Obsidian probe (server.py::api_env_obsidian)
export interface ObsidianStatus {
  installed: boolean;
  path: string | null;
}

// `POST /api/config/vault` — onboarding vault write (server.py::api_config_vault)
export interface VaultConfigResult {
  name: string;
  path: string;
  default: boolean;
}

// ── Vault recovery ─────────────────────────────────────────────────────────
// /api/me answers 409 (or 503 for NO_VAULT) with a machine-readable `code` when
// the configured vault is missing / empty / not yet a Squirrel vault, so the
// popup can guide re-setup instead of showing a backend-offline banner.
export type VaultRecoveryCode =
  | "NO_VAULT"
  | "VAULT_MISSING"
  | "VAULT_EMPTY"
  | "VAULT_LEGACY"
  | "VAULT_UNSTRUCTURED";

export interface VaultRecoveryPayload {
  error: string;
  code: VaultRecoveryCode;
  vault?: { name: string; path: string };
  vault_status?: "missing" | "empty" | "legacy" | "unstructured";
  migrate_command?: string;
  repair_command?: string;
}

/** Narrow an unknown error to a vault-recovery payload, or null. */
export function asVaultRecovery(err: unknown): VaultRecoveryPayload | null {
  if (!(err instanceof ApiError)) return null;
  const p = err.payload as Partial<VaultRecoveryPayload> | undefined;
  const code = p?.code;
  if (
    code === "NO_VAULT" ||
    code === "VAULT_MISSING" ||
    code === "VAULT_EMPTY" ||
    code === "VAULT_LEGACY" ||
    code === "VAULT_UNSTRUCTURED"
  ) {
    return p as VaultRecoveryPayload;
  }
  return null;
}

export interface VaultRepairResult {
  repaired: { from: string; to: string; action: "rename" | "merge" }[];
  path: string;
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  me: () => call<Me>("/api/me"),
  obsidianStatus: () => call<ObsidianStatus>("/api/env/obsidian"),
  setVaultConfig: (body: { name?: string; path: string; create?: boolean }) =>
    call<VaultConfigResult>("/api/config/vault", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  repairVault: () =>
    call<VaultRepairResult>("/api/vault/repair", { method: "POST" }),
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
  setEstimate: (
    body:
      | { project_slug: string; intent_slug: string; minutes: number }
      | { project_slug: string; intent_slug: string; clear: true },
  ) =>
    call<{ ok: true; estimate: unknown }>("/api/intent/estimate", {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  // Focus check-in / check-out. Backend keeps one open work session per vault.
  focusCheckin: (body: {
    project_slug: string;
    intent_slug: string;
    slot: "today" | "today_pm" | "week";
  }) =>
    call<{ session_id: number }>("/api/focus/checkin", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  // `note` (optional): why the user is switching focus, stored on the session.
  focusCheckout: (note?: string | null) =>
    call<{
      session_id: number;
      duration_minutes: number;
      time_invested_minutes: number;
    }>("/api/focus/checkout", {
      method: "POST",
      body: JSON.stringify(note ? { note } : {}),
    }),
  // 404 (`no_open_session`) is a normal "nothing checked in" state, not an error.
  focusSession: async (): Promise<OpenSession | null> => {
    try {
      return await call<OpenSession>("/api/focus/session");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
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
  // ── Post-its ───────────────────────────────────────────────────────────────
  postItCreate: (text: string, color: string) =>
    call<{ id: string }>("/api/post-its", {
      method: "POST",
      body: JSON.stringify({ text, color }),
    }),
  // ── Quick Tasks ────────────────────────────────────────────────────────────
  quickTasks: () => call<QuickTasksPayload>("/api/quick-tasks"),
  quickTaskCreate: (text: string) =>
    call<{ success: true; id: string }>("/api/quick-tasks", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),
  quickTaskComplete: (id: string) =>
    call<{ success: true }>(`/api/quick-task/${id}/complete`, { method: "PATCH" }),
  quickTaskDelete: (id: string) =>
    call<{ success: true }>(`/api/quick-task/${id}`, { method: "DELETE" }),
  quickTaskSnooze: (id: string, until: string) =>
    call<{ success: true; snoozed_until: string }>(
      `/api/quick-task/${id}/snooze`,
      { method: "PATCH", body: JSON.stringify({ until }) },
    ),
};
