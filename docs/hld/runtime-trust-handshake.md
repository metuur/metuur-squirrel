# Runtime Trust Handshake — High-Level Design

## Overview

Squirrel's Tauri shell currently treats anything listening on `127.0.0.1:3939` as the legitimate backend (`apps/desktop/src-tauri/src/backend_supervisor.rs:117-134`). A malicious local process that wins the port race can intercept every API call, capture all note edits, and drive the React UI through fake responses. The Tauri webview CSP (`tauri.conf.json:28` — `connect-src 'self' http://127.0.0.1:3939`) is no defense, because the squatter *is* `127.0.0.1:3939`.

This change introduces a per-launch shared-secret handshake between the Tauri shell and the backend it intends to use. Tauri generates a 32-byte token at startup, passes it to the spawned sidecar via argv, and challenges any pre-existing listener (Adopted mode) with the same token before issuing any API call. A listener that cannot return the matching token is refused; the tray shows an Error state and the user gets a banner naming the cause.

The token never touches disk for the normal in-app flow. The launchd-supervised backend (CLI install path, no Tauri parent at backend start) reads the token from `~/.squirrel/launchd-token`, which the Tauri installer writes once at install time with `chmod 0600` — separating runtime race conditions from install-time authenticated provisioning.

## Stakeholders & Impact

| Stakeholder | Today's pain | After this ships |
|---|---|---|
| Primary user (Javier) | Anything listening on :3939 is silently trusted. A port-squatting local process can read every vault edit and serve fake `/api/home` content to drive the user toward attacker-controlled "PRESSING NOW" items in the tray | The Tauri shell refuses to adopt unverified listeners; tray Error state and an explicit banner appear instead of silent compromise. The squatter cannot mint the credential that proves it legitimate, because Tauri (not the backend) is the trust anchor. |
| CLI-only / dev-backend users (`make backend-start` in a terminal) | Same trust gap, with the added confusion that the GUI might silently adopt the dev backend without making the user aware | Backend started without `--token` runs in explicit "dev mode". GUI refuses to adopt it and the banner names the dev-mode case. Terminal-hacking flow continues to work for CLI-only use. |
| launchd-supervised backend (no Tauri parent at backend start) | No way to authenticate the GUI without runtime cooperation | Install-time provisioned token at `~/.squirrel/launchd-token` (`chmod 0600`, user-owned). Tauri reads it on launch and verifies the launchd-supervised backend the same way it would verify a spawned sidecar. |

Out-of-scope consumers (LAN-mode callers, GPG sync packages, DMG/sidecar codesign) are listed only to confirm they are not addressed here.

## Goals

When this ships, the following are observable and true:

1. **A Tauri-spawned sidecar accepts API calls only when the request carries the matching `X-Squirrel-Token` header.** Every existing route under `/api/*` enforces this.
2. **A `GET /api/_handshake` endpoint exists.** It returns `200 {"token_echo": "<hex>"}` when the request header matches; `401` with empty body otherwise.
3. **When :3939 is already bound at Tauri startup, Tauri probes `/api/_handshake` with its in-memory token within a 3-second budget.** Mismatch → refuse adoption: tray Error icon, banner, no API call issued, no fallback port.
4. **Backend started without `--token` (and without `--token-file`) runs in dev mode** — serves loopback without authentication, logs `WARN: dev mode, no token auth` at startup, returns `200 {"mode": "dev"}` from `/api/_handshake`. Tauri treats `mode=dev` as adopt-refusal.
5. **The launchd plist (when installed) passes `--token-file ~/.squirrel/launchd-token`.** The Tauri installer writes this file once at first install with 32 bytes of entropy, `chmod 0600`, owner = user. Tauri reads the same file when launching against a launchd-supervised backend.
6. **No runtime token is ever written to disk by the Tauri shell or by the backend.** The only on-disk token is the install-time `launchd-token`.
7. **Adoption refusal is observable to the user** through the tray icon state and the banner text — no silent compromise, no silent retry.

## Non-Goals

- **No protection against attackers with the user's UID or with root.** Such an attacker can read process argv, attach a debugger, or read the launchd-token file. The threat model is "other local process running as the same UID at startup race time", not "compromised user account".
- **No cryptographic handshake protocol.** No Diffie-Hellman, no nonce, no signed response. This is a pre-shared-secret comparison, not an authenticated key exchange.
- **No request-body HMAC.** Loopback HTTP between two processes the same user owns does not need integrity protection beyond TCP.
- **No token rotation during a session.** Tokens live for the process lifetime.
- **No LAN-mode authentication.** That is a separate change (M3 in the security audit) with a different trust model and lifetime.
- **No GPG signing of sync packages.** Separate change (L3).
- **No DMG or sidecar code-signing or notarization.** Deferred to a launch milestone.
- **No structured audit log of handshake outcomes.** Outcomes are logged at `info` via existing `tracing`, not persisted to SQLite or rotated separately.

## Success Criteria

Done when the following are observable on a fresh macOS install:

1. **Squat test.** Bind `nc -l 3939` before launching Squirrel.app. Within ~3 s the tray flips to Error; a banner reads "Another process is using port 3939. Quit it and relaunch Squirrel." No `/api/me`, `/api/home`, or any other API call is issued by the Tauri shell. Verifiable via `tracing` log lines.
2. **Normal launch.** Launch Squirrel.app. Tray flips to Normal after backend health check. `lsof -i :3939` shows the spawned `squirrel-backend` PID. `find ~/.squirrel -name "runtime-token*"` returns nothing — no runtime token on disk.
3. **Dev-backend conflict.** Run `make backend-start` in a terminal. Backend startup log contains `WARN: dev mode, no token auth`. Launch Squirrel.app. Tray flips to Error; banner reads "Detected dev-mode backend on port 3939. Quit `make backend-start` and relaunch Squirrel, or quit Squirrel and use the CLI." Terminal-side backend remains usable for `curl http://127.0.0.1:3939/api/me` etc.
4. **Launchd install path.** Install via the launchd installer (CLI install path). `~/.squirrel/launchd-token` exists, mode `0600`, owner = `$USER`. `launchctl list | grep org.squirrel.web-ui` shows the service running. Launch Squirrel.app. Tray flips to Normal — Tauri adopted the launchd-supervised backend by handshake-verifying with the install-time token.
5. **Tampered launchd-token.** Rewrite `~/.squirrel/launchd-token` to a different value. Restart the launchd backend so it re-reads the file. Relaunch Squirrel.app. Tray flips to Error; banner reads "Backend token mismatch. Reinstall via `install.sh --reinstall` or quit Squirrel." Verifiable via `tracing` log line `handshake refused: token mismatch`.
6. **No token leakage.** Searching the Tauri logs (`~/.squirrel/tauri.log`), the backend logs (`~/.squirrel/web-ui.stdout.log`, `web-ui.stderr.log`), and any response body from `/api/_handshake` (without the matching header) for the hex token value returns zero hits.
