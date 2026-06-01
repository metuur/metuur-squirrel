# Runtime Trust Handshake — Tasks

Source specs: `docs/hld/runtime-trust-handshake.md`, `docs/lld/runtime-trust-handshake.md`, `docs/ears/runtime-trust-handshake.md`.
Story IDs are stable — referenced from `.devlocal/<user>/<story-id>/scratchpad.md` for private notes.

Scope: H3 from the security audit only. The other 5 units in `.devlocal/javier/security-audit.md` (Day-1 sweep, M3 LAN PSK, H2 python3 fix, M1 deep-link confirm, L3 GPG signing) are out of scope for this plan.

Dependency layers:

```
1.1 (Tauri token gen) ──┐
                        ├── 1.2 (sidecar spawn argv)
2.1 (backend argparse + dev mode) ──┐
                                    ├── 2.2 (X-Squirrel-Token enforcement) ──── 3.1 (/api/_handshake)
                                    │
1.2 + 3.1 ─────► 4.1 (probe + adopt-or-refuse) ──► 4.2 (refusal cause events) ──► 6.1 (tray Why? + banner shell) ──► 6.2 (banner copy)
                                                                                                                       │
2.1 ─► 5.1 (installer mints launchd-token) ──► 5.2 (plist --token-file) ──► 5.3 (Tauri reads launchd-token)            │
5.1 + 5.2 ─► 5.4 (install.sh --reinstall)                                                                              │
                                                                                                                       ▼
                                                                                                                      7.1 (smoke test)
```

Mutex tags:
- `(mutex: supervisor)` — 1.2 and 4.1 both modify `apps/desktop/src-tauri/src/backend_supervisor.rs`. Sequence them or rebase carefully.
- `(mutex: server-routes)` — 2.2 and 3.1 both add to `apps/backend/server.py` request dispatch (`ROUTES` list and `_dispatch`). Sequence them.

## Unit 1: Tauri token minting

- [x] **1.1** Generate per-launch token at Tauri startup (est: ~30m)
  - acceptance:
    - R-1.1 — WHEN the Tauri shell starts, generate a 32-byte token via `rand::rngs::OsRng`.
    - R-1.2 — Token held in process memory only; no disk write from the Tauri runtime path.
    - R-1.5 — Hex-encoded (64 ASCII chars) for wire/argv use.
  - touchpoints:
    - `apps/desktop/src-tauri/Cargo.toml` — add `rand = "0.8"` (and `subtle = "2"` for later 4.x stories).
    - `apps/desktop/src-tauri/src/backend_supervisor.rs` — add `pub(crate) fn mint_runtime_token() -> String` returning 64-char hex.
    - `apps/desktop/src-tauri/src/lib.rs` — add `RuntimeToken(pub(crate) String)` state struct and `.manage(...)` it before `spawn_or_adopt` runs.
  - verify:
    - `cargo test -p squirrel mint_runtime_token` — unit test that asserts length == 64, all chars `[0-9a-f]`, and two consecutive calls yield different values.
    - `cargo build` succeeds.
  - skip TDD; run the verify block as the test (scaffolding story).

- [x] **1.2** Pass `--token <hex>` to sidecar spawn (deps: 1.1, est: ~30m) `(mutex: supervisor)`
  - acceptance:
    - R-1.3 — Sidecar receives the token via `--token <hex>` argv argument.
    - R-1.4 — Token MUST NOT be added to any env var passed to the child.
  - touchpoints:
    - `apps/desktop/src-tauri/src/backend_supervisor.rs:82-89` — extend `cmd.args([...])` with `["--token", &token]`. Read token from the managed `RuntimeToken` state.
  - verify:
    - Add an `assert!(!format!("{:?}", cmd).contains("env"))` test, OR run the app and inspect the spawned child's argv via `ps -ww -p $(lsof -ti :3939)` — must show `--token <hex>`.
    - Inspect `env | grep -i squirrel` from inside the spawned backend (temporary debug log in `server.py`) — must NOT contain the token value.
  - skip TDD; verify block is the test.

## Unit 2: Backend token acceptance

