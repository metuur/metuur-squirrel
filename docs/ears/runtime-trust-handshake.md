# Runtime Trust Handshake — EARS Specifications

## Unit 1: Token minting and storage (Tauri side)

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | WHEN the Tauri shell starts, THE SYSTEM SHALL generate a 32-byte random token using a cryptographically secure RNG (`rand::rngs::OsRng` or equivalent). |
| R-1.2 | THE SYSTEM SHALL hold the runtime token in process memory only — it SHALL NOT be written to disk by the Tauri shell at runtime. |
| R-1.3 | WHEN the Tauri shell spawns the bundled sidecar, THE SYSTEM SHALL pass the token via the `--token <hex>` argv argument. |
| R-1.4 | THE SYSTEM SHALL NOT pass the runtime token via environment variables to any child process. |
| R-1.5 | THE SYSTEM SHALL hex-encode the token (64 ASCII characters) on the wire and in argv. No other encoding is permitted. |

## Unit 2: Token acceptance and enforcement (sidecar side)

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | WHEN the backend starts with `--token <hex>`, THE SYSTEM SHALL store the token in memory for the lifetime of the process. |
| R-2.2 | WHEN the backend starts with `--token-file <path>`, THE SYSTEM SHALL read a single line of hex from the file, verify the file is owned by the running user and has mode `0600`, and store the token in memory. |
| R-2.3 | IF the file referenced by `--token-file` is missing, not owned by the running user, not mode `0600`, or does not contain exactly 64 hex characters (optionally trailing `\n`), THE SYSTEM SHALL exit non-zero with a clear stderr message naming the specific check that failed. |
| R-2.4 | IF both `--token` and `--token-file` are provided, THE SYSTEM SHALL exit non-zero with a clear stderr message; the two flags are mutually exclusive. |
| R-2.5 | WHEN the backend starts with neither `--token` nor `--token-file`, THE SYSTEM SHALL enter dev mode: log `WARN: dev mode, no token auth` at startup at `warning` level via the existing `logging` subscriber and serve loopback requests without authentication. |
| R-2.6 | WHEN a request to any route other than `GET /api/_handshake` is received AND the backend is NOT in dev mode, THE SYSTEM SHALL reject the request with HTTP `401` and empty body unless the `X-Squirrel-Token` request header value matches the stored token. |
| R-2.7 | THE SYSTEM SHALL compare the `X-Squirrel-Token` value to the stored token in constant time (`hmac.compare_digest` on the Python side, `subtle::ConstantTimeEq` or `hmac::verify` on the Rust side). |
| R-2.8 | WHILE the backend is in dev mode, R-2.6 and R-2.7 SHALL NOT apply; loopback requests SHALL be served regardless of header presence. |
| R-2.9 | THE SYSTEM SHALL NOT log the stored token value at any log level, in any error message, or in any response body. |

## Unit 3: Handshake endpoint contract

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | WHEN `GET /api/_handshake` is received AND the `X-Squirrel-Token` header value matches the stored token AND the backend is NOT in dev mode, THE SYSTEM SHALL respond `200 {"token_echo": "<hex>"}` where `<hex>` is exactly the stored token. |
| R-3.2 | WHEN `GET /api/_handshake` is received AND the `X-Squirrel-Token` header is missing or non-matching AND the backend is NOT in dev mode, THE SYSTEM SHALL respond `401` with empty body. |
| R-3.3 | WHEN `GET /api/_handshake` is received AND the backend is in dev mode, THE SYSTEM SHALL respond `200 {"mode": "dev"}` regardless of header presence or value. |
| R-3.4 | THE SYSTEM SHALL NOT include the stored token in any response body for any request lacking the matching header. |
| R-3.5 | THE SYSTEM SHALL respond to `GET /api/_handshake` within 1 second of receipt under normal conditions. |

