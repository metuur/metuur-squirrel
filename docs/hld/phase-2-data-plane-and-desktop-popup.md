# Phase 2 — Data Plane + Desktop Popup — High-Level Design

## Overview

Phase 1 proved the Tauri desktop runtime works (tray, lifecycle, notifications, accessory app behaviour) with a fake internal watcher. Phase 2 brings the system online: the Python backend (`apps/backend/server.py`, migrated from v0.5) runs as a long-lived local JSON API, and the desktop's React popup makes real fetch calls against it. The browser-served SPA at `apps/backend/app/` stays as a separate, deeper surface for vault navigation. Phase 2 is the moment Squirrel stops being a shell and starts showing vault data.

The unifying architectural commitment: **one API, multiple consumers**. The Tauri popup, the browser SPA, and (later) the macOS deadline daemon all read from the same `http://127.0.0.1:3939/api/*` surface. The shared Python core in `apps/cli/lib/` remains the single source of truth for parsing, aggregation, and classification.

## Stakeholders & Impact

| Stakeholder | Today's pain | After Phase 2 ships |
|---|---|---|
| Primary user (Javier) | SQ icon shows but does nothing real; vault state invisible from the desktop | Popup shows today's focus + next critical deadline; tray opens the browser SPA for deeper work |
| macOS deadline daemon | Polls `lib/deadline_scanner.py` directly; cannot be replaced without reworking the daemon shell script | A documented `/api/deadlines` contract exists; Phase 3 can swap the daemon to HTTP without changing semantics |
| Browser SPA at `apps/backend/app/` | Works against a backend that lives at `companions/web-ui/`; broken after migration | Builds and runs against `apps/backend/server.py` end-to-end |
| Future Phase 3 (sidecar lifecycle, daemon refactor, launchd) | Each piece would need to invent its own backend-launching mechanism | Phase 2 nails down the "backend is a long-lived 127.0.0.1:3939 service" contract that Phase 3 plugs into |

Out-of-scope consumers (Obsidian plugin, vault-watcher Rust crate, agent skills/hooks) are listed only to confirm they are not stakeholders for Phase 2.

## Goals

When Phase 2 ships, the following are observable and true:

1. **`apps/backend/server.py` runs end-to-end after the migration.** Invoking it manually (`python3 apps/backend/server.py --port 3939`) imports `config_loader` + `vocabulary` from `apps/cli/lib/`, opens the configured vault, and serves `/api/*`.
2. **The browser SPA works against the migrated backend.** `pnpm -F squirrel-web-ui dev` proxies `/api/*` to `127.0.0.1:3939` and every page (Home, Projects, Notes, Deadlines, History, Search, Settings) renders without changes to API client code.
3. **The Tauri popup is wired to the backend.** `apps/desktop/src/` gains a small set of widgets — *today's focus*, *next critical deadline*, *capture button*, *Open Web UI* — fed by `fetch('/api/...')`. No `tauri::command` is required for Phase 2; the React code uses the same `api/client.ts` shape as the browser SPA.
4. **Tauri's webview can reach `127.0.0.1:3939` in prod.** `tauri.conf.json` declares a CSP that allows `connect-src http://127.0.0.1:3939`. Dev still uses Vite's proxy on port 1420.
5. **The tray's "Open Web UI" item launches the browser** at `http://127.0.0.1:3939` via `tauri-plugin-opener`.
6. **The popup gracefully degrades when the backend isn't running.** Each widget shows a "Backend offline — run `python3 apps/backend/server.py`" placeholder instead of crashing.
7. **`make backend-start` is the canonical dev entry point** for the API. The desktop and browser surfaces both assume the user (or, later, Phase 3) is responsible for keeping the backend alive.
8. **The `/api/deadlines` contract is documented** in `docs/lld/phase-2-data-plane-and-desktop-popup.md` so the Phase 3 daemon refactor has a stable target.

## Non-Goals

Out of scope for Phase 2:

- **Auto-starting / embedding the backend as a Tauri sidecar.** Phase 2 ships with a manually-started backend; sidecar lifecycle is Phase 3.
- **Refactoring the macOS deadline daemon to call the API.** Phase 2 only nails the contract; the daemon still shells out to `lib/deadline_scanner.py` directly until Phase 3.
- **`launchd` plist for the backend.** Same reasoning — Phase 3.
- **Tauri Rust ↔ Python `invoke()` bridge.** Rejected in conversation: the multi-consumer model makes a long-lived HTTP API simpler than per-call subprocess shell-outs from Rust.
- **Merging the browser SPA into the Tauri webview.** Rejected: the two surfaces have different shapes (deep SPA vs. glanceable popup) and stay separate. A `packages/ui/` lifted-shared-components layer can come later if duplication starts hurting.
- **Real vault watcher.** The Rust-side fake watcher stays. A real watcher is a separate Phase.
- **Auth, multi-user, or any non-`127.0.0.1` binding** by default. `--lan` opt-in stays; nothing else changes.
- **Windows artifact** as a release deliverable. Cross-platform code paths must not regress, but no Windows MSI ships from Phase 2.
- **AI features.** The v0.5 `/api/ai/*` surface is out of scope; assertions stay skipped (see test triage commit `b3f0ae8`).

## Success Criteria

Phase 2 is done when a fresh checkout can:

1. `make test-cli` — green, no new failures.
2. `python3 apps/backend/server.py --port 3939` — starts, logs "vault X loaded", serves `/api/me`.
3. `pnpm -F squirrel-web-ui dev` — Home page loads with real focus + projects + deadlines from the vault. Every nav route works.
4. `pnpm tauri dev` — popup window opens; widgets show today's focus + next deadline pulled from `/api/home` and `/api/deadlines`; "Open Web UI" tray item launches the browser.
5. Stop the backend (`pkill -f apps/backend/server.py`); reopen the popup; widgets show the "backend offline" state instead of erroring.
6. Restart the backend; widgets recover on next interaction.
7. `docs/lld/phase-2-data-plane-and-desktop-popup.md` documents the `/api/deadlines` response shape (the contract Phase 3's daemon will consume).

If all seven steps pass, Phase 2 ships.