- [x] **2.1** Add `--token`/`--token-file` argparse and dev-mode warning (est: ~45m)
  - acceptance:
    - R-2.1 — `--token <hex>` loads token into module-level `TOKEN` constant for process lifetime.
    - R-2.2 — `--token-file <path>` reads single line of hex, verifies file is mode `0600` and owned by `os.geteuid()`.
    - R-2.3 — Bad token-file (missing, wrong mode, wrong owner, malformed content) → `sys.exit(2)` with stderr message naming the failed check.
    - R-2.4 — Both `--token` and `--token-file` → `sys.exit(2)` with mutex error message.
    - R-2.5 — Neither flag → dev mode: `logging.getLogger("squirrel.server").warning("dev mode, no token auth")` and set `DEV_MODE = True`.
  - touchpoints:
    - `apps/backend/server.py:1752-1770` (`main()`) — add the three mutually exclusive arguments.
    - `apps/backend/server.py` near `DEFAULT_HOST` (line 60 area) — add `TOKEN: Optional[str] = None` and `DEV_MODE: bool = False` module-level constants.
    - New helper `_load_token_from_file(path: pathlib.Path) -> str` co-located with argparse.
  - verify:
    - `pytest apps/cli/tests/test_web_ui_server.py -k token` — new tests covering all five branches.
    - Manual: `python apps/backend/server.py --token deadbeef…` (64 chars) → no warning; `--token X --token-file Y` → exits 2; no flags → "dev mode" warning on stderr.

- [x] **2.2** Enforce `X-Squirrel-Token` on every non-handshake route (deps: 2.1, est: ~60m) `(mutex: server-routes)`
  - acceptance:
    - R-2.6 — Reject `401` empty body when header missing/mismatched AND NOT dev mode AND route != `/api/_handshake`.
    - R-2.7 — Comparison via `hmac.compare_digest`.
    - R-2.8 — While `DEV_MODE` is True, this enforcement is bypassed.
    - R-2.9 — Token value never appears in any log line, response body, or exception message.
  - touchpoints:
    - `apps/backend/server.py:390-416` (`_dispatch`) — add token check immediately after `is_safe_request_path` and before `ROUTES` walk. Skip when `bare == "/api/_handshake"` (handshake handler enforces its own contract per R-3.1/R-3.2).
    - Static asset routes (`/assets/`, `/icons/`, `/favicon*`, `/squirrel.svg`, `/manifest.json`, SPA shell) — decide: also gated by token, or not? **Decision:** also gated. The threat is impersonation of *any* backend response. Bypass would let a squatter serve a hostile React bundle.
    - Add a tracing log line at refusal with NO token value: `_log_request("X", path, 401)`.
  - verify:
    - `pytest apps/cli/tests/test_web_ui_server.py -k auth` — new tests: missing header → 401; bad header → 401; right header → 200; dev mode → 200 either way; `/api/_handshake` always reachable.
    - `grep -r "$TOKEN_VALUE_FROM_TEST" ~/.squirrel/*.log` after a refused request must return zero hits.

## Unit 3: Handshake endpoint

- [x] **3.1** Add `GET /api/_handshake` handler (deps: 2.1, 2.2, est: ~30m) `(mutex: server-routes)`
  - acceptance:
    - R-3.1 — Matching header → `200 {"token_echo": "<hex>"}`.
    - R-3.2 — Missing/mismatched header AND not dev mode → `401` empty body.
    - R-3.3 — Dev mode → `200 {"mode": "dev"}` regardless of header.
    - R-3.4 — No body path leaks the stored token to a non-matching caller.
    - R-3.5 — < 1s response under normal conditions (handler is constant-work; satisfied trivially).
  - touchpoints:
    - `apps/backend/server.py:272-329` (`ROUTES` table) — register `("GET", re.compile(r"^/api/_handshake$"), "api_handshake")` BEFORE the SPA shell wildcard route.
    - Add `def api_handshake(self) -> None:` method on `Handler`.
    - The Unit 2 enforcement code added in 2.2 must exempt `/api/_handshake` so the handler can run its own logic.
  - verify:
    - `pytest apps/cli/tests/test_web_ui_server.py -k handshake` — six tests covering the cross-product of {has header, missing, mismatch} × {dev mode, normal}.
    - Manual: `curl -i http://127.0.0.1:3939/api/_handshake` → 401 in normal mode; with correct header → 200 + `token_echo`.

## Unit 4: Tauri adoption decision

