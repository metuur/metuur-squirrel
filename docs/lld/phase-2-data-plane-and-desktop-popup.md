# Phase 2 — Data Plane + Desktop Popup — Low-Level Design

## Architecture

```
Squirrel Phase 2 (two processes the user starts independently)
│
├── apps/backend/server.py                  # long-lived, manually started in Phase 2
│   ├── http.server.HTTPServer @ 127.0.0.1:3939
│   ├── Imports apps/cli/lib/{config_loader, vocabulary, ...} via sys.path
│   ├── /api/me, /api/home, /api/deadlines, /api/projects, /api/notes,
│   │   /api/history, /api/search, /api/parakeet, /api/vault, /api/theme
│   └── Serves dist/ at / when present (SPA shell)
│
└── apps/desktop/ (Tauri v2 process)
    ├── Tauri main (Rust) — Phase 1 plumbing preserved unchanged
    │   ├── Tray controller — gains one new menu item "Open Web UI"
    │   │   └── On click: tauri_plugin_opener::open("http://127.0.0.1:3939")
    │   └── Window event handlers — unchanged
    │
    └── React popup (apps/desktop/src/, new Phase 2 code)
        ├── App.tsx              — popup root, mounts top banner + 4 widgets
        ├── components/
        │   ├── BackendStatusBanner — shows "Backend offline" when /api/me fails
        │   ├── FocusWidget         — today's focus from /api/home
        │   ├── DeadlinesWidget     — top critical/urgent items from /api/home
        │   ├── ParakeetWidget      — one-line nudge from /api/parakeet
        │   ├── CaptureButton       — opens capture modal → POST /api/notes
        │   └── OpenWebUIButton     — visible in the popup too, not just tray
        ├── api/client.ts         — popup-scoped subset of the v0.5 client
        └── hooks/useBackend.ts   — polls /api/me every 10s, exposes {online, error}
```

### Process model

Two processes in Phase 2: the user starts `apps/backend/server.py` manually (`make backend-start`), then launches the Tauri app. The Tauri app does **not** start, manage, or stop the backend. The browser SPA — if used — runs in the user's browser against the same backend. The macOS deadline daemon continues to shell out to `lib/deadline_scanner.py` directly until Phase 3.

### Data flow — happy path

1. User runs `make backend-start` → Python process binds `127.0.0.1:3939`.
2. User opens the Tauri popup (tray icon click or `Open Squirrel`).
3. React mounts; `useBackend()` immediately calls `GET /api/me` → succeeds → `{online: true}`.
4. Each widget fires its own fetch (`/api/home`, `/api/parakeet`) in parallel.
5. Widgets render their slice of the JSON.
6. `useBackend()` re-polls `/api/me` every 10s; if it fails, sets `{online: false}` and the banner takes over.

### Data flow — backend offline

1. `useBackend()` `/api/me` poll fails (timeout or connection refused).
2. `BackendStatusBanner` shows "Backend offline — run `make backend-start`".
3. Widgets that already rendered keep showing their last-good data but go visually muted.
4. `CaptureButton` becomes disabled with a tooltip "Backend offline".
5. `OpenWebUIButton` is still clickable but warns the user via toast that the browser page will fail to load.

### `/api/deadlines` contract (Phase 3 daemon target)

Verified empirically via smoke test against `apps/backend/server.py` on 2026-05-28:

```ts
type DeadlinesResponse = DeadlineGroup[];

interface DeadlineGroup {
  label: string;              // e.g. "Today / Tomorrow", "This Week", "Soon"
  items: DeadlineItem[];      // non-empty; empty groups omitted from response
}

interface DeadlineItem {
  id: string;                 // e.g. "CASA-CONTABILIDAD-TAXES-2025"
  title: string;              // human-readable, may include the id
  deadline: string;           // ISO date "YYYY-MM-DD"
  is_overdue: boolean;
  hours_left: number | null;  // null when is_overdue
  days_overdue: number | null;// null when !is_overdue
}
```

Invariants:
- Groups arrive ordered by urgency: critical/urgent first, then forward in time.
- `hours_left` and `days_overdue` are mutually exclusive — exactly one is non-null per item.
- `id` is the canonical tag and is stable across calls; safe to use as React key and as a daemon dedup key.

