# Runtime Trust Handshake — Low-Level Design

## Architecture

Three components participate:

1. **Tauri shell** (`apps/desktop/src-tauri/src/`) — mints the token, spawns or adopts the backend, makes the adoption decision.
2. **Backend HTTP server** (`apps/backend/server.py`) — receives the token at startup (via argv or token-file), enforces it on every request, answers handshake probes.
3. **Launchd installer** (`apps/backend/launchd/install.sh` + plist template) — writes the install-time `launchd-token` so the launchd-supervised backend can join the trust system.

There are three runtime paths.

### Path A — In-memory token (Tauri-managed flow, the default)

```
Tauri startup
   │
   ▼
rand::rngs::OsRng → 32 random bytes → hex String  (in-memory only)
   │
   ▼
backend_supervisor::spawn_or_adopt
   │
   ├─ port_in_use(3939) == false ───────────────────────────┐
   │                                                        │
   │                                                        ▼
   │                                            tauri::shell.sidecar("squirrel-backend")
   │                                              .args(["--port", "3939", "--token", &hex])
   │                                              .spawn()
   │                                                        │
   │                                                        ▼
   │                                            sidecar reads --token, stores in TOKEN,
   │                                            HTTP listener begins
   │                                                        │
   │                                                        ▼
   │                                            handshake probe matches → Adopted
   │                                            (mode = Managed in supervisor state)
   │
   └─ port_in_use(3939) == true ───────────► Path B (adoption decision)
```

Token never reaches the filesystem. There is no file to race for.

### Path B — Adoption decision (port already taken at Tauri startup)

```
backend_supervisor::spawn_or_adopt detects port 3939 bound
   │
   ▼
read locally-held token T (either Tauri-minted in this process, or read
from ~/.squirrel/launchd-token if present)
   │
   ▼
HTTP GET 127.0.0.1:3939/api/_handshake
  header: X-Squirrel-Token: <T>
  timeout: 3s
   │
   ├─ 200 + {"token_echo": "<T>"} matches  ───► SupervisionMode::Adopted, proceed
   │
   ├─ 200 + {"mode": "dev"}                ───► refuse → tray.Error + banner(DevModeDetected)
   │
   ├─ 401                                   ───► refuse → tray.Error + banner(UnknownProcess)
   │
   ├─ 200 + other shape                     ───► refuse → tray.Error + banner(UnknownProcess)
   │
   ├─ connect/read timeout (3s)             ───► refuse → tray.Error + banner(NotResponding)
   │
   └─ refused → NO API request is ever sent. NO fallback port is attempted.
```

### Path C — Launchd-supervised path (no Tauri parent at backend start)

```
Tauri installer (run once at install time, user-authenticated action)
   │
   ▼
generate 32 random bytes → hex → write to ~/.squirrel/launchd-token
chmod 0600, chown $USER
   │
   ▼
render plist with ProgramArguments including
  ["squirrel-backend", "--port", "3939", "--token-file", "~/.squirrel/launchd-token"]
launchctl bootstrap gui/$UID ~/Library/LaunchAgents/org.squirrel.web-ui.plist
   │
   ▼
squirrel-backend started by launchd at next login (or now via launchctl kickstart)
   │
   ▼
reads --token-file, verifies file mode 0600 + owner = $USER, loads token into TOKEN
HTTP listener begins, requires X-Squirrel-Token on all routes
   │
   ▼
Tauri shell launches later
   │
   ▼
spawn_or_adopt sees port 3939 bound
reads ~/.squirrel/launchd-token (same file the backend read)
runs Path B with that token
match → Adopted; mismatch → Error banner
```

The launchd-token is install-time-provisioned by an authenticated user action, not raced at startup. The user who ran `install.sh` is the trust anchor.

## Constraints

### Cryptographic

- Token MUST be ≥ 256 bits of entropy. Use `rand::rngs::OsRng` on the Rust side, `secrets.token_hex(32)` on the Python side.
- Token comparison MUST be constant-time:
  - Rust: `subtle::ConstantTimeEq::ct_eq` or `hmac::verify`.
  - Python: `hmac.compare_digest`.
- Token format on the wire is **hex string** (64 chars). The argv/`--token-file` representation is also hex. No base64, no binary.
- The handshake endpoint MUST NOT return the token in plaintext when the request lacks the header. Return only `401` with empty body.

### Argv vs. env

- Token MUST be passed via argv (`--token <hex>`), NOT via environment variable.
- Rationale: argv is visible only to the same UID via `ps`. Env additionally leaks via `/proc/<pid>/environ` (Linux) and is inherited by every child process the sidecar later spawns. Both surfaces are visible to the threatened adversary (same-UID process); argv is the smaller leak.
- Sidecar must read `--token` once at startup and discard the argv reference where reasonable (Python: `del sys.argv` after `argparse` parses, or overwrite). This is best-effort defense in depth, not a security guarantee.

