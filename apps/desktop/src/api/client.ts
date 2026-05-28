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

export interface PressingItem {
  id: string;
  title: string;
  deadline: string;
  urgency: string;
  urgency_label: string;
  is_overdue: boolean;
  hours_left: number | null;
  days_overdue: number | null;
  /** Unix epoch seconds of the note file's last modification. Added in
   *  Phase 2; may be `null` if the file wasn't found at scan time. */
  mtime?: number | null;
}

export interface ProjectListItem {
  slug: string;
  title: string;
  percent_done?: number;
  deadline?: string | null;
  active_intent?: string | null;
  last_activity?: string | null;
}

export interface HomePayload {
  focus: FocusItem | null;
  pressing: PressingItem[];
  projects: ProjectListItem[];
  parakeet: string;
}

export interface ParakeetPayload {
  message: string;
}

export interface CaptureResult {
  success: true;
  id: string;
  project_slug: string;
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  me: () => call<Me>("/api/me"),
  home: () => call<HomePayload>("/api/home"),
  parakeet: () => call<ParakeetPayload>("/api/parakeet"),
  noteCreate: (text: string, project_slug: string | null) =>
    call<CaptureResult>("/api/notes", {
      method: "POST",
      body: JSON.stringify({ text, project_slug }),
    }),
};