The Phase 3 daemon refactor will swap its current `python3 deadline_scanner.py --vault ... --level critical,urgent` shell-out for `GET /api/deadlines?level=critical,urgent` (level filter to be added in Phase 3; today's endpoint returns all levels and the daemon filters client-side).

## Constraints

| Constraint | Source | Implication |
|---|---|---|
| Backend stays Python stdlib only | v0.5 ARCHITECTURE C1; carried forward | No Flask, no Django, no FastAPI in `apps/backend/server.py` |
| `127.0.0.1` binding by default | v0.5 C5 | `--lan` opt-in unchanged; no other host bindings |
| Backend reads `~/.squirrel/config.toml` | Existing config_loader contract | Phase 2 does not introduce a new config surface |
| Manual backend start in Phase 2 | HLD non-goal | No launchd, no Tauri sidecar embedding, no shell-out from Rust |
| Popup ≠ browser SPA | HLD decision | `apps/desktop/src/` writes its own thin widgets; does not import from `apps/backend/app/src/` |
| Tauri CSP allows `127.0.0.1:3939` | Phase 2 goal #4 | `tauri.conf.json` must declare connect-src for the API origin |
| Dev port 1420 for Tauri, 3939 for backend, 5173 for browser SPA | Existing wiring | Vite proxy stays in browser SPA's config; desktop's vite config does not need a proxy (popup uses absolute URL `http://127.0.0.1:3939/api/...` since it shares the webview's origin = `tauri://localhost`) |
| No new third-party React deps for popup | HLD scope | Popup uses React + the existing 5 Tauri plugins; no router (single view), no marked, no Tailwind CDN |
| Type drift fix is non-behavioural | Smoke test finding | `ProjectListItem.last_activity?` declared but UI still degrades when backend omits |

## Key Decisions

### D1. Polling vs. WebSocket for backend liveness
**Decision**: Polling `/api/me` every 10 seconds from `useBackend()`.
**Rationale**: The backend already exposes `/api/me`; adding a WebSocket surface to a stdlib-only `http.server` is a real lift. The popup is opened transiently and dismissed — 10s is well under the user's perception threshold for "is this thing connected". Cost: ~144 requests/day per open popup; well within local-loopback overhead.
**Rejected**: WebSocket (server-side complexity), SSE (same), no polling (banner stays stale).

### D2. Per-widget fetch vs. one aggregating call
**Decision**: Each widget fetches its own endpoint (`/api/home`, `/api/parakeet`) on mount; they do not share a single aggregating call.
**Rationale**: The endpoints are already designed to be cheap and self-contained (v0.5 token-budget contract). Independent fetches keep one slow endpoint from blocking the others and let widgets fail independently.
**Rejected**: A new `/api/popup` aggregating endpoint — premature consolidation; the widget set is going to change.

### D3. Popup widget is hand-rolled, not lifted from browser SPA
**Decision**: `apps/desktop/src/components/` gets its own four small widgets, not imports from `apps/backend/app/src/components/`.
**Rationale**: Aligned with the HLD decision to keep two surfaces separate. The browser SPA's components assume a routed multi-page context, a sidebar, and Tailwind CDN. The popup is a 4-widget vertical stack. Forcing reuse would either bloat the popup or gut the SPA.
**Rejected**: Symlink the SPA's components into desktop/src/ (drags in router, sidebar, modal stack).
**Revisit trigger**: When a 5th widget needs the same Modal or Toast primitive that the SPA already has — that's the moment to extract to `packages/ui/`.

### D4. CSP string for the Tauri webview
**Decision**: Set `tauri.conf.json` security.csp to a fixed allowlist:
```
default-src 'self';
connect-src 'self' http://127.0.0.1:3939;
script-src 'self';
style-src 'self' 'unsafe-inline';
img-src 'self' data:;
```
**Rationale**: Connect to the backend, no other network egress. `'unsafe-inline'` on style-src only — React inline style props need it. No CDN, no fonts.googleapis, no Tailwind CDN — popup uses local CSS only (see D3).
**Rejected**: `csp: null` (current Phase 1 default — too permissive for shipping); a broader CSP matching the browser SPA's CDN-heavy needs (irrelevant for the popup).

### D5. Capture path — POST `/api/notes`, not a new endpoint
**Decision**: The capture button POSTs `{ text, project_slug: null }` to `/api/notes` — same endpoint the browser SPA uses.
**Rationale**: One write path for the vault; the backend already handles atomic writes (v0.5 C7).
**Rejected**: A new `/api/capture` endpoint — duplicates `/api/notes` semantics.

### D6. "Open Web UI" exists in two places (tray menu + popup)
**Decision**: Both the tray menu and the popup body show the "Open Web UI" affordance.
**Rationale**: Discoverability — a user who sees the popup should not need to also know about the tray menu to find the deep view. The tray entry is for users who keep the popup hidden.
**Rejected**: Tray-only (loses discoverability), popup-only (forces opening the popup just to launch the browser).

### D7. Backend lifecycle is the user's responsibility in Phase 2
**Decision**: The Tauri app does not start, restart, or monitor the backend process. It only detects whether the backend is reachable.
**Rationale**: Sidecar lifecycle (Tauri-managed subprocess, crash restart, port collisions, shutdown sequencing) is real engineering work that belongs in Phase 3 alongside the launchd refactor. Shipping Phase 2 without it means the user runs `make backend-start` in a terminal — friction, but bounded and visible.
**Rejected**: Tauri sidecar embedding now (drags Phase 3 work into Phase 2), shelling out to `python3 server.py` from Rust setup (no supervision, dies silently on Python errors).

### D8. The user's launchd-managed backend at `~/Library/LaunchAgents/org.squirrel.web-ui.plist` is not touched
**Decision (original Phase 2 spec)**: Phase 2 does not modify, unload, or rewrite the existing launchd plist that points at the old `adhd-context-bridge/companions/web-ui/server.py`.
**Rationale**: The user's live environment is currently served by that plist (verified during smoke test, PID 26878). Touching it is a Phase 3 concern when the daemon refactor lands together. Until then, the user manually decides which backend they want and runs `make backend-start` from the new monorepo as needed.
**Side effect**: While Phase 2 is being developed, port 3939 may be held by the legacy backend. Smoke-test scripts should accept a `--port` arg (already supported) so the migrated backend can run on 3940 alongside.

**Superseded 2026-05-28**: After the Phase 2 implementation was complete and the migrated backend was verified working at `http://127.0.0.1:3940`, the OLD launchd-served SPA at `:3939` was throwing React #310 from a stale prod bundle. The user explicitly authorized repointing the plist. Sequence executed:
1. `launchctl bootout gui/$UID ~/Library/LaunchAgents/org.squirrel.web-ui.plist`
2. `sed -i.bak-<ts>` swap of `ProgramArguments[1]` from `…/adhd-context-bridge/companions/web-ui/server.py` to `…/squirrel/apps/backend/server.py`
3. `launchctl bootstrap gui/$UID …`
4. Verified PID on `:3939` is running the migrated path and serving the rebuilt dist `index-CDIuq7Ni.js`.

Backup at `~/Library/LaunchAgents/org.squirrel.web-ui.plist.bak-<timestamp>`. Revert: `mv …bak-… plist && launchctl bootout/bootstrap`.

### D9. `dist/` policy stays untracked in the monorepo
**Decision**: `apps/backend/app/dist/` is not committed in this monorepo, despite the v0.5 local `.gitignore` whitelisting it with `!dist/`.
**Rationale**: The monorepo's root `.gitignore` says `dist/` is build output. Anyone building the browser SPA has pnpm available (Tauri needs it too). The v0.5 model where end-users without Node got a pre-built bundle is replaced by either (a) the agent-pack installer running `pnpm -F squirrel-web-ui build`, or (b) the Tauri bundle shipping its own static assets.
**Rejected**: Carry forward `!dist/` and commit minified bundles (merge conflict churn, diff noise).
**Follow-up**: `agent-pack/install.sh` needs an update to add a build step; tracked in Phase 3 distribution work.

## Out of Scope

The following must not appear in Phase 2 implementation:

- Tauri sidecar embedding of `server.py` (Phase 3)
- launchd plist creation, modification, or deletion (Phase 3)
- macOS deadline daemon refactor to use HTTP (Phase 3 — Phase 2 only documents the contract)
- Rust `#[tauri::command]` wrappers for Python CLI calls (rejected: uncle-senior verdict)
- Browser SPA changes beyond the one type-drift fix already landed
- Backend auth, TLS, or non-localhost binding
- Backend writes from the popup beyond `/api/notes` capture (no project create, no settings, no theme — all reachable in the browser SPA)
- AI / LLM endpoints (`/api/ai/*` stays out)
- A `packages/ui/` lifted-component layer (deferred until pain shows up)
- Windows artifact, Linux daemon, mobile
- Vault watcher (Rust fake watcher from Phase 1 stays as-is)
- Replacing the Phase 1 fake watcher with a real one
- Settings UI in the popup
- Multi-vault picker UI in the popup (browser SPA owns that)
- Push from backend to popup (popup polls; no server-sent events)
