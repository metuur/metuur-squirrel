# Phase 2 — Data Plane + Desktop Popup — EARS Specifications

## Unit 1: Backend reachability

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL treat `http://127.0.0.1:3939` as the canonical backend origin for the popup. The origin SHALL be hard-coded in `apps/desktop/src/api/client.ts` and SHALL NOT be configurable in Phase 2. |
| R-1.2 | WHEN the popup mounts, THE SYSTEM SHALL issue `GET /api/me` within 500ms and SHALL re-issue it every 10 seconds while the popup is mounted. |
| R-1.3 | IF `GET /api/me` returns a 2xx response, THE SYSTEM SHALL set backend status to `online`. |
| R-1.4 | IF `GET /api/me` returns a non-2xx response OR fails with a connection error OR times out after 3 seconds, THE SYSTEM SHALL set backend status to `offline`. |
| R-1.5 | WHILE backend status is `offline`, THE SYSTEM SHALL display a top banner reading "Backend offline — run `make backend-start` in the squirrel monorepo". |
| R-1.6 | WHEN backend status transitions from `offline` to `online`, THE SYSTEM SHALL hide the banner and SHALL re-trigger each widget's data fetch within 1 second. |
| R-1.7 | THE SYSTEM SHALL NOT start, restart, or stop the `apps/backend/server.py` process from the Tauri app in Phase 2. |

## Unit 2: Popup widgets

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE popup SHALL render exactly five visible elements, in order: BackendStatusBanner (visible only when offline), FocusWidget, DeadlinesWidget, ParakeetWidget, CaptureButton, OpenWebUIButton. |
| R-2.2 | WHEN the popup mounts AND backend status is `online`, THE FocusWidget SHALL issue `GET /api/home` and SHALL render the `focus.title` and `focus.next_action` fields. |
| R-2.3 | IF `/api/home` returns `focus: null`, THE FocusWidget SHALL display "No active focus — capture a thought or start a project." |
| R-2.4 | WHEN the popup mounts AND backend status is `online`, THE DeadlinesWidget SHALL render the first 3 items from `/api/home.pressing[]`. |
| R-2.5 | THE DeadlinesWidget SHALL display each item as `{title} — {is_overdue ? "OVERDUE " + days_overdue + "d" : hours_left + "h left"}`. |
| R-2.6 | IF `/api/home.pressing[]` is empty, THE DeadlinesWidget SHALL display "Nothing pressing today." |
| R-2.7 | WHEN the popup mounts AND backend status is `online`, THE ParakeetWidget SHALL issue `GET /api/parakeet` and SHALL render the `message` string verbatim. |
| R-2.8 | IF `GET /api/parakeet` returns an empty or whitespace-only message, THE ParakeetWidget SHALL render nothing (zero vertical space). |
| R-2.9 | WHILE backend status is `offline`, FocusWidget / DeadlinesWidget / ParakeetWidget SHALL display their last successfully-fetched data with reduced opacity (≤0.5), OR a placeholder dash "—" if no successful fetch has occurred. |

## Unit 3: Capture path

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE CaptureButton SHALL be visible at all times the popup is mounted. |
| R-3.2 | WHILE backend status is `offline`, THE CaptureButton SHALL be disabled and SHALL show a tooltip "Backend offline — capture will fail". |
| R-3.3 | WHEN the user clicks CaptureButton AND backend status is `online`, THE SYSTEM SHALL open a modal with a single multi-line text input and Save / Cancel buttons. |
| R-3.4 | WHEN the user clicks Save in the capture modal, THE SYSTEM SHALL `POST /api/notes` with body `{ text: <input value>, project_slug: <user's ProjectSelector choice; null = Inbox> }`. **Amended 2026-05-28**: the original wording hard-coded `project_slug: null`. A chip-row selector now lets the user route the capture to any project from `/api/home.projects[]`, with the focus project highlighted as a suggested target. |
| R-3.5 | IF the POST returns 2xx, THE SYSTEM SHALL close the modal AND display a toast "Captured to inbox". |
| R-3.6 | IF the POST returns non-2xx, THE SYSTEM SHALL keep the modal open, display the server error message inline, and SHALL NOT clear the input. |
| R-3.7 | THE SYSTEM SHALL NOT add `/api/capture` or any new write endpoint in Phase 2. The capture path reuses `/api/notes`. |

## Unit 4: "Open Web UI" affordance

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE tray menu SHALL gain a new item "Open Web UI" placed between "Open Squirrel" and "Background Watcher (On/Off)". |
| R-4.2 | THE popup SHALL display an "Open Web UI" button at the bottom. |
| R-4.3 | WHEN the user clicks either affordance, THE SYSTEM SHALL invoke `tauri-plugin-opener` with the URL `http://127.0.0.1:3939`. |
| R-4.4 | THE SYSTEM SHALL NOT pre-check backend reachability before invoking `tauri-plugin-opener`. If the backend is offline, the user's browser will surface its own error. |

## Unit 5: CSP and security

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | `apps/desktop/src-tauri/tauri.conf.json` SHALL set `app.security.csp` to a non-null string allowing exactly: `default-src 'self'`, `connect-src 'self' http://127.0.0.1:3939`, `script-src 'self'`, `style-src 'self' 'unsafe-inline'`, `img-src 'self' data:`. |
| R-5.2 | THE popup's React code SHALL NOT load any external CDN, font, image, or script. Tailwind CDN is not used; popup styling lives in local CSS. |
| R-5.3 | THE SYSTEM SHALL NOT issue any network request to a host other than `127.0.0.1:3939` from the Tauri webview. |

## Unit 6: Type contract

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | `apps/desktop/src/api/client.ts` SHALL declare TypeScript types matching the live `/api/me`, `/api/home`, `/api/parakeet`, and `/api/notes` response shapes (as verified by the Phase 2 smoke test on 2026-05-28). |
| R-6.2 | THE SYSTEM SHALL declare `ProjectListItem.last_activity?: string \| null` to match the type fix already committed (65898c7). |
| R-6.3 | THE `/api/deadlines` response contract SHALL be documented in `docs/lld/phase-2-data-plane-and-desktop-popup.md` § "`/api/deadlines` contract". Implementation of the daemon refactor consuming this contract is Phase 3. |

## Unit 7: Out-of-scope guards (negative requirements)

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL NOT embed or spawn the Python backend as a Tauri sidecar in Phase 2. |
| R-7.2 | THE SYSTEM SHALL NOT create, modify, or remove any launchd plist in Phase 2. **Superseded 2026-05-28**: user explicitly authorized repointing `org.squirrel.web-ui.plist` from the source-repo path to `apps/backend/server.py`. See LLD D8 supersession note. |
| R-7.3 | THE SYSTEM SHALL NOT add `#[tauri::command]` wrappers that shell out to the `squirrel` Python CLI. All data flows from the webview's `fetch()` to the backend's HTTP API. |
| R-7.4 | THE SYSTEM SHALL NOT introduce a `packages/ui/` shared-component layer in Phase 2. The popup's components live exclusively under `apps/desktop/src/components/`. |
| R-7.5 | THE SYSTEM SHALL NOT alter the macOS deadline daemon (`agent-pack/companions/macos-reminders/reminder-daemon.sh`) in Phase 2. The daemon continues to shell out to `lib/deadline_scanner.py` directly. |
| R-7.6 | THE SYSTEM SHALL NOT change the Phase 1 fake watcher; the Rust 60-second simulated event source remains the only event producer in Phase 2. |