### File-system constraints (launchd-token only)

- `~/.squirrel/launchd-token` MUST be `chmod 0600` and owned by the user running the installer.
- Installer MUST fail closed if it cannot achieve those permissions (do not silently write a less-restrictive file).
- Backend MUST verify the file's mode and owner before reading; if either check fails, exit non-zero with a clear stderr message naming the problem.
- File contents are a single line of 64 hex chars + optional trailing `\n`. Anything else is treated as malformed → backend exit non-zero.

### Timing / availability

- Handshake probe budget: **3 seconds total** (connect + send + read). Same as existing `HEALTH_REQ_TIMEOUT` in `backend_supervisor.rs:35`.
- One probe attempt only. No retry, no backoff. The user resolves the conflict and relaunches.
- Adoption refusal is terminal: the tray remains in Error state and no subsequent API call is attempted until the next Tauri restart.

### Logging

- Outcomes logged at `info` via existing `tracing` subscriber: `handshake_attempt` with fields `outcome` (`adopted` / `refused_dev` / `refused_401` / `refused_unknown` / `refused_timeout`), `elapsed_ms`.
- Token value MUST NOT be logged at any level.
- Banner text is rendered in the React shell from a stable event payload emitted by Rust; the Rust side emits a typed enum, the React side maps to localized strings.

## Key Decisions

### D1 — Tauri mints, sidecar receives. Backend never mints.

**Decision:** Tauri is the trust anchor in the in-memory flow. The installer is the trust anchor in the launchd flow. The backend never generates a token of its own.

**Why:** A backend that self-mints can be impersonated by anyone who can listen on :3939 first — they self-mint just as legitimately. The mint authority must be something the user has already authenticated (the signed Tauri app they launched, or the installer they ran with their credentials).

**Rejected alternative:** "Backend self-seeds if file missing." This was the original plan; uncle-senior caught that it inverts H3 by replacing a port race with a file race that the squatter wins identically.

### D2 — Token in memory only for the in-app flow; on disk only for the launchd flow.

**Decision:** The Tauri-managed flow holds the token in process memory and passes it via argv. Nothing is written to disk. The launchd flow writes a single file at install time and never again.

**Why:** Filesystem state at process start is a race surface. Removing the file in the default path closes the race. The launchd flow has no Tauri-at-startup to mint a token, so file-based pre-provisioning is unavoidable — but it can be authenticated by tying it to the install action.

### D3 — Dev-mode backend is explicit, and Tauri refuses to adopt it.

**Decision:** Backend started without `--token` and without `--token-file` runs unauthenticated on loopback, prints a clear `WARN`, and returns `{"mode": "dev"}` from the handshake. Tauri treats this as adopt-refusal and surfaces the dev-mode case in the banner.

**Why:** `make backend-start` is a real workflow for the dogfooding author. The naive design ("no token = silently insecure") would let the GUI adopt the dev backend without the user knowing. The explicit `mode: dev` response makes the situation observable and forces a choice: kill `make backend-start`, or use the CLI/curl path that doesn't need the GUI.

### D4 — No token rotation, no challenge-nonce, no body HMAC.

**Decision:** A 256-bit pre-shared secret compared in constant time is the entire mechanism.

**Why:** The threat is "wrong process on the port", not "active MITM of authenticated requests". Loopback HTTP between two processes the same user owns does not need TLS or HMAC. Adding nonce-challenge or body HMAC adds complexity that buys nothing against the modeled adversary, and risks introducing implementation bugs (timing leaks, replay windows) more dangerous than what they would prevent.

### D5 — Adoption refusal is terminal, no fallback port.

**Decision:** If adoption is refused, the tray stays in Error until the user relaunches. No fallback port, no silent retry, no degraded-mode operation.

**Why:** Anything less surfaces the conflict to the user only weakly and trains them to ignore the tray state. The refusal must be loud enough that the user notices and resolves it.

## Out of Scope

- LAN authentication for `--lan` mode (separate change — M3 in the audit).
- GPG signing of sync packages (separate change — L3).
- DMG and sidecar codesign + notarization (deferred to launch milestone).
- Defense against attackers with UID-level access (read process memory, debugger attach).
- Token rotation during a process lifetime.
- Cross-machine sync of tokens.
- Hardware-backed key storage (Keychain, Secure Enclave). Not warranted at this threat model.
- A persistent structured audit log of every handshake outcome (info-level `tracing` is sufficient).
- Backend-initiated re-handshake or re-key signalling.