- [x] **4.1** Replace `port_in_use → Adopted` with `port_in_use → probe + verify-or-refuse` (deps: 1.1, 3.1, est: ~90m) `(mutex: supervisor)`
  - acceptance:
    - R-4.1 — On `port_in_use(3939) == true`, issue `GET /api/_handshake` with `X-Squirrel-Token: <runtime_token>` within 3 s.
    - R-4.2 — `200` with constant-time-equal `token_echo` → `SupervisionMode::Adopted`.
    - R-4.7 — On refusal, no API request is ever sent for the lifetime of this Tauri process.
    - R-4.8 — No fallback port.
    - R-4.9 — No attempt to spawn a sidecar to displace the squatter.
    - R-4.10 — Log `handshake_attempt` at `info` with `outcome` and `elapsed_ms` fields.
  - touchpoints:
    - `apps/desktop/src-tauri/src/backend_supervisor.rs:117-134` (`spawn_or_adopt`) — rewrite the `if port_in_use(...) { return Adopted; }` block to call a new `probe_handshake(&app, &token) -> HandshakeOutcome` helper.
    - New enum `HandshakeOutcome { Adopted, RefusedDev, Refused401, RefusedUnknown, RefusedTimeout }`.
    - New `SupervisionMode::RefusedAdoption(HandshakeOutcome)` variant — separate from `Failed` so the tray banner can distinguish "spawn failed" from "refused adoption".
    - Use the existing `reqwest::blocking::Client` pattern at the top of `backend_supervisor.rs` (or `tokio` if the call site is async — confirm at code time).
    - Constant-time compare with `subtle::ConstantTimeEq`.
  - verify:
    - Unit test in `backend_supervisor.rs`: mock the HTTP call and assert each branch maps to the right `HandshakeOutcome`.
    - Manual: `nc -l 3939 &` then launch Squirrel — must NOT issue `/api/me` or any other call (verify by watching netcat's stdout — only the `/api/_handshake` request appears, nothing else).

- [x] **4.2** Emit typed refusal-cause events on adoption refusal (deps: 4.1, est: ~30m)
  - acceptance:
    - R-4.3 — `mode: dev` response → emit `handshake-refused` with payload `{"cause": "DevModeDetected"}`.
    - R-4.4 — `401` → `{"cause": "UnknownProcess"}`.
    - R-4.5 — `200` with unrecognized body → `{"cause": "UnknownProcess"}`.
    - R-4.6 — Timeout → `{"cause": "NotResponding"}`.
  - touchpoints:
    - `apps/desktop/src-tauri/src/backend_supervisor.rs` — after `RefusedAdoption(outcome)` is set, call `app.emit("handshake-refused", payload)` and `tray::set_state(app, IconState::Error)`.
    - New `#[derive(Serialize)] struct HandshakeRefusalPayload { cause: &'static str }` co-located with the enum.
    - `apps/desktop/src-tauri/src/tray.rs` — confirm `IconState::Error` is already wired (it is, per existing tray tests).
  - verify:
    - Manual: drive each of the 4 refusal causes (nc squat, dev backend, timeout via slow nc, malformed response via a one-line python http server) and confirm the React side receives the right cause string in dev console.

## Unit 5: Launchd-supervised path

- [x] **5.1** Installer mints `~/.squirrel/launchd-token` with chmod 0600 (deps: 2.1, est: ~30m)
  - acceptance:
    - R-5.1 — Generate 32 bytes from `openssl rand -hex 32`, write to `~/.squirrel/launchd-token`, `chmod 600`, owner = `$USER`. Token value NEVER printed to stdout/stderr.
    - R-5.2 — If file already exists at install time AND passes R-2.3 checks, preserve it; if it exists but fails R-2.3 checks, exit non-zero with a clear message.
  - touchpoints:
    - `apps/backend/launchd/install.sh:60-68` — add token generation step BEFORE the sed substitution that writes the plist.
    - Add helper function `ensure_launchd_token()` returning path; abstracts the check-or-create logic.
    - Add a `_verify_token_file_permissions()` shared with backend (or implement same checks in bash with `stat -f "%Lp"` for mode and `stat -f "%Su"` for owner on macOS).
  - verify:
    - Run `bash apps/backend/launchd/install.sh` on a clean `~/.squirrel/`: file exists, `stat -f "%Lp %Su" ~/.squirrel/launchd-token` returns `600 $USER`.
    - Run installer second time: file is unchanged (compare sha256 before/after).
    - `pre-test:` `chmod 0644 ~/.squirrel/launchd-token`, run installer → exits non-zero with message naming the permission failure.

- [x] **5.2** Plist template includes `--token-file` argument (deps: 5.1, est: ~15m)
  - acceptance:
    - R-5.3 — `ProgramArguments` array in rendered plist includes `--token-file` followed by the absolute path to `~/.squirrel/launchd-token`.
  - touchpoints:
    - `apps/backend/launchd/plist.template` — add two new `<string>` entries: `<string>--token-file</string><string>__TOKEN_FILE__</string>` after `__PORT__`.
    - `apps/backend/launchd/install.sh:64-68` — add `-e "s|__TOKEN_FILE__|$HOME/.squirrel/launchd-token|g"` to the sed pipeline.
  - verify:
    - `bash install.sh && cat ~/Library/LaunchAgents/org.squirrel.web-ui.plist | grep token-file` returns the substituted absolute path.
    - `launchctl unload && launchctl load` → backend stderr log contains no "dev mode" warning.
  - skip TDD; verify block is the test (template substitution).

- [ ] **5.3** Tauri reads `~/.squirrel/launchd-token` when port is bound and file exists (deps: 1.1, 4.1, 5.1, est: ~30m)
  - acceptance:
    - R-5.4 — When `spawn_or_adopt` finds the port bound AND `~/.squirrel/launchd-token` exists AND passes the R-2.3 file checks, use that token (instead of the in-memory runtime token) for the handshake probe.
    - R-5.5 — File exists but fails checks → emit `handshake-refused` with `{"cause": "LaunchdTokenInvalid"}` and refuse adoption.
  - touchpoints:
    - `apps/desktop/src-tauri/src/backend_supervisor.rs` — extend the new probe path from 4.1: before probing, try to read launchd-token; on read success, prefer it; on read failure with file present, refuse.
    - Add helper `read_launchd_token() -> Result<Option<String>, LaunchdTokenError>`. `None` = file absent (legitimate, fall through to in-memory token). `Err` = file present but invalid.
  - verify:
    - Manual three-way test:
      - No `~/.squirrel/launchd-token`, no port squatter → spawns sidecar (existing Managed flow).
      - Valid launchd-token + launchd backend running → adopts.
      - Tampered launchd-token (`echo "garbage" > ~/.squirrel/launchd-token`) → tray Error + LaunchdTokenInvalid banner.

- [ ] **5.4** `install.sh --reinstall` regenerates token and re-bootstraps service (deps: 5.1, 5.2, est: ~30m)
  - acceptance:
    - R-5.6 — `bash install.sh --reinstall`: regenerate `~/.squirrel/launchd-token`, rewrite plist, `launchctl bootout` then `launchctl bootstrap` so the running backend picks up the new token at process restart.
  - touchpoints:
    - `apps/backend/launchd/install.sh:13-30` — add `--reinstall` to the arg parser. Should not exit on the existing `Unknown argument` branch.
    - New `do_reinstall()` function: shred the existing token file (`rm -f`) before re-running `ensure_launchd_token`.
    - Use `launchctl bootout gui/$UID …` + `launchctl bootstrap gui/$UID …` (modern API, not deprecated `unload`/`load`).
  - verify:
    - Capture sha256 of `~/.squirrel/launchd-token` before; run `install.sh --reinstall`; sha256 differs after.
    - `launchctl list | grep org.squirrel.web-ui` still shows the service running post-reinstall.
    - Tauri shell launched against post-reinstall backend: tray Normal (Tauri reads the same fresh token and handshake succeeds).

## Unit 6: User-visible state and recovery

- [ ] **6.1** Tray "Why?" item + window-blocking banner shell (deps: 4.2, est: ~45m)
  - acceptance:
    - R-6.1 — When tray is in Error state due to refused adoption, the tray menu shows a "Why?" item that triggers showing the dashboard with the banner.
    - R-6.2 — While the tray is in Error state from refused adoption, the dashboard renders the banner above all other content, with a "Quit Squirrel" button as the primary action.
  - touchpoints:
    - `apps/desktop/src-tauri/src/tray.rs` — append a conditional "Why?" `MenuItem` to the tray menu when `IconState == Error` and the cause is `RefusedAdoption`. Wire its `on_event` to `tray::show_main_window(app)` + emit `handshake-refused` payload again.
    - `apps/desktop/src-tauri/Cargo.toml` — already has `tauri-plugin-process` for the Quit button (see existing `BackendStatusBanner` story per `Cargo.toml:27`).
    - `apps/desktop/src/components/HandshakeBanner.tsx` (new) — React banner component that listens for `handshake-refused`, shows banner above all routed content, includes Quit button calling `tauri-plugin-process` restart-app helper.
    - `apps/desktop/src/App.tsx` or layout root — mount `<HandshakeBanner />` at the top level so it covers every route.
  - verify:
    - Manual: drive a refusal cause (e.g. nc squat); tray menu shows "Why?"; clicking it opens the dashboard with the banner above content; the rest of the dashboard is visually inaccessible until Quit is clicked.

- [ ] **6.2** Banner copy for each refusal cause (deps: 6.1, est: ~30m)
  - acceptance:
    - R-6.3 — `DevModeDetected`: identify `make backend-start` as likely source; offer (a) quit dev backend + relaunch, or (b) quit Squirrel + use CLI.
    - R-6.4 — `UnknownProcess`: suggest running `lsof -i :3939` to identify the squatter.
    - R-6.5 — `NotResponding`: suggest wait 30s + relaunch, then check `~/.squirrel/web-ui.stderr.log`.
    - R-6.6 — `LaunchdTokenInvalid`: recommend running `install.sh --reinstall`.
  - touchpoints:
    - `apps/desktop/src/components/HandshakeBanner.tsx` — switch on the `cause` payload field, render the four message bodies. Include the actual shell commands in inline `<code>` blocks; use the existing `material-icons` package for the warning icon (consistent with `apps/backend/app/src/pages/NotePage.tsx:21`).
    - No i18n required (project is currently single-locale).
  - verify:
    - Manual: drive each of the four causes, confirm banner text matches the spec, copy is readable, command snippets are copy-pasteable.
  - skip TDD; verify block is the test (UI copy).

## Unit 7: End-to-end verification

- [ ] **7.1** Walk the six Success Criteria from `docs/hld/runtime-trust-handshake.md` on a fresh macOS install (deps: 6.2, 5.4, est: ~45m)
  - acceptance: each of the six bullets in the HLD Success Criteria section reproduces as written.
  - verify (the six checks themselves):
    1. **Squat test:** `nc -l 3939 &`; launch Squirrel.app; within 3 s tray = Error, banner = UnknownProcess; `grep handshake_attempt ~/.squirrel/tauri.log` shows outcome=refused_unknown.
    2. **Normal launch:** kill the squatter; launch Squirrel.app; tray → Normal; `lsof -i :3939` shows the sidecar PID; `find ~/.squirrel -name "runtime-token*"` returns zero hits.
    3. **Dev-backend conflict:** `cd apps/backend && python server.py` (no flags); launch Squirrel.app; tray Error; banner = DevModeDetected; the literal `make backend-start` appears in the message.
    4. **Launchd install path:** uninstall Squirrel.app; `bash apps/backend/launchd/install.sh`; verify `~/.squirrel/launchd-token` is 0600 + owner; `launchctl list | grep org.squirrel.web-ui` running; launch Squirrel.app; tray Normal.
    5. **Tampered launchd-token:** `echo "garbage" > ~/.squirrel/launchd-token`; `launchctl kickstart -k gui/$UID/org.squirrel.web-ui` to force re-read; launch Squirrel.app; tray Error; banner = LaunchdTokenInvalid; copy mentions `install.sh --reinstall`.
    6. **No token leakage:** run a refused-adoption flow with a known test token in argv; `grep "<test-token>" ~/.squirrel/*.log ~/.squirrel/launchd-token` (excluding the legit `launchd-token` if present) returns zero hits.
  - On all-pass: append a one-line dated note in `.uncle-dev/learns/runtime-trust-handshake.md` documenting what was verified and on what macOS version.

## Cross-cutting notes

- **No new external deps beyond `rand`, `subtle` (Rust) and `secrets`, `hmac` (Python stdlib — already available).**
- **Test fixtures:** new test token used in pytest should be a hex string like `"0" * 64` for readability; production code paths must continue to use CSPRNG.
- **Backwards compat:** existing CLI users who don't reinstall will continue running an `--token`-less backend (dev mode). The GUI refuses to adopt it — they get a banner and a clear next step. This is intentional per the LLD's D3 decision.
- **Effort total:** ~7.5–8 hours of focused work. Uncle-lead's revised estimate was 1 day for H3 alone. Matches.