## Unit 4: Adoption decision (Tauri side)

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | WHEN the Tauri backend supervisor detects that TCP port 3939 is already bound at startup, THE SYSTEM SHALL probe `GET /api/_handshake` against `127.0.0.1:3939` with header `X-Squirrel-Token: <hex>` set to the locally-held token within a 3-second total timeout (connect + send + read). |
| R-4.2 | IF the probe response is HTTP `200` with body `{"token_echo": "<hex>"}` where the echoed value equals the locally-held token (constant-time compared), THE SYSTEM SHALL enter `SupervisionMode::Adopted` and proceed with normal operation. |
| R-4.3 | IF the probe response is HTTP `200` with body containing the field `"mode": "dev"`, THE SYSTEM SHALL refuse adoption, set the tray icon to `Error`, and emit an event tagged `DevModeDetected` to the React shell for banner rendering. |
| R-4.4 | IF the probe response is HTTP `401`, THE SYSTEM SHALL refuse adoption, set the tray icon to `Error`, and emit an event tagged `UnknownProcess` to the React shell for banner rendering. |
| R-4.5 | IF the probe response is HTTP `200` with a body shape matching neither R-4.2 nor R-4.3, THE SYSTEM SHALL refuse adoption, set the tray icon to `Error`, and emit an event tagged `UnknownProcess`. |
| R-4.6 | IF the probe connect, send, or read exceeds the 3-second budget, THE SYSTEM SHALL refuse adoption, set the tray icon to `Error`, and emit an event tagged `NotResponding`. |
| R-4.7 | WHEN Tauri refuses adoption, THE SYSTEM SHALL NOT issue any subsequent API request to `127.0.0.1:3939` for the lifetime of the Tauri process. |
| R-4.8 | WHEN Tauri refuses adoption, THE SYSTEM SHALL NOT attempt to bind a fallback TCP port. |
| R-4.9 | WHEN Tauri refuses adoption against a listener that is NOT a self-owned orphaned sidecar (see R-4.11), THE SYSTEM SHALL NOT spawn a new sidecar in an attempt to displace the existing listener. |
| R-4.10 | THE SYSTEM SHALL log every handshake outcome (`adopted`, `refused_dev`, `refused_401`, `refused_unknown`, `refused_timeout`) at `info` level via the existing `tracing` subscriber with fields `outcome` and `elapsed_ms`. |
| R-4.11 | WHEN the handshake outcome is `refused_401`, `refused_unknown`, or `refused_timeout`, AND the process bound to port 3939 is verifiably one of Squirrel's own `squirrel-backend` executables that the Tauri process is permitted to terminate (i.e. a self-owned orphan from a prior launch), THE SYSTEM SHALL terminate that process (`SIGKILL`), wait up to 2 seconds for the port to free, and then spawn a fresh `Managed` sidecar. This reclaim SHALL NOT apply to `refused_dev` (a deliberate `make backend-start`) nor to `refused_launchd_token`. |
| R-4.12 | IF the process bound to port 3939 is NOT identifiable as a self-owned `squirrel-backend` (a foreign listener) or cannot be terminated by the Tauri process, THE SYSTEM SHALL preserve the refusal behavior of R-4.7/R-4.8/R-4.9 (no displacing kill, no fallback port, no further requests) and surface the refusal banner. |

## Unit 5: Launchd-supervised path (installer + on-disk token)

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | WHEN the Tauri installer runs for the first time on a machine, THE SYSTEM SHALL generate a 32-byte random token (CSPRNG), write it to `~/.squirrel/launchd-token` with mode `0600` and owner equal to the running user, and SHALL NOT print the token to any output stream. |
| R-5.2 | IF `~/.squirrel/launchd-token` already exists at install time, THE SYSTEM SHALL preserve the existing value (no overwrite) provided it passes the file checks in R-2.3; otherwise the installer SHALL exit non-zero with a clear message. |
| R-5.3 | THE SYSTEM SHALL render the launchd plist `ProgramArguments` to include `["--token-file", "<absolute-path-to>/.squirrel/launchd-token"]`. |
| R-5.4 | WHEN the Tauri shell launches and finds port 3939 bound, AND `~/.squirrel/launchd-token` exists and satisfies the R-2.3 checks, THE SYSTEM SHALL use the token from that file for the adoption probe defined in R-4.1. |
| R-5.5 | IF `~/.squirrel/launchd-token` exists but fails the R-2.3 checks (permissions, ownership, format), THE SYSTEM SHALL refuse to use it and SHALL emit an event tagged `LaunchdTokenInvalid` to the React shell for banner rendering. Adoption is refused. |
| R-5.6 | WHEN the user runs `install.sh --reinstall`, THE SYSTEM SHALL regenerate `~/.squirrel/launchd-token`, rewrite the plist, and re-bootstrap the launchd service so the running backend re-reads the new token. |
| R-5.7 | WHEN the Tauri shell enters `SupervisionMode::Adopted` against a backend whose adoption probe (R-4.1) succeeded under a token other than this launch's minted runtime token (i.e. the launchd token per R-5.4), THE SYSTEM SHALL promote that token to the effective token used by every subsequent client request — the webview (`runtime_token`), the web-UI launch URL (`open_web_url`), and the health/alert pollers — so all `X-Squirrel-Token` headers match the adopted backend. Absent this promotion, every `/api/*` call returns HTTP `401` and pages render empty. |

## Unit 6: User-visible state and recovery

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | WHEN the tray icon is in `Error` state due to a refused adoption, the tray menu SHALL display a "Why?" item that opens the banner with the refusal cause and the recovery instructions. |
| R-6.2 | WHILE the tray is in `Error` state due to refused adoption, the dashboard window SHALL display the banner above all other content with a "Quit Squirrel" button as the primary action. |
| R-6.3 | WHEN the refusal cause is `DevModeDetected`, THE SYSTEM SHALL include in the banner the literal text identifying `make backend-start` as the likely source and offering the choice of (a) quit the dev backend and relaunch Squirrel, or (b) quit Squirrel and continue using the CLI. |
| R-6.4 | WHEN the refusal cause is `UnknownProcess`, THE SYSTEM SHALL include in the banner the suggestion to run `lsof -i :3939` from a terminal to identify the squatter. |
| R-6.5 | WHEN the refusal cause is `NotResponding`, THE SYSTEM SHALL include in the banner the suggestion to wait 30 seconds and relaunch Squirrel, then to check `~/.squirrel/web-ui.stderr.log` if the issue persists. |
| R-6.6 | WHEN the refusal cause is `LaunchdTokenInvalid`, THE SYSTEM SHALL include in the banner the recommendation to run `install.sh --reinstall`. |
