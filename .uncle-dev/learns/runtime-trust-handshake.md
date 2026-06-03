# Runtime Trust Handshake — verification log

Feature: H3 from the security audit. Specs in `docs/{hld,lld,ears,tasks}/runtime-trust-handshake.md`.

## 2026-06-01 — Units 1–6 implemented and verified; 7.1 walked (macOS 26.5, arm64)

All 13 implementation stories (1.1–6.2) landed with green tests:
- **Rust** (`apps/desktop/src-tauri`): 74 lib tests pass. Token minting, raw-TCP
  adoption probe + constant-time classification, RefusedAdoption supervision
  mode, R-4.7 health-probe suppression, launchd-token reading, refusal-cause
  events, tray "Why?" item.
- **Python** (`apps/backend/server.py`): 37 of 38 `test_web_ui_server.py` pass
  (the 1 failure, `test_delete_returns_405`, is **pre-existing and unrelated** —
  confirmed by stashing the feature branch; a DELETE-routing expectation, not
  handshake code). Covers token/token-file argparse, dev mode, X-Squirrel-Token
  enforcement, and the `/api/_handshake` contract.
- **Frontend** (`apps/desktop`): `tsc --noEmit` clean; 14 vitest pass. New
  `HandshakeBanner` with per-cause recovery copy.

### Automated end-to-end evidence (protocol + filesystem layers)

Ran a real `server.py` on a scratch port and exercised the wire contract:
- normal mode: `GET /` and `/api/_handshake` without the header → **401 empty
  body**; with the matching header → **200**, `/api/_handshake` echoes the exact
  token; wrong header → **401** (Success Criteria 1, 2, 6 — backend layer).
- dev mode (no flags): `GET /` → 200; `/api/_handshake` → `{"mode":"dev"}`
  (Criterion 3 — backend layer).
- no token leakage: the hex token appears in **zero** log lines (Criterion 6).
- launchd installer (isolated `HOME`, stubbed `launchctl`): mints
  `~/.squirrel/launchd-token` at **mode 0600, owner $USER, 64 hex**; idempotent
  on re-run; aborts on bad perms; `--reinstall` regenerates the token and fires
  `launchctl bootout` + `bootstrap` (Criterion 4 — file layer; Criterion 5 — token
  rewrite path).

Caught + fixed along the way: Homebrew **GNU coreutils `stat`** on PATH shadows
BSD `stat`, breaking `stat -f`. The installer now calls `/usr/bin/stat`
explicitly (macOS-only script, so BSD stat is guaranteed).

### Still requires a human on a fresh macOS install (GUI-observable only)

The six HLD Success Criteria include tray-icon-flip and banner-render
observations against the built `Squirrel.app`, which cannot be observed
headlessly. Remaining manual sign-off, using the built app:
1. `nc -l 3939` then launch → tray Error + UnknownProcess banner within ~3 s;
   `grep handshake_attempt ~/.squirrel/*.log` shows `outcome=refused_unknown`
   and **no** `/api/me` line.
2. Clean launch → tray Normal; `lsof -i :3939` = sidecar PID;
   `find ~/.squirrel -name 'runtime-token*'` empty.
3. `make backend-start` then launch → tray Error + DevModeDetected banner naming
   `make backend-start`.
4. `bash apps/backend/launchd/install.sh` then launch → tray Normal (adopted).
5. Tamper `~/.squirrel/launchd-token`, `launchctl kickstart -k`, relaunch → tray
   Error + LaunchdTokenInvalid banner mentioning `install.sh --reinstall`.
6. Confirm the token is absent from `~/.squirrel/*.log` after a refused flow.

Note: implemented banner copy follows the **EARS** wording (R-6.3..R-6.6), which
is more detailed than the HLD's illustrative example sentences (names the exact
recovery command + offers the choices). Treat EARS as authoritative.
