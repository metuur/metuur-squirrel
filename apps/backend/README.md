# Squirrel — Web UI (local browser companion)

A modern browser interface for your Squirrel vault. **React 19 + Vite + Tailwind + shadcn/Radix** on the front, **stdlib-only Python** JSON API on the back. Runs **locally** (`127.0.0.1`), with **no authentication** (don't expose to the internet).

> The compiled UI bundle ships with the plugin at `companions/web-ui/app/dist/`, so most users do **not** need Node.js installed. Node is only needed if you want to rebuild the UI from source.

---

## Quick start

```bash
# One-time install (verifies Python, confirms prebuilt UI is present)
bash scripts/install-web-ui.sh

# Start the server (defaults: port 3939, localhost only)
squirrel web start

# Open it in your default browser
squirrel web open

# Check whether it's running
squirrel web status

# Stop it
squirrel web stop
```

Default URL: **http://127.0.0.1:3939**

If you change ports: `squirrel web start --port 4040`.

---

## What's inside

```
companions/web-ui/
├── server.py                  # Stdlib-only Python JSON API + SPA shell
├── app/                       # React source (only needed to rebuild)
│   ├── src/
│   │   ├── api/client.ts      # fetch wrappers for /api/*
│   │   ├── components/        # shadcn-style UI primitives + layout
│   │   ├── pages/             # Home, Project, Note, Deadlines, History, Settings
│   │   └── ...
│   ├── dist/                  # ← Compiled bundle (COMMITTED to git)
│   ├── package.json
│   ├── tailwind.config.ts
│   └── vite.config.ts
└── launchd/                   # Optional macOS auto-start
```

The Python server (`server.py`) serves:
- `GET /api/*` — JSON endpoints the SPA consumes
- `GET /` and any unknown path → `dist/index.html` (the SPA shell)
- `GET /assets/*` → the hashed Vite bundle chunks (cached for 1 year)

---

## Rebuilding the UI (optional, requires Node 18+)

If you edit anything under `companions/web-ui/app/src/`:

```bash
cd companions/web-ui/app
npm install            # one-time, ~30s, 197 packages
npm run build          # vite build → dist/
git add dist           # commit the new bundle so users skip the build
```

Or from the install script:

```bash
bash scripts/install-web-ui.sh --rebuild
```

During development, the dev server with hot-reload + proxy:

```bash
cd companions/web-ui/app
npm run dev            # opens http://127.0.0.1:5173, proxies /api/* → :3939
```

(Keep `squirrel web start` running in another terminal so the proxy has something to hit.)

---

## Auto-start on login (macOS only, optional)

```bash
bash companions/web-ui/launchd/install.sh
```

Installs `~/Library/LaunchAgents/org.squirrel.web-ui.plist` and loads it via `launchctl`. The server then starts every time you log in.

Remove it:

```bash
bash companions/web-ui/launchd/install.sh --uninstall
```

Non-macOS hosts: the script prints a one-line message and exits cleanly.

---

## Uninstall

```bash
squirrel web uninstall
```

That command:
- stops the running server (if any),
- removes the launchd plist (if installed),
- removes `~/.squirrel/web-ui.pid`.

Your vault, `~/.squirrel/config.toml`, and the source files under `companions/web-ui/` are **left untouched**. To delete the source too: `rm -rf companions/web-ui`.

---

## Security model

- **Localhost only by default.** Server binds `127.0.0.1`. `--lan` opt-in binds `0.0.0.0` and prints a yellow warning to stderr — use only on a trusted network.
- **No authentication.** Mitigated by localhost binding. Anyone with shell access to your machine can already read your vault.
- **No telemetry.** Zero outbound HTTP requests by default. The optional AI proxy (`[ai]` block in `~/.squirrel/config.toml`) is the only thing that talks to a remote API.
- **Atomic writes.** Every file write goes through a temp file + `os.replace`. mtime concurrency is checked on every overwrite — conflicting saves return HTTP 409 with the current body.
- **Path containment.** Every file-touching route resolves the target with `Path.resolve()` and refuses anything outside the active workspace.
- **Security headers.** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` on every response. Dynamic JSON is `Cache-Control: no-store`. Hashed `/assets/*` chunks are `immutable, max-age=31536000`.

---

## What's in scope

- Browse projects, recent activity, deadlines.
- Add a note from any page (capture modal).
- Edit a note or a project page (plain textarea, raw Markdown).
- Switch workspace (only visible with ≥ 2 workspaces).
- Dark / light / auto theme.
- Optional AI suggestions (gated on `[ai]` config block).

## What's NOT in scope (by design)

- Delete a file from the UI.
- Create or rename a project / folder from the UI.
- Sync packages (sync-out / sync-in stay in slash commands + CLI).
- Real-time updates (no WebSockets).
- Authentication, multi-user, remote access.
- Markdown WYSIWYG / preview pane.
- Tag editor, frontmatter editor, backlinks panel.

---

## Optional AI features

Add to `~/.squirrel/config.toml`:

```toml
[ai]
provider = "anthropic"
api_key = "sk-ant-..."        # or use api_key_env = "ANTHROPIC_API_KEY"
model = "claude-sonnet-4-6"   # optional, defaults to claude-sonnet-4-6
```

Then three buttons light up in the UI:
- **Generate brief** on each project page.
- **Help me decide** in the capture modal.
- **Help me start** on the home page when no focus is set.

Each click sends one request to the Anthropic Messages API via Python's stdlib `urllib.request` (no `requests`, no `httpx`, no SDK dependency). `max_tokens` capped at 2000. At most one AI request per browser session in-flight at a time.

If you remove the `[ai]` block, the buttons disappear and no AI code ever runs.

---

## Reversibility checklist

| Goal | Command |
|---|---|
| Stop the server | `squirrel web stop` |
| Disable auto-start (macOS) | `bash companions/web-ui/launchd/install.sh --uninstall` |
| Remove PID + launchd plist | `squirrel web uninstall` |
| Delete the companion source | `rm -rf companions/web-ui` |

After any of these, every other Squirrel command (status, deadlines, slash commands, skills) keeps working. Your vault and config are never touched by uninstall.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `not running` after `start` | Check `~/.squirrel/web-ui.log`. Port may be in use; try `--port 4040`. |
| `/` shows "The browser UI is not built yet." | The shipped `dist/` is missing. Run `bash scripts/install-web-ui.sh --rebuild`. |
| iPad shows blank page | Both devices must be on the same Wi-Fi *and* the server must be started with `--lan` (acceptable only on a trusted network). |
| Buttons absent / can't add notes | Verify you have at least one vault configured: `squirrel vaults list`. |
| AI buttons don't appear | Confirm `[ai]` block in `~/.squirrel/config.toml`. Restart the server. |

The full request log lives at `~/.squirrel/web-ui.log`. It records `<ISO-timestamp> <method> <path> <status>` only — no bodies, no cookies, no API keys.
