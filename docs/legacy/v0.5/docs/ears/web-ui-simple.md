# Web UI (Simple) — EARS Specifications

## Unit 1: Server lifecycle and binding

| ID    | EARS statement |
|-------|----------------|
| R-1.1 | THE SYSTEM SHALL provide a `companions/web-ui/server.py` executable using only Python standard library modules. |
| R-1.2 | WHEN `squirrel web start` is invoked, THE SYSTEM SHALL start the server, write its PID to `~/.squirrel/web-ui.pid`, and print the listening URL to stdout. |
| R-1.3 | THE SYSTEM SHALL bind to `127.0.0.1` by default. |
| R-1.4 | IF the user passes `--lan`, THE SYSTEM SHALL bind to `0.0.0.0` and print a yellow warning to stderr indicating the server is reachable on the LAN with no authentication. |
| R-1.5 | THE SYSTEM SHALL accept `--port N` with default `3939`. |
| R-1.6 | WHEN `squirrel web stop` is invoked, THE SYSTEM SHALL send SIGTERM to the PID in `~/.squirrel/web-ui.pid`, wait up to 5 seconds, send SIGKILL if still alive, then remove the PID file. |
| R-1.7 | WHEN `squirrel web status` is invoked, THE SYSTEM SHALL print one line indicating "running on <URL>" or "not running" and exit with code 0 (running) or 1 (not running). |
| R-1.8 | WHEN `squirrel web open` is invoked and the server is not running, THE SYSTEM SHALL start it before opening the default browser via Python's `webbrowser` module. |
| R-1.9 | WHEN `squirrel web uninstall` is invoked, THE SYSTEM SHALL stop the server, remove the launchd plist (if installed), and remove the PID file. |
| R-1.10 | WHILE the server is running, THE SYSTEM SHALL log requests to `~/.squirrel/web-ui.log` in the format `<ISO-timestamp> <method> <path> <status>` with no request bodies and no cookie values. |
| R-1.11 | THE SYSTEM SHALL have zero non-stdlib Python dependencies. |

## Unit 2: Pages

| ID    | EARS statement |
|-------|----------------|
| R-2.1 | THE SYSTEM SHALL serve a home page at `GET /` showing: today's focus, deadlines today/tomorrow, a list of projects, and a "Add a note" button. |
| R-2.2 | THE SYSTEM SHALL serve `GET /projects/{slug}` showing the project description, recent notes for that project, deadlines for that project, and an edit button. |
| R-2.3 | THE SYSTEM SHALL serve `GET /projects/{slug}/edit` with a single textarea for the project page body and a save button. |
| R-2.4 | THE SYSTEM SHALL serve `GET /notes/{id}` showing the note body, with edit and back-to-project actions. |
| R-2.5 | THE SYSTEM SHALL serve `GET /notes/{id}/edit` with a single textarea for the note body and a save button. |
| R-2.6 | THE SYSTEM SHALL serve `GET /deadlines` showing items grouped into "Today", "This week", and "Later". |
| R-2.7 | THE SYSTEM SHALL serve `GET /history` showing the most recently modified 30 items across the current workspace. |
| R-2.8 | THE SYSTEM SHALL serve `GET /settings` showing the dark-mode toggle, workspace picker (if >1 workspace), and an "About" block. |
| R-2.9 | WHEN any page renders, THE SYSTEM SHALL render server-side from a `.html` template using Python f-strings or equivalent stdlib templating. |
| R-2.10 | EACH page SHALL load and render its first paint within 1 second on a 5-year-old laptop on localhost. |
| R-2.11 | EACH page SHALL be usable with JavaScript disabled, with forms degrading to standard HTML POST submissions. |

## Unit 3: JSON endpoints

