# Harden Backend Lifecycle + Caching — High-Level Design

## Overview

Three independent stability/performance risks in the Phase 2 posture compound into one user-visible failure mode: **the app appears to run but silently shows nothing**. This change hardens the desktop lifecycle and cuts per-poll work so that installing the DMG and launching Squirrel "just works" without a terminal, and so the 30 s tray poll stops re-scanning the vault three times and re-opening SQLite on every cycle.

The three fixes ship as one rollout because they interact — hardened supervision pushes the backend through more `/api/home` cycles, which makes the scan cache more valuable:

1. **Backend supervision (sidecar).** The Tauri app spawns-or-adopts the bundled `squirrel-backend` binary, health-checks it on the existing 30 s heartbeat, respawns within bounds, and surfaces a **visible error state** instead of an empty tray when the backend can't be located.
2. **Vault-scan TTL cache.** A process-local cache in the Python backend wraps the three independent vault scanners (`aggregate_status`, `scan_vault_deadlines`, `scan_vault_reminders`) behind a 25 s TTL with write-path invalidation, replacing ~900 file reads / 30 s with one scan per TTL boundary.
3. **Cached SQLite connection.** The Rust tray poller borrows one cached `rusqlite::Connection` (WAL + `busy_timeout`) for every notification helper instead of opening a fresh connection per call.

The detailed contract lives in `docs/lld/harden-backend-lifecycle-and-caching.md`. The EARS for this work are **R-9.1–R-9.13 in `docs/ears/phase-2-data-plane-and-desktop-popup.md` (Unit 9)** — deliberately folded into the Phase 2 EARS file because they **supersede R-1.7 and R-7.1** (which forbade Tauri-side backend supervision); this HLD does not introduce a separate EARS file.

## Stakeholders & Impact

- **Primary user (ADHD knowledge worker):** today a DMG installer with no launchd plist yields a tray icon whose menus are permanently empty, with no on-screen explanation. After this ships they install the DMG, launch Squirrel, and within ~10 s get a working tray — no `make backend-start`, no plist, no terminal. When the backend genuinely can't start, they see "Backend unavailable" instead of silence.
- **Power users running launchd / `make backend-start`:** unaffected — the supervisor detects a backend already bound to `127.0.0.1:3939` and **adopts** it (monitors only, never double-spawns, never kills the externally-managed process on quit).
- **Backend HTTP thread:** stops blocking on ~900 file reads every 30 s; `/api/home` median latency drops by ≥50% on a 300-file vault via the TTL cache.
- **Rust tray state:** SQLite churn goes from N connection opens per poll cycle to one open per app lifetime.

## Goals

- The user can install the DMG and get a working tray **without touching a terminal, ever**.
- `/api/home` median latency drops by **≥50%** on a 300-file vault.
- SQLite churn in the tray poller goes from N opens per cycle to **one open per app lifetime**.
- The "silent empty tray" failure mode is replaced by a **visible error state**.
- No new external dependencies beyond what `tauri-plugin-shell` adds on the Rust side and the stdlib-only cache on the Python side.

## Non-Goals

- No re-architecting of the polling model — still 30 s, still HTTP, still tray-pulled. No push notifications, websockets, or a Rust-native scanner.
- No change to the bundle format — still PyInstaller `--onefile`.
- macOS only this round; Linux/Windows lifecycle is a separate LLD.
- No auth/CSP changes — still localhost-only.
- No mtime-based incremental indexing — TTL + write invalidation only (incremental indexing is deferred to a future LLD for very large vaults).

## Success Criteria

1. **Fresh-install smoke:** on a Mac with no launchd plist, installing the new DMG and launching Squirrel brings the tray icon to Normal within 10 s and populates "PRESSING NOW" within 30 s; `ps aux | grep squirrel-backend` shows one child owned by the Squirrel app.
2. **Clean shutdown:** quitting via tray → "Quit Squirrel" removes the `squirrel-backend` child within ~3 s (SIGTERM → SIGKILL escalation).
3. **Adoption:** with a launchd-managed backend running, launching Squirrel goes into Adopted mode; quitting Squirrel does **not** kill the launchd backend.
4. **Self-heal:** `kill -9` the backend child → within ~90 s the tray flips to Error and a respawn occurs within bounds (≤5 respawns/hour, 60 s cooldown).
5. **Cache hit-rate:** `curl http://127.0.0.1:3939/api/cache/stats` shows `hit_rate` climbing toward 1.0 within ~2 minutes; a note write is reflected on the next poll (write-path invalidation).
6. **SQLite reuse:** the tray poller opens the notifications DB once at startup and reuses it; sys-time (file opens) on the Tauri process drops.