| ID    | EARS statement |
|-------|----------------|
| R-3.1 | THE SYSTEM SHALL expose `POST /api/note` accepting JSON `{text, project_slug?}` and creating a new capture file in the matching project folder (or `99-Resources/Inbox/` if project_slug is absent or `"unfiled"`). |
| R-3.2 | THE SYSTEM SHALL expose `POST /api/note/{id}` accepting JSON `{body, mtime}` and overwriting the note file. |
| R-3.3 | THE SYSTEM SHALL expose `POST /api/project/{slug}` accepting JSON `{body, mtime}` and overwriting the project page file. |
| R-3.4 | THE SYSTEM SHALL expose `GET /api/search?q=QUERY` returning matching files with up to 3 lines of snippet per file. |
| R-3.5 | THE SYSTEM SHALL expose `GET /api/parakeet` returning the user-facing deadline-tone message for the current workspace, derived from `lib/deadline_scanner` but rendered through `lib/vocabulary`. |
| R-3.6 | THE SYSTEM SHALL expose `POST /api/vault` accepting JSON `{name}` and setting a `squirrel_vault` cookie naming the active workspace. |
| R-3.7 | WHEN any JSON endpoint receives malformed JSON, THE SYSTEM SHALL respond with HTTP 400 and a plain-English error message (no stack traces). |
| R-3.8 | WHEN any write endpoint runs, THE SYSTEM SHALL write to a temporary file in the target directory and call `os.replace` to atomically move it into place. |
| R-3.9 | WHEN any write endpoint runs, THE SYSTEM SHALL resolve the target path with `Path.resolve()` and verify the resolved path is inside the active vault root, returning HTTP 403 otherwise. |
| R-3.10 | WHEN a write request includes an `mtime` field, THE SYSTEM SHALL compare it to the current file's mtime; IF they differ, THE SYSTEM SHALL return HTTP 409 with `{current_body, current_mtime}` and a user-facing message. |

## Unit 4: Vocabulary translation

| ID    | EARS statement |
|-------|----------------|
| R-4.1 | THE SYSTEM SHALL expose a module `lib/vocabulary.py` that translates internal Squirrel terms to user-facing labels. |
| R-4.2 | THE SYSTEM SHALL never render the string "vault" in any user-visible HTML when only one vault is configured. |
| R-4.3 | WHEN multiple vaults are configured, THE SYSTEM SHALL use the word "workspace" in user-visible HTML (not "vault"). |
| R-4.4 | THE SYSTEM SHALL never render any of these strings in user-visible HTML: `frontmatter`, `PARA`, `intent`, `wiki-link`, `.md`, `proyecto`, `tipo`, `estado`, `01-Proyectos-Activos`, `02-Areas`, `03-Recursos`, `04-Archivo`, `02-Parking-Lot`, `99-Resources`, `shutdown note`, `parakeet`. |
| R-4.5 | WHEN a project is referenced by its internal tag (e.g., `PROYECTO-A`), THE SYSTEM SHALL render its human title parsed from the project page's `# Title` line, falling back to a capitalized version of the slug if no title is found. |
| R-4.6 | WHEN an urgency level is rendered, THE SYSTEM SHALL map: `critical, urgent` → "Today / Tomorrow", `soon` → "This week", `upcoming, eventual, distant` → "Later". |
| R-4.7 | THE SYSTEM SHALL include a test `tests/test_no_developer_vocabulary.py` that crawls every rendered HTML response and fails if any forbidden term from R-4.4 appears. |

## Unit 5: Capture (the primary user flow)

| ID    | EARS statement |
|-------|----------------|
| R-5.1 | THE SYSTEM SHALL display a "Add a note" button on every page in the global header. |
| R-5.2 | WHEN the user clicks "Add a note", THE SYSTEM SHALL open a modal containing: a textarea (autofocused), a project dropdown defaulted to the current project (or "Unfiled" if not on a project page), an "Add" button, and a "Cancel" button. |
| R-5.3 | WHEN the user submits the capture modal with non-empty text, THE SYSTEM SHALL POST `/api/note` and on success close the modal, show a "Saved" toast for 2 seconds, and refresh the underlying page. |
| R-5.4 | WHEN the project dropdown is "Unfiled" at submit, THE SYSTEM SHALL write the note to `<vault>/99-Resources/Inbox/UNFILED-<NNN>.md` with frontmatter that marks it unfiled. |
| R-5.5 | WHEN the project dropdown selects an existing project, THE SYSTEM SHALL write the note to that project's folder with the existing capture-numbering convention from `lib/intent_parser`. |
| R-5.6 | THE SYSTEM SHALL expose a new helper `lib/capture_writer.py` containing `write_capture(vault_path, project_slug_or_none, text) -> Path` so the same function can be reused by future callers. |
| R-5.7 | WHEN capture writes fail (disk full, permissions, etc.), THE SYSTEM SHALL respond with HTTP 500 and a plain-English message; the modal SHALL show the message and not close. |

## Unit 6: Mobile, iPad, and accessibility

| ID    | EARS statement |
|-------|----------------|
| R-6.1 | THE SYSTEM SHALL include `<meta name="viewport" content="width=device-width, initial-scale=1">` on every page. |
| R-6.2 | THE SYSTEM SHALL render all body text at a minimum of 18px on viewports ≤ 1024px wide and 20px on tablet/desktop. |
| R-6.3 | THE SYSTEM SHALL render all interactive tap targets (buttons, links acting as buttons, dropdown triggers) at a minimum of 44×44 px. |
| R-6.4 | THE SYSTEM SHALL use a color palette with at least 4.5:1 contrast ratio between body text and background in both light and dark modes (WCAG 2.1 AA). |
| R-6.5 | THE SYSTEM SHALL provide a dark mode toggle in `/settings` and persist the preference in a cookie (`squirrel_theme`). |
| R-6.6 | WHEN the cookie `squirrel_theme` is absent, THE SYSTEM SHALL honor the browser's `prefers-color-scheme` media query for the initial theme. |
| R-6.7 | THE SYSTEM SHALL not use any hover-only affordances; every action is reachable via tap/click. |
| R-6.8 | THE SYSTEM SHALL function correctly on iPad Safari and on Firefox, Chrome, and Safari on macOS. |

## Unit 7: Multi-vault awareness

| ID    | EARS statement |
|-------|----------------|
| R-7.1 | THE SYSTEM SHALL read the configured vault list via `lib/config_loader.list_vaults()` at startup and on each request. |
| R-7.2 | WHEN exactly one vault is configured, THE SYSTEM SHALL NOT render any workspace picker, workspace label, or the word "workspace" anywhere in the UI. |
| R-7.3 | WHEN two or more vaults are configured, THE SYSTEM SHALL render a discreet dropdown in the global header titled "Workspace" listing each by its `name`. |
| R-7.4 | WHEN the user selects a different workspace, THE SYSTEM SHALL POST `/api/vault` with the new name, set the `squirrel_vault` cookie, and reload the current page. |
| R-7.5 | WHEN a request arrives with no `squirrel_vault` cookie, THE SYSTEM SHALL use the default vault. |
| R-7.6 | WHEN a request arrives with a `squirrel_vault` cookie naming a vault that no longer exists, THE SYSTEM SHALL fall back to the default vault and clear the cookie. |

## Unit 8: Concurrency and write safety

| ID    | EARS statement |
|-------|----------------|
| R-8.1 | WHEN any GET endpoint returns a file body, THE SYSTEM SHALL include the file's mtime in the response. |
| R-8.2 | WHEN any POST endpoint writes a file, THE SYSTEM SHALL require an `mtime` field in the request body. |
| R-8.3 | IF the request `mtime` does not match the current file mtime, THE SYSTEM SHALL return HTTP 409 with `{current_body, current_mtime, message}`. |
| R-8.4 | WHEN the UI receives a 409 conflict, THE SYSTEM SHALL show a modal with three options: "Show their version" (load current body into the editor), "Keep mine" (force-save by re-fetching mtime and retrying), and "Cancel" (close the modal). |
| R-8.5 | THE SYSTEM SHALL not provide an automatic merge or three-way diff in v1. |

## Unit 9: Security and headers

| ID    | EARS statement |
|-------|----------------|
| R-9.1 | THE SYSTEM SHALL bind only to `127.0.0.1` unless the `--lan` flag is explicitly provided. |
| R-9.2 | THE SYSTEM SHALL not implement any authentication mechanism in v1. |
| R-9.3 | THE SYSTEM SHALL set `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` on every response. |
| R-9.4 | THE SYSTEM SHALL set `Cache-Control: no-store` on all dynamic responses (`/api/*` and rendered pages); static assets MAY be cached. |
| R-9.5 | IF a request path contains `..`, leading `/`, or any segment starting with `.`, THE SYSTEM SHALL return HTTP 400. |
| R-9.6 | WHEN any file-touching route runs, THE SYSTEM SHALL resolve the target with `Path.resolve()` and verify containment within the vault root, returning HTTP 403 otherwise. |
| R-9.7 | THE SYSTEM SHALL refuse HTTP methods other than GET, POST, OPTIONS with HTTP 405. |
| R-9.8 | THE SYSTEM SHALL not include vault file contents, request bodies, cookie values, or API keys in any log output. |

## Unit 10: Error presentation

| ID    | EARS statement |
|-------|----------------|
| R-10.1 | THE SYSTEM SHALL never expose a Python stack trace to the browser. |
| R-10.2 | WHEN an internal error occurs, THE SYSTEM SHALL render an HTML page (for GET routes) or return JSON `{error: "<plain English message>"}` (for /api routes) with HTTP 500. |
| R-10.3 | THE SYSTEM SHALL write the full stack trace to `~/.squirrel/web-ui.log` for the operator to inspect, not the browser. |
| R-10.4 | THE SYSTEM SHALL use plain-English error messages with no technical jargon. Example: "Could not save your note. Please try again." (not "EIO writing /vault/...") |

## Unit 11: Installer integration

| ID    | EARS statement |
|-------|----------------|
| R-11.1 | THE SYSTEM SHALL add a new optional step to `install.sh` titled "Web UI (browser interface)" with default selection "No". |
| R-11.2 | WHEN the user selects "Yes" in that step, THE SYSTEM SHALL run `scripts/install-web-ui.sh`. |
| R-11.3 | WHEN `scripts/install-web-ui.sh` runs, THE SYSTEM SHALL register the `squirrel web` subcommand group (already part of the squirrel CLI binary), confirm no further build step is required, and print the URL to launch. |
| R-11.4 | THE SYSTEM SHALL not require Node.js or npm at install time or runtime. |
| R-11.5 | WHEN `--auto` mode is used in `install.sh`, THE SYSTEM SHALL skip the web UI step unless `--with-web-ui` is also passed. |
| R-11.6 | THE SYSTEM SHALL provide a `companions/web-ui/launchd/install.sh` that installs a launchd LaunchAgent on macOS to auto-start the web UI server at login. |
| R-11.7 | IF the OS is not macOS when the launchd installer runs, THE SYSTEM SHALL print a message and exit cleanly without modifying anything. |

## Unit 12: Optional AI proxy (Milestone D-AI)

| ID    | EARS statement |
|-------|----------------|
| R-12.1 | THE SYSTEM SHALL render no AI-related buttons, copy, or hints if `~/.squirrel/config.toml` does not contain an `[ai]` section. |
| R-12.2 | WHEN `[ai]` config is present with `provider = "anthropic"` and a resolvable API key, THE SYSTEM SHALL render three AI-augmented buttons: "Generate brief" (on project pages), "Help me decide" (in the capture modal), and "Help me start" (on the home page when no focus is set). |
| R-12.3 | THE SYSTEM SHALL resolve the API key from either `api_key` (string in config) or `api_key_env` (environment variable name in config). Direct `api_key` SHALL be preferred. |
| R-12.4 | THE SYSTEM SHALL never log or render the API key value. |
| R-12.5 | WHEN an AI endpoint is invoked, THE SYSTEM SHALL use only `urllib.request` (stdlib) to call the Anthropic API. No `requests`, `httpx`, or `anthropic` SDK dependency. |
| R-12.6 | THE SYSTEM SHALL enforce at most one concurrent AI request per browser cookie session. |
| R-12.7 | THE SYSTEM SHALL set `max_tokens` ≤ 2000 on every AI request to bound cost. |
| R-12.8 | WHEN an AI request fails (network, API error, rate limit), THE SYSTEM SHALL render a plain-English error and offer "Try again". |

## Unit 13: Performance

| ID    | EARS statement |
|-------|----------------|
| R-13.1 | EACH HTML page SHALL first-paint within 1 second on localhost on a 5-year-old laptop or iPad. |
| R-13.2 | TOTAL assets per page (HTML + CSS + JS + icons) SHALL be ≤ 100 KB uncompressed. |
| R-13.3 | THE SYSTEM SHALL not require any third-party CDN or external network resource to render any page. |
| R-13.4 | THE SYSTEM SHALL not load any web font from a CDN; system fonts are sufficient. |

## Unit 14: Reversibility

| ID    | EARS statement |
|-------|----------------|
| R-14.1 | WHEN `squirrel web uninstall` runs, THE SYSTEM SHALL stop the server, remove the launchd plist (if installed), and remove the PID file. |
| R-14.2 | WHEN `squirrel web uninstall` runs, THE SYSTEM SHALL leave the user's vault and `~/.squirrel/config.toml` untouched. |
| R-14.3 | WHEN the entire `companions/web-ui/` directory is removed, THE SYSTEM SHALL not affect any other Squirrel command, skill, or CLI subcommand. |
| R-14.4 | THE SYSTEM SHALL document the uninstall procedure in `companions/web-ui/README.md`. |

## Unit 15: Phased delivery

| ID    | EARS statement |
|-------|----------------|
| R-15.1 | Milestone B (Read-only): WHEN complete, THE SYSTEM SHALL satisfy units 1, 2, 4, 6, 7, 9, 10, 11, 13, the read portions of unit 5, and units 8 (read-only path). |
| R-15.2 | Milestone C (Capture + edit): WHEN complete, THE SYSTEM SHALL satisfy units 3 (write endpoints), 5 (full capture flow), the write portions of 2 (edit pages), and unit 8 (concurrency). |
| R-15.3 | Milestone D-AI (Optional AI): WHEN complete AND when the operator configures `[ai]`, THE SYSTEM SHALL satisfy unit 12. |
| R-15.4 | Milestone E (Polish): WHEN complete, THE SYSTEM SHALL provide PWA manifest, keyboard navigation parity with browser defaults, and complete user-facing documentation in `docs/guides/getting-started.md`. |
