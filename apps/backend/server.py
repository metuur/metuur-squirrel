#!/usr/bin/env python3
"""
companions/web-ui/server.py — Squirrel web UI JSON API + React SPA shell.

This is the v2 server that backs the React + Vite + Tailwind + shadcn UI in
`companions/web-ui/app/`. The Python side is now a pure JSON API plus a
static shell that serves the SPA's `dist/index.html` at `/` and the
bundle assets at `/assets/*`.

Hard constraints:
  C1.  Python stdlib only (server side). The UI side has its own Node deps.
  C2.  Python 3.9+.
  C5.  Localhost-only by default (--lan opt-in).
  C7.  Atomic writes via temp file + os.replace.
  C8.  mtime concurrency on every file write.
  C12. The vocabulary translator (lib/vocabulary.py) still scrubs labels
       returned by the JSON API.

Run:
    python3 companions/web-ui/server.py --port 3939
"""

from __future__ import annotations

import argparse
import datetime
import hmac
import http.server
import json
import logging
import logging.handlers
import os
import pathlib
import re
import socket
import socketserver
import subprocess
import sys
import threading
import traceback
import urllib.parse
from typing import Any, Callable, Optional

# When running as a PyInstaller bundle, lib modules are frozen and sys._MEIPASS
# holds the temp extraction dir. In dev, walk up to the repo root as before.
if getattr(sys, "frozen", False):
    _LIB = pathlib.Path(sys._MEIPASS)  # type: ignore[attr-defined]
else:
    _REPO = pathlib.Path(__file__).resolve().parent.parent.parent
    _LIB = _REPO / "apps" / "cli" / "lib"
    sys.path.insert(0, str(_LIB))

import config_loader  # noqa: E402
import db  # noqa: E402
import vocabulary  # noqa: E402


# ─── Paths / constants ───────────────────────────────────────────────────────

DEFAULT_PORT = 3939
DEFAULT_HOST = "127.0.0.1"
LAN_HOST = "0.0.0.0"

# ─── Runtime Trust Handshake auth state (docs/ears/runtime-trust-handshake.md) ─
# Set once at startup by configure_auth(). TOKEN holds the per-process shared
# secret (hex). DEV_MODE is True only when the backend was started with neither
# --token nor --token-file, meaning loopback requests are served without auth.
TOKEN: Optional[str] = None
DEV_MODE: bool = False
_TOKEN_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _auth_required() -> bool:
    """True when requests must carry a valid X-Squirrel-Token (R-2.6, R-2.8).

    Enforcement is active only when a token is configured AND dev mode is off.
    The (TOKEN=None, DEV_MODE=False) state happens only when configure_auth was
    never called — i.e. the server is embedded in-process (tests, library use)
    — and is treated as unenforced. In production main() always calls
    configure_auth, which sets either TOKEN (enforce) or DEV_MODE=True (bypass).
    """
    return TOKEN is not None and not DEV_MODE

# The SPA build output. When frozen (PyInstaller bundle) the dist/ folder is
# extracted alongside the lib modules under sys._MEIPASS. In dev it lives at
# apps/backend/app/dist/ relative to this file.
if getattr(sys, "frozen", False):
    APP_DIST = pathlib.Path(sys._MEIPASS) / "app" / "dist"  # type: ignore[attr-defined]
else:
    APP_DIST = pathlib.Path(__file__).resolve().parent / "app" / "dist"

WORKSPACE_COOKIE = "squirrel_vault"
THEME_COOKIE = "squirrel_theme"

# ─── Lazy log path ───────────────────────────────────────────────────────────


def _log_path() -> pathlib.Path:
    return pathlib.Path("~/.squirrel/web-ui.log").expanduser()


LOG_PATH = _log_path()
PID_PATH = pathlib.Path("~/.squirrel/web-ui.pid").expanduser()

# Rotation policy — keep at most 4 files of 10 MB each (~40 MB worst case
# per user). Prior implementation was unbounded append, which grew the log
# ~1 MB/month per user with the tray polling every 30s.
LOG_MAX_BYTES = 10_000_000
LOG_BACKUP_COUNT = 3

_LOG_HANDLER: Optional[logging.handlers.RotatingFileHandler] = None
_LOG_HANDLER_PATH: Optional[pathlib.Path] = None
_LOG_HANDLER_LOCK = threading.Lock()


def _get_log_handler() -> Optional[logging.handlers.RotatingFileHandler]:
    """Return a process-cached RotatingFileHandler keyed by the current
    ``_log_path()``. Rebuilds when the path changes — needed for the test
    suite, which sets ``HOME`` to a different tempdir per test.

    Returns None when the parent dir can't be created or the file can't be
    opened (matches the prior ``except OSError: pass`` swallow semantics).
    """
    global _LOG_HANDLER, _LOG_HANDLER_PATH
    p = _log_path()
    if _LOG_HANDLER is not None and _LOG_HANDLER_PATH == p:
        return _LOG_HANDLER
    with _LOG_HANDLER_LOCK:
        if _LOG_HANDLER is not None and _LOG_HANDLER_PATH == p:
            return _LOG_HANDLER
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.handlers.RotatingFileHandler(
                str(p),
                maxBytes=LOG_MAX_BYTES,
                backupCount=LOG_BACKUP_COUNT,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
        except OSError:
            return None
        if _LOG_HANDLER is not None:
            try:
                _LOG_HANDLER.close()
            except Exception:
                pass
        _LOG_HANDLER = handler
        _LOG_HANDLER_PATH = p
        return handler


def _write_log_line(line: str) -> None:
    handler = _get_log_handler()
    if handler is None:
        return
    record = logging.LogRecord(
        name="squirrel.web-ui",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=line,
        args=None,
        exc_info=None,
    )
    try:
        handler.emit(record)
    except Exception:
        pass


def _log_request(method: str, path: str, status: int) -> None:
    iso = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    bare_path = path.split("?", 1)[0]
    _write_log_line(f"{iso} {method} {bare_path} {status}")


def _log_exception(exc: BaseException) -> None:
    trace = "".join(traceback.format_exception(exc)).rstrip()
    iso = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    for line in trace.splitlines():
        _write_log_line(f"{iso} ERROR {line}")


# ─── Cookies ─────────────────────────────────────────────────────────────────


def parse_cookie_header(raw: Optional[str]) -> dict[str, str]:
    if not raw:
        return {}
    out: dict[str, str] = {}
    for part in raw.split(";"):
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = v.strip()
    return out


def _set_cookie(handler: "Handler", name: str, value: str) -> None:
    handler.send_header(
        "Set-Cookie",
        f"{name}={value}; Path=/; HttpOnly; SameSite=Lax",
    )


def _clear_cookie(handler: "Handler", name: str) -> None:
    handler.send_header(
        "Set-Cookie",
        f"{name}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax",
    )


# ─── Vault resolution ────────────────────────────────────────────────────────


class VaultContext:
    def __init__(self, active, all_vaults, cookie_was_stale: bool):
        self.active = active
        self.all = all_vaults
        self.cookie_was_stale = cookie_was_stale
        self.multi = len(all_vaults) > 1


def resolve_vault(cookie_name: Optional[str]) -> Optional[VaultContext]:
    try:
        vaults = config_loader.list_vaults()
    except config_loader.NoVaultsConfiguredError:
        return None
    cookie_was_stale = False
    active = None
    if cookie_name:
        for v in vaults:
            if v.name == cookie_name:
                active = v
                break
        if active is None:
            cookie_was_stale = True
    if active is None:
        for v in vaults:
            if v.default:
                active = v
                break
    if active is None:
        active = vaults[0]
    return VaultContext(active=active, all_vaults=vaults, cookie_was_stale=cookie_was_stale)


# ─── Path security ───────────────────────────────────────────────────────────


def is_safe_request_path(path: str) -> bool:
    bare = path.split("?", 1)[0]
    if ".." in bare.split("/"):
        return False
    for seg in bare.split("/"):
        if seg.startswith(".") and seg not in ("",):
            return False
    return True


def is_path_inside(target: pathlib.Path, root: pathlib.Path) -> bool:
    try:
        target.resolve(strict=False).relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


# ─── Scratch-pad bootstrap ───────────────────────────────────────────────────

_scratch_pad_ensured: set = set()  # vault paths already checked this process


def _ensure_scratch_pad_once(vault_path: pathlib.Path) -> None:
    key = str(vault_path)
    if key in _scratch_pad_ensured:
        return
    _scratch_pad_ensured.add(key)
    try:
        from new_project_writer import ensure_scratch_pad
        ensure_scratch_pad(vault_path)
    except Exception:
        pass  # Non-fatal


_mind_journal_ensured: set = set()  # vault paths already checked this process


def _ensure_mind_journal_once(vault_path: pathlib.Path, vault_name: str) -> None:
    key = str(vault_path)
    if key in _mind_journal_ensured:
        return
    _mind_journal_ensured.add(key)
    try:
        from mind_journal import ensure_mind_journal
        ensure_mind_journal(vault_path, vault_name)
    except Exception:
        pass  # Non-fatal


# ─── Route table ─────────────────────────────────────────────────────────────


ROUTES: list[tuple[str, "re.Pattern[str]", str]] = [
    # ── JSON API ────────────────────────────────────────────────────────────
    # Runtime Trust Handshake probe — exempt from the token gate in _dispatch
    # because it runs its own contract (R-3.1..R-3.4). Must precede the SPA
    # wildcard so it is matched as an API route, not the shell.
    ("GET",  re.compile(r"^/api/_handshake$"),                        "api_handshake"),
    ("GET",  re.compile(r"^/api/me$"),                                "api_me"),
    ("GET",  re.compile(r"^/api/vaults$"),                            "api_vaults_list"),
    ("POST", re.compile(r"^/api/vault$"),                             "api_set_vault"),
    ("GET",  re.compile(r"^/api/home$"),                              "api_home"),
    ("GET",  re.compile(r"^/api/focus$"),                             "api_focus_get"),
    ("PUT",  re.compile(r"^/api/focus/today$"),                       "api_focus_put_today"),
    ("PUT",  re.compile(r"^/api/focus/week$"),                        "api_focus_put_week"),
    ("GET",  re.compile(r"^/api/focus/history$"),                     "api_focus_history"),
    ("POST", re.compile(r"^/api/focus/checkin$"),                     "api_focus_checkin"),
    ("POST", re.compile(r"^/api/focus/checkout$"),                    "api_focus_checkout"),
    ("GET",  re.compile(r"^/api/focus/session$"),                     "api_focus_session"),
    ("POST", re.compile(r"^/api/focus/recalculate$"),                 "api_focus_recalculate"),
    ("GET",  re.compile(r"^/api/projects$"),                          "api_projects_list"),
    ("GET",  re.compile(r"^/api/projects/(?P<slug>[A-Z0-9][A-Z0-9_-]*)$"),
                                                                       "api_project_detail"),
    ("POST", re.compile(r"^/api/projects$"),                          "api_project_create"),
    ("POST", re.compile(r"^/api/intents$"),                           "api_intent_create"),
    ("POST", re.compile(r"^/api/projects/(?P<slug>[A-Z0-9][A-Z0-9_-]*)$"),
                                                                       "api_project_save"),
    ("DELETE", re.compile(r"^/api/projects/(?P<slug>[A-Z0-9][A-Z0-9_-]*)$"),
                                                                       "api_project_delete"),
    ("PATCH", re.compile(r"^/api/projects/(?P<slug>[A-Z0-9][A-Z0-9_-]*)/status$"),
                                                                       "api_project_set_status"),
    ("GET",  re.compile(r"^/api/notes/(?P<note_id>[A-Za-z0-9][A-Za-z0-9_-]*)$"),
                                                                       "api_note_detail"),
    ("POST", re.compile(r"^/api/notes/(?P<note_id>[A-Za-z0-9][A-Za-z0-9_-]*)$"),
                                                                       "api_note_save"),
    ("POST", re.compile(r"^/api/notes$"),                             "api_note_create"),
    ("GET",   re.compile(r"^/api/journal$"),                          "api_journal_get"),
    ("POST",  re.compile(r"^/api/journal/entry$"),                    "api_journal_entry"),
    ("PATCH", re.compile(r"^/api/journal/config$"),                   "api_journal_config"),
    ("GET",  re.compile(r"^/api/reminders$"),                         "api_reminders"),
    ("PATCH", re.compile(r"^/api/reminder/(?P<note_id>[A-Za-z0-9][A-Za-z0-9_-]*)/dismiss$"), "api_reminder_dismiss"),
    ("PATCH", re.compile(r"^/api/reminder/(?P<note_id>[A-Za-z0-9][A-Za-z0-9_-]*)/snooze$"),  "api_reminder_snooze"),
    ("GET",  re.compile(r"^/api/quick-tasks$"),                       "api_quick_tasks_list"),
    ("POST", re.compile(r"^/api/quick-tasks$"),                       "api_quick_task_create"),
    ("PATCH", re.compile(r"^/api/quick-task/(?P<qt_id>[A-Za-z0-9][A-Za-z0-9_-]*)/complete$"), "api_quick_task_complete"),
    ("PATCH", re.compile(r"^/api/quick-task/(?P<qt_id>[A-Za-z0-9][A-Za-z0-9_-]*)/snooze$"),   "api_quick_task_snooze"),
    ("DELETE", re.compile(r"^/api/quick-task/(?P<qt_id>[A-Za-z0-9][A-Za-z0-9_-]*)$"),         "api_quick_task_delete"),
    ("POST", re.compile(r"^/api/reveal$"),                            "api_reveal"),
    ("GET",  re.compile(r"^/api/deadlines$"),                         "api_deadlines"),
    ("GET",  re.compile(r"^/api/history$"),                           "api_history"),
    ("GET",  re.compile(r"^/api/search$"),                            "api_search"),
    ("GET",  re.compile(r"^/api/parakeet$"),                          "api_parakeet"),
    ("POST", re.compile(r"^/api/theme$"),                             "api_set_theme"),
    ("POST", re.compile(r"^/api/settings/notifications$"),           "api_settings_notifications"),
    ("POST", re.compile(r"^/api/notifications/preview$"),            "api_notifications_preview"),
    ("GET",  re.compile(r"^/api/notifications$"),                    "api_notifications_list"),
    ("POST", re.compile(r"^/api/notifications/read-all$"),           "api_notifications_read_all"),
    ("PATCH", re.compile(r"^/api/notification/(?P<nid>[A-Za-z0-9][A-Za-z0-9_-]*)/read$"),
                                                                      "api_notification_read"),
    ("PATCH", re.compile(r"^/api/notification/(?P<nid>[A-Za-z0-9][A-Za-z0-9_-]*)/dismiss$"),
                                                                      "api_notification_dismiss"),
    ("GET",  re.compile(r"^/api/cache/stats$"),                       "api_cache_stats"),
    # ── SPA shell + static bundle ───────────────────────────────────────────
    ("GET",  re.compile(r"^/favicon\.ico$"),                          "spa_favicon"),
    ("GET",  re.compile(r"^/favicon\.svg$"),                          "spa_favicon_svg"),
    ("GET",  re.compile(r"^/squirrel\.svg$"),                         "spa_squirrel_svg"),
    ("GET",  re.compile(r"^/(?P<name>icon-\d+\.png)$"),               "spa_root_icon"),
    ("GET",  re.compile(r"^/apple-touch-icon\.png$"),                 "spa_apple_touch_icon"),
    ("GET",  re.compile(r"^/manifest\.json$"),                        "spa_manifest"),
    ("GET",  re.compile(r"^/assets/(?P<rel>[A-Za-z0-9._/-]+)$"),      "spa_asset"),
    ("GET",  re.compile(r"^/icons/(?P<rel>[A-Za-z0-9._/-]+)$"),       "spa_icon"),
    # Anything else GET → serve the SPA shell (client-side router takes over).
    ("GET",  re.compile(r"^/.*$"),                                    "spa_shell"),
]


# ─── HTTP handler ────────────────────────────────────────────────────────────


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "Squirrel/web-ui-react"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    # method gating
    def do_GET(self) -> None: self._dispatch("GET")
    def do_POST(self) -> None: self._dispatch("POST")
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_common_headers(no_store=True)
        self.send_header("Allow", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()
        _log_request("OPTIONS", self.path, 204)
    def do_HEAD(self) -> None: self._method_not_allowed("HEAD")
    def do_PUT(self) -> None: self._dispatch("PUT")
    def do_DELETE(self) -> None: self._dispatch("DELETE")
    def do_PATCH(self) -> None: self._dispatch("PATCH")

    def _method_not_allowed(self, method: str) -> None:
        _log_request(method, self.path, 405)
        self.send_response(405)
        self._send_common_headers(no_store=True)
        self.send_header("Allow", "GET, POST, PUT, OPTIONS")
        self.end_headers()

    # Origins allowed to call the JSON API from a webview / browser. Localhost
    # only — the Tauri popup (tauri://localhost), the vite dev server (:1420
    # for the desktop, :5173 for the browser SPA), and the backend itself
    # (:3939). Echo back when the request's Origin matches; omit otherwise so
    # we never advertise `*` to arbitrary hosts.
    _ALLOWED_CORS_ORIGINS = frozenset({
        "tauri://localhost",
        "http://localhost:1420",
        "http://localhost:5173",
        "http://127.0.0.1:1420",
        "http://127.0.0.1:5173",
        "http://localhost:3939",
        "http://127.0.0.1:3939",
    })

    def _send_common_headers(self, *, no_store: bool) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        if no_store:
            self.send_header("Cache-Control", "no-store")
        origin = self.headers.get("Origin")
        if origin and origin in self._ALLOWED_CORS_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _token_ok(self) -> bool:
        """Constant-time compare of the X-Squirrel-Token header to the stored
        token (R-2.7). False when the header is absent. The token value is
        never logged or echoed (R-2.9)."""
        presented = self.headers.get("X-Squirrel-Token")
        if presented is None or TOKEN is None:
            return False
        return hmac.compare_digest(presented, TOKEN)

    def _send_unauthorized(self, method: str) -> None:
        """401 with an empty body (R-2.6). Logs the refusal without the token
        value (R-2.9)."""
        _log_request(method, self.path, 401)
        self.send_response(401)
        self._send_common_headers(no_store=True)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _dispatch(self, method: str) -> None:
        path = self.path
        if not is_safe_request_path(path):
            return self._send_plain_error(400, "Bad path.")
        bare = path.split("?", 1)[0]
        # R-2.6/R-2.7/R-2.8: gate API routes on a constant-time token match.
        # The SPA shell and static assets are exempt so the browser can load
        # the app via the open-web token URL before any API call is made.
        # /api/_handshake runs its own contract and is always exempt.
        if (bare.startswith("/api/") and bare != "/api/_handshake"
                and _auth_required() and not self._token_ok()):
            return self._send_unauthorized(method)
        for m, pattern, fn_name in ROUTES:
            if m != method:
                continue
            match = pattern.match(bare)
            if match is None:
                continue
            handler_fn: Callable = getattr(self, fn_name)
            try:
                handler_fn(**match.groupdict())
            except _UserError as ue:
                self._send_plain_error(ue.status, ue.message)
            except Exception as exc:
                _log_exception(exc)
                if bare.startswith("/api/"):
                    self._send_json_error(500, "Something went wrong. Please try again.")
                else:
                    self._send_html_error(500, "Something went wrong.")
            return
        if bare.startswith("/api/"):
            self._send_json_error(404, "Not found.")
        else:
            self._serve_spa_shell()

    # ── Response helpers ────────────────────────────────────────────────────

    def _send_json(self, payload: Any, *, status: int = 200,
                   extra_set_cookie=None, clear_cookie_name=None) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        _log_request(self.command, self.path, status)
        self.send_response(status)
        self._send_common_headers(no_store=True)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if extra_set_cookie:
            _set_cookie(self, *extra_set_cookie)
        if clear_cookie_name:
            _clear_cookie(self, clear_cookie_name)
        self.end_headers()
        self.wfile.write(body)

    def _send_json_error(self, status: int, message: str) -> None:
        body = json.dumps({"error": message}).encode("utf-8")
        _log_request(self.command, self.path, status)
        self.send_response(status)
        self._send_common_headers(no_store=True)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html_error(self, status: int, message: str) -> None:
        page = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Squirrel</title></head><body style='font-family:system-ui;"
            "padding:2rem;text-align:center'><h1>Oh no</h1><p>"
            + message.replace("<", "&lt;") + "</p><p><a href='/'>Back to home</a></p>"
            "</body></html>"
        )
        body = page.encode("utf-8")
        _log_request(self.command, self.path, status)
        self.send_response(status)
        self._send_common_headers(no_store=True)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_plain_error(self, status: int, message: str) -> None:
        if self.path.startswith("/api/"):
            self._send_json_error(status, message)
        else:
            self._send_html_error(status, message)

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _UserError(400, "We could not understand that request.")

    def _context(self) -> tuple[VaultContext, dict[str, str]]:
        cookies = parse_cookie_header(self.headers.get("Cookie"))
        ctx = resolve_vault(cookies.get(WORKSPACE_COOKIE))
        if ctx is None:
            raise _UserError(
                503,
                "No workspace is set up yet. Run `squirrel vaults add <name> <path>`.",
            )
        return ctx, cookies

    # Drop all cached vault-scan entries for the active vault. Called from
    # write handlers so the next /api/home reflects the user's own write
    # immediately (R-9.9) instead of waiting up to TTL.
    def _invalidate_vault_cache(self, ctx: "VaultContext") -> None:
        import cache
        cache.invalidate(str(ctx.active.path))

    # ── /api/_handshake — runtime trust probe ───────────────────────────────

    def api_handshake(self) -> None:
        """Runtime Trust Handshake endpoint (R-3.1..R-3.4).

        - dev mode            → 200 {"mode": "dev"} regardless of header (R-3.3)
        - matching token      → 200 {"token_echo": "<hex>"} (R-3.1)
        - missing/mismatched  → 401 empty body, no token leaked (R-3.2, R-3.4)
        """
        if DEV_MODE:
            self._send_json({"mode": "dev"})
            return
        if _auth_required() and self._token_ok():
            self._send_json({"token_echo": TOKEN})
            return
        self._send_unauthorized("GET")

    # ── /api/me — bootstrap ─────────────────────────────────────────────────

    def api_me(self) -> None:
        ctx, cookies = self._context()
        _ensure_scratch_pad_once(ctx.active.path)
        _ensure_mind_journal_once(ctx.active.path, ctx.active.name)
        payload = {
            "active_workspace": _vault_to_dict(ctx.active),
            "workspaces": [_vault_to_dict(v) for v in ctx.all],
            "multi_vault": ctx.multi,
            "theme": cookies.get(THEME_COOKIE) or "auto",
            "version": _detect_version(),
            "notifications": config_loader.load_notifications_settings(
                config_loader.DEFAULT_CONFIG_PATH
            ),
        }
        if ctx.cookie_was_stale:
            self._send_json(payload, clear_cookie_name=WORKSPACE_COOKIE)
        else:
            self._send_json(payload)

    def api_vaults_list(self) -> None:
        ctx, _ = self._context()
        self._send_json([_vault_to_dict(v) for v in ctx.all])

    def api_set_vault(self) -> None:
        payload = self._read_json_body()
        name = (payload.get("name") or "").strip()
        if not name:
            raise _UserError(400, "Pick a workspace.")
        try:
            config_loader.get_vault(name=name)
        except config_loader.VaultNotFoundError:
            raise _UserError(404, "We could not find that workspace.")
        self._send_json({"success": True, "name": name},
                        extra_set_cookie=(WORKSPACE_COOKIE, name))

    def api_set_theme(self) -> None:
        payload = self._read_json_body()
        theme = (payload.get("theme") or "auto").strip()
        if theme not in ("auto", "light", "dark"):
            raise _UserError(400, "Theme must be auto, light, or dark.")
        if theme == "auto":
            self._send_json({"success": True, "theme": "auto"},
                            clear_cookie_name=THEME_COOKIE)
        else:
            self._send_json({"success": True, "theme": theme},
                            extra_set_cookie=(THEME_COOKIE, theme))

    # ── /api/home — dashboard bundle ────────────────────────────────────────

    def api_home(self) -> None:
        ctx, _ = self._context()
        from status_aggregator import aggregate_status
        from deadline_scanner import scan_vault_deadlines
        from focus_picker import get_manual_focus
        import cache

        vault_key = str(ctx.active.path)
        try:
            status = cache.get_or_compute(
                vault_key, "status",
                lambda: aggregate_status(ctx.active.path),
            )
        except Exception:
            status = {"wip": {"projects": []}, "recommended_focus": None}
        try:
            deadlines = cache.get_or_compute(
                vault_key, "deadlines",
                lambda: scan_vault_deadlines(ctx.active.path),
            )
        except Exception:
            deadlines = {"by_urgency": {}}
        try:
            manual_focus = get_manual_focus(ctx.active.path)
        except Exception:
            manual_focus = {"today": None, "today_pm": None, "week": None}

        focus = status.get("recommended_focus") or {}
        focus_payload = None
        if focus.get("project"):
            focus_payload = {
                "slug": focus["project"],
                "title": vocabulary.project_title(focus["project"], ctx.active.path),
                "next_action": focus.get("next_action", "") or "",
                "reason": focus.get("reason", "") or "",
            }

        pressing = []
        for lvl in ("overdue", "critical", "urgent"):
            for item in deadlines.get("by_urgency", {}).get(lvl, []):
                # `last_worked` = epoch seconds of the most recent shutdown
                # note (`/sq-end`) on this task. Carries the "when did I last
                # sit down with this" semantic — more meaningful than file
                # mtime, which fires on any save.
                last_worked: Optional[float] = None
                ts = item.get("last_shutdown")
                if ts:
                    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
                        try:
                            last_worked = datetime.datetime.strptime(ts, fmt).timestamp()
                            break
                        except ValueError:
                            continue
                # Classify the entity behind this pressing entry so the
                # frontend can render a Project/Task/Note badge and route a
                # project-page hit to /projects/{slug} instead of /notes/{id}.
                kind = "note"
                project_slug: Optional[str] = None
                path_str = item.get("path")
                if path_str:
                    try:
                        kind = _classify_kind(ctx.active.path, pathlib.Path(path_str))
                        if kind == "project":
                            project_slug = pathlib.Path(path_str).stem
                    except Exception:
                        pass
                entry = {
                    "id": item.get("id", ""),
                    "title": item.get("title", item.get("id", "")),
                    "deadline": item.get("deadline", ""),
                    "urgency": lvl,
                    "urgency_label": vocabulary.urgency_label(lvl),
                    "is_overdue": bool(item.get("is_overdue")),
                    "hours_left": item.get("hours_left"),
                    "days_overdue": item.get("days_overdue"),
                    "last_worked": last_worked,
                    "kind": kind,
                }
                if project_slug:
                    entry["slug"] = project_slug
                pressing.append(entry)

        projects = []
        for p in status.get("wip", {}).get("projects", []):
            slug = p.get("id", "")
            projects.append({
                "slug": slug,
                "title": vocabulary.project_title(slug, ctx.active.path),
                "percent_done": p.get("intents", {}).get("percent_done", 0),
                "delivered": bool(p.get("delivered", False)),
                "deadline": p.get("deadline"),
                "last_activity": p.get("last_activity"),
                "active_intent": p.get("active_intent"),
                "kind": "project",
            })

        try:
            from reminder_scanner import scan_vault_reminders
            rem = cache.get_or_compute(
                vault_key, "reminders",
                lambda: scan_vault_reminders(ctx.active.path),
            )
        except Exception:
            rem = {"approaching": [], "active": []}

        # R-3.10 — recurring Mind Journal check-in state (due / next_due).
        journal_block = {"due": False, "next_due": None}
        try:
            from mind_journal import read_journal
            j = read_journal(ctx.active.path)
            if j.get("exists"):
                journal_block = {"due": j["due"], "next_due": j["next_due"]}
        except Exception:
            pass

        # R-5.1 / R-4.3 — Quick Task Stack summary. Computed fresh (not cached) so
        # the wake-commit runs on each poll; quick tasks are excluded from the
        # cached scanners above so this does not affect their results.
        qt_block = {"active": [], "active_count": 0, "snoozed_count": 0,
                    "oldest": None, "return_blocked": False}
        try:
            from quick_task_writer import collect_quick_tasks
            qt = collect_quick_tasks(ctx.active.path)
            qt_block = {
                "active": qt["active"],
                "active_count": qt["active_count"],
                "snoozed_count": qt["snoozed_count"],
                "oldest": qt["active"][0] if qt["active"] else None,
                "return_blocked": qt["return_blocked"],
            }
        except Exception:
            pass

        self._send_json({
            "focus": focus_payload,
            "pressing": pressing[:5],
            "projects": projects,
            "manual_focus": {
                "today": manual_focus.get("today"),
                "today_pm": manual_focus.get("today_pm"),
                "week": manual_focus.get("week"),
            },
            "parakeet": _parakeet_message_for(ctx.active.path),
            "reminders": {
                "approaching_count": len(rem.get("approaching", [])),
                "active_count": len(rem.get("active", [])),
            },
            "journal": journal_block,
            "quick_tasks": qt_block,
        })

    # ── /api/focus — manual picks ───────────────────────────────────────────

    def api_focus_get(self) -> None:
        ctx, _ = self._context()
        from focus_picker import get_manual_focus
        try:
            focus = get_manual_focus(ctx.active.path)
        except Exception:
            focus = {"today": None, "today_pm": None, "week": None}
        self._send_json({
            "today": focus.get("today"),
            "today_pm": focus.get("today_pm"),
            "week": focus.get("week"),
        })

    def api_focus_put_today(self) -> None:
        body = self._read_json_body()
        slot = "today_pm" if body.get("slot") == "pm" else "today"
        self._api_focus_put(slot, body)

    def api_focus_put_week(self) -> None:
        self._api_focus_put("week")

    def _api_focus_put(self, slot: str, body: Optional[dict] = None) -> None:
        ctx, _ = self._context()
        if body is None:
            body = self._read_json_body()
        from focus_picker import (
            set_manual_focus, clear_manual_focus, get_manual_focus,
            IntentNotFound,
        )
        if body.get("clear") is True:
            clear_manual_focus(ctx.active.path, slot)
        elif body.get("project_slug") and body.get("intent_slug"):
            note_raw = body.get("note")
            note = note_raw if isinstance(note_raw, str) else None
            try:
                set_manual_focus(
                    ctx.active.path, slot,
                    body["project_slug"], body["intent_slug"],
                    note=note,
                )
            except IntentNotFound:
                self._send_json_error(404, "intent_not_found")
                return
        else:
            self._send_json_error(400, "bad_request")
            return
        self._invalidate_vault_cache(ctx)
        focus = get_manual_focus(ctx.active.path)
        self._send_json({
            "today": focus.get("today"),
            "today_pm": focus.get("today_pm"),
            "week": focus.get("week"),
        })

    def api_focus_history(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        today = datetime.date.today().isoformat()
        date_val = qs.get("date", [None])[0]
        from_val = qs.get("from", [None])[0]
        to_val   = qs.get("to",   [None])[0]
        if date_val:
            from_d = to_d = date_val
        elif from_val and to_val:
            from_d, to_d = from_val, to_val
        else:
            from_d = to_d = today
        conn = db.get_conn()
        db.init_schema(conn)
        try:
            picks = conn.execute(
                "SELECT id, vault, slot, date, project_slug, intent_slug, picked_at, cleared_at, note"
                " FROM focus_picks WHERE date BETWEEN ? AND ? ORDER BY picked_at DESC",
                (from_d, to_d),
            ).fetchall()
            sessions = conn.execute(
                "SELECT id, vault, slot, date, project_slug, intent_slug, checkin_at, checkout_at,"
                " CASE WHEN checkout_at IS NOT NULL"
                " THEN CAST((julianday(checkout_at) - julianday(checkin_at)) * 1440 AS INTEGER)"
                " ELSE NULL END AS duration_minutes"
                " FROM work_sessions WHERE date BETWEEN ? AND ? ORDER BY checkin_at DESC",
                (from_d, to_d),
            ).fetchall()
        finally:
            conn.close()
        pick_keys = ("id", "vault", "slot", "date", "project_slug", "intent_slug", "picked_at", "cleared_at", "note")
        session_keys = ("id", "vault", "slot", "date", "project_slug", "intent_slug", "checkin_at", "checkout_at", "duration_minutes")
        self._send_json({
            "picks": [dict(zip(pick_keys, r)) for r in picks],
            "sessions": [dict(zip(session_keys, r)) for r in sessions],
        })

    def api_focus_checkin(self) -> None:
        body = self._read_json_body()
        project_slug = body.get("project_slug", "")
        intent_slug = body.get("intent_slug", "")
        slot = body.get("slot", "today")
        if not project_slug or not intent_slug:
            self._send_json_error(400, "project_slug and intent_slug are required")
            return
        ctx, _ = self._context()
        today = datetime.date.today().isoformat()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = db.get_conn()
        db.init_schema(conn)
        try:
            cur = conn.execute(
                "INSERT INTO work_sessions (vault, slot, date, project_slug, intent_slug, checkin_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (ctx.active.path.name, slot, today, project_slug, intent_slug, now),
            )
            conn.commit()
            session_id = cur.lastrowid
        finally:
            conn.close()
        self._invalidate_vault_cache(ctx)
        self._send_json({"session_id": session_id})

    def _update_time_invested(self, vault_path, project_slug: str, intent_slug: str, conn) -> int:
        total = conn.execute(
            "SELECT COALESCE(SUM(CAST((julianday(checkout_at) - julianday(checkin_at)) * 1440 AS INTEGER)), 0)"
            " FROM work_sessions WHERE vault = ? AND project_slug = ? AND intent_slug = ? AND checkout_at IS NOT NULL",
            (vault_path.name, project_slug, intent_slug),
        ).fetchone()[0]
        intent_path = vault_path / "01-Proyectos-Activos" / project_slug / f"{intent_slug}.md"
        if intent_path.is_file():
            from intent_parser import write_frontmatter
            write_frontmatter(intent_path, {"time_invested_minutes": int(total)})
        return int(total)

    def api_focus_checkout(self) -> None:
        ctx, _ = self._context()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = db.get_conn()
        db.init_schema(conn)
        try:
            row = conn.execute(
                "SELECT id, project_slug, intent_slug, checkin_at FROM work_sessions"
                " WHERE vault = ? AND checkout_at IS NULL ORDER BY checkin_at DESC LIMIT 1",
                (ctx.active.path.name,),
            ).fetchone()
            if row is None:
                self._send_json_error(409, "no_open_session")
                return
            session_id, project_slug, intent_slug, checkin_at = row
            conn.execute("UPDATE work_sessions SET checkout_at = ? WHERE id = ?", (now, session_id))
            conn.commit()
            duration_minutes = conn.execute(
                "SELECT CAST((julianday(checkout_at) - julianday(checkin_at)) * 1440 AS INTEGER)"
                " FROM work_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()[0] or 0
            time_invested = self._update_time_invested(ctx.active.path, project_slug, intent_slug, conn)
        finally:
            conn.close()
        self._invalidate_vault_cache(ctx)
        self._send_json({
            "session_id": session_id,
            "duration_minutes": duration_minutes,
            "time_invested_minutes": time_invested,
        })

    def api_focus_session(self) -> None:
        ctx, _ = self._context()
        conn = db.get_conn()
        db.init_schema(conn)
        try:
            row = conn.execute(
                "SELECT project_slug, intent_slug, checkin_at FROM work_sessions"
                " WHERE vault = ? AND checkout_at IS NULL ORDER BY checkin_at DESC LIMIT 1",
                (ctx.active.path.name,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            self._send_json_error(404, "no_open_session")
            return
        project_slug, intent_slug, checkin_at = row
        self._send_json({"project_slug": project_slug, "intent_slug": intent_slug, "checkin_at": checkin_at})

    def api_focus_recalculate(self) -> None:
        ctx, _ = self._context()
        conn = db.get_conn()
        db.init_schema(conn)
        try:
            intents = conn.execute(
                "SELECT DISTINCT project_slug, intent_slug FROM work_sessions"
                " WHERE vault = ? AND checkout_at IS NOT NULL",
                (ctx.active.path.name,),
            ).fetchall()
            for project_slug, intent_slug in intents:
                self._update_time_invested(ctx.active.path, project_slug, intent_slug, conn)
        finally:
            conn.close()
        self._invalidate_vault_cache(ctx)
        self._send_json({"updated": len(intents)})

    # ── projects ────────────────────────────────────────────────────────────

    def api_projects_list(self) -> None:
        ctx, _ = self._context()
        proj_root = ctx.active.path / "01-Proyectos-Activos"
        out = []
        if proj_root.is_dir():
            for sub in sorted(proj_root.iterdir()):
                if not sub.is_dir() or sub.name.startswith("."):
                    continue
                out.append({
                    "slug": sub.name,
                    "title": vocabulary.project_title(sub.name, ctx.active.path),
                })
        self._send_json(out)

    def api_project_detail(self, slug: str) -> None:
        ctx, _ = self._context()
        proj_dir = ctx.active.path / "01-Proyectos-Activos" / slug
        if not is_path_inside(proj_dir, ctx.active.path) or not proj_dir.is_dir():
            raise _UserError(404, "We could not find that project.")
        proj_md = proj_dir / f"{slug}.md"
        body = ""
        mtime = 0.0
        if proj_md.is_file():
            body = proj_md.read_text(encoding="utf-8", errors="replace")
            mtime = proj_md.stat().st_mtime
        notes = []
        for n in sorted(
            (p for p in proj_dir.glob("*.md") if p.name != f"{slug}.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            notes.append({
                "id": n.stem,
                "title": _first_title(n.read_text(encoding="utf-8", errors="replace")) or n.stem,
                "modified_at": n.stat().st_mtime,
            })
        self._send_json({
            "slug": slug,
            "title": vocabulary.project_title(slug, ctx.active.path),
            "body": _strip_frontmatter(body),
            "raw_body": body,
            "mtime": mtime,
            "notes": notes,
        })

    def api_project_create(self) -> None:
        ctx, _ = self._context()
        payload = self._read_json_body()
        tag = (payload.get("tag") or "").strip()
        project_type = (payload.get("type") or "").strip()
        project_name = (payload.get("name") or "").strip()
        if not tag or not project_type:
            raise _UserError(400, "tag and type are required.")
        from new_project_writer import NewProjectError, create_project
        try:
            result = create_project(
                tag=tag,
                tipo=project_type,
                name=project_name,
                vault_name=ctx.active.name,
                deadline=(payload.get("deadline") or None) or None,
                stakeholders=payload.get("stakeholders") or None,
                description=payload.get("description") or "",
                first_intent_tag=payload.get("first_intent_tag") or None,
                first_intent_title=payload.get("first_intent_title") or "",
                force=bool(payload.get("force") or False),
            )
        except NewProjectError as e:
            status_map = {
                "NO_CONFIG":      500,
                "VAULT_MISSING":  500,
                "VAULT_UNKNOWN":  500,
                "INVALID_TAG":    400,
                "INVALID_TIPO":   400,
                "INVALID_DEADLINE": 400,
                "INVALID_INTENT_TAG": 400,
                "INTENT_TAG_MISMATCH": 400,
                "PROJECT_EXISTS": 409,
                "WIP_CAPACITY":   409,
            }
            self._send_json(
                {"error": e.message, "code": e.code},
                status=status_map.get(e.code, 400),
            )
            return
        self._invalidate_vault_cache(ctx)
        self._send_json({
            "success": True,
            "slug": result["tag"],
            "type": result["type"],
            "deadline": result["deadline"],
            "wip_count": result["wip_count"],
            "wip_max": result["wip_max"],
            "over_cap": result["over_cap"],
            "intent_id": (
                pathlib.Path(result["intent_path"]).stem
                if result.get("intent_path") else None
            ),
        })

    def api_project_save(self, slug: str) -> None:
        ctx, _ = self._context()
        proj_md = ctx.active.path / "01-Proyectos-Activos" / slug / f"{slug}.md"
        if not is_path_inside(proj_md, ctx.active.path) or not proj_md.is_file():
            raise _UserError(404, "We could not find that project.")
        self._save_with_mtime(proj_md, ctx.active.path, self._read_json_body())
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "slug": slug,
                         "mtime": proj_md.stat().st_mtime})

    def api_project_delete(self, slug: str) -> None:
        ctx, _ = self._context()
        proj_md = ctx.active.path / "01-Proyectos-Activos" / slug / f"{slug}.md"
        if not is_path_inside(proj_md, ctx.active.path) or not proj_md.is_file():
            raise _UserError(404, "We could not find that project.")
        text = proj_md.read_text(encoding="utf-8", errors="replace")
        fm = _parse_frontmatter_simple(text)
        if str(fm.get("protected", "")).lower() in ("true", "1", "yes"):
            raise _UserError(403, "PROJECT_PROTECTED")
        import shutil
        project_dir = ctx.active.path / "01-Proyectos-Activos" / slug
        if not is_path_inside(project_dir, ctx.active.path):
            raise _UserError(403, "That path is outside your workspace.")
        shutil.rmtree(project_dir)
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "slug": slug})

    def api_project_set_status(self, slug: str) -> None:
        """Move a project between board columns by rewriting frontmatter.

        Accepts `deadline` (YYYY-MM-DD, or null to clear) and/or `delivered`
        (bool). The board's THIS WEEK / ACTIVE / LATER lanes are deadline-driven;
        DELIVERED is the `delivered` flag. Only these two fields are touched —
        the rest of the project page is preserved verbatim.
        """
        ctx, _ = self._context()
        proj_md = ctx.active.path / "01-Proyectos-Activos" / slug / f"{slug}.md"
        if not is_path_inside(proj_md, ctx.active.path) or not proj_md.is_file():
            raise _UserError(404, "We could not find that project.")
        payload = self._read_json_body()
        updates: dict = {}
        if "deadline" in payload:
            dl = payload.get("deadline")
            if dl is None or (isinstance(dl, str) and not dl.strip()):
                updates["deadline"] = None
            else:
                dl = str(dl).strip()
                if not re.match(r"^\d{4}-\d{2}-\d{2}$", dl):
                    raise _UserError(400, "deadline must be a YYYY-MM-DD date.")
                updates["deadline"] = dl
        if "delivered" in payload:
            updates["delivered"] = "true" if bool(payload.get("delivered")) else None
        if not updates:
            raise _UserError(400, "Nothing to update — send a deadline and/or delivered.")
        text = proj_md.read_text(encoding="utf-8", errors="replace")
        new_text = _update_frontmatter_fields(text, updates)
        tmp = proj_md.with_suffix(proj_md.suffix + ".tmp")
        tmp.write_text(new_text, encoding="utf-8")
        os.replace(tmp, proj_md)
        self._invalidate_vault_cache(ctx)
        fm = _parse_frontmatter_simple(new_text)
        self._send_json({
            "success": True,
            "slug": slug,
            "deadline": fm.get("deadline"),
            "delivered": str(fm.get("delivered", "")).strip().lower() in ("true", "1", "yes"),
        })

    def api_intent_create(self) -> None:
        ctx, _ = self._context()
        payload = self._read_json_body()
        project_slug = (payload.get("project_slug") or "").strip()
        tag = (payload.get("tag") or "").strip().upper()
        title = (payload.get("title") or "").strip()
        deadline = (payload.get("deadline") or "").strip()
        reminder_date = (payload.get("reminder_date") or "").strip()
        if not project_slug or not tag or not title:
            raise _UserError(400, "project_slug, tag, and title are required.")
        _INTENT_TAG_RE = re.compile(r"^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$")
        if not _INTENT_TAG_RE.match(tag):
            raise _UserError(422, f"{tag!r} is not a valid intent tag (UPPERCASE, dash-separated).")
        # filename is the .md stem; falls back to tag for backward compat
        filename = (payload.get("filename") or "").strip().upper() or tag
        if not _INTENT_TAG_RE.match(filename):
            raise _UserError(422, f"{filename!r} is not a valid filename (UPPERCASE, dash-separated, e.g. TRABAJO-PROYECTO-A).")
        vault_root = ctx.active.path
        project_dir = vault_root / "01-Proyectos-Activos" / project_slug
        if not is_path_inside(project_dir, vault_root) or not project_dir.is_dir():
            raise _UserError(404, "Project not found.")
        intent_path = project_dir / f"{filename}.md"
        if not is_path_inside(intent_path, vault_root):
            raise _UserError(403, "That path is outside your workspace.")
        if intent_path.exists():
            raise _UserError(409, f"A file named '{filename}.md' already exists in this project.")
        template_candidates = [
            vault_root / "agent-pack" / "templates" / "intent.md",
            _REPO / "agent-pack" / "templates" / "intent.md",
        ]
        template_text: Optional[str] = None
        for tp in template_candidates:
            if tp.is_file():
                template_text = tp.read_text(encoding="utf-8")
                break
        if template_text is None:
            raise _UserError(500, "Intent template not found. Ensure agent-pack/templates/intent.md exists.")
        today = datetime.date.today().isoformat()
        rendered = (
            template_text
            .replace("<TAG>", tag)
            .replace("<PROJECT>", project_slug)
            .replace("<YYYY-MM-DD>", today)
            .replace("<Título corto>", title or tag)
        )
        if not deadline:
            rendered = "\n".join(
                line for line in rendered.splitlines()
                if not line.strip().startswith("deadline:")
            ) + "\n"
        else:
            rendered = rendered.replace(
                "deadline: <YYYY-MM-DD>   # ISO date; omit if no hard deadline",
                f"deadline: {deadline}",
            )
        tmp = intent_path.with_suffix(".md.tmp")
        tmp.write_text(rendered, encoding="utf-8")
        os.replace(tmp, intent_path)
        if reminder_date:
            try:
                from reminder_writer import write_reminder_date
                write_reminder_date(intent_path, reminder_date)
            except Exception as exc:
                _log_exception(exc)
                # Non-fatal: file was created; reminder is just missing
        self._invalidate_vault_cache(ctx)
        self._send_json(
            {"success": True, "path": str(intent_path.relative_to(vault_root))},
            status=201,
        )

    # ── notes ───────────────────────────────────────────────────────────────

    def api_note_detail(self, note_id: str) -> None:
        ctx, _ = self._context()
        note_path = _find_note(ctx.active.path, note_id)
        if note_path is None:
            raise _UserError(404, "We could not find that note.")
        text = note_path.read_text(encoding="utf-8", errors="replace")
        self._send_json({
            "id": note_id,
            "title": _first_title(text) or note_id,
            "body": _strip_frontmatter(text),
            "raw_body": text,
            "mtime": note_path.stat().st_mtime,
            "project_slug": note_path.parent.name,
            "kind": _classify_kind(ctx.active.path, note_path),
        })

    def api_note_save(self, note_id: str) -> None:
        ctx, _ = self._context()
        note_path = _find_note(ctx.active.path, note_id)
        if note_path is None:
            raise _UserError(404, "We could not find that note.")
        self._save_with_mtime(note_path, ctx.active.path, self._read_json_body())
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "id": note_id,
                         "mtime": note_path.stat().st_mtime})

    def api_note_create(self) -> None:
        ctx, _ = self._context()
        payload = self._read_json_body()
        text = (payload.get("text") or "").strip()
        if not text:
            raise _UserError(400, "Please write something before saving.")
        project_slug = payload.get("project_slug")
        reminder_date = (payload.get("reminder_date") or "").strip()
        if project_slug in ("", "unfiled", None):
            project_slug = None
        from capture_writer import write_capture
        try:
            path = write_capture(ctx.active.path, project_slug, text)
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not save your note. Please try again.")
        if reminder_date:
            try:
                from reminder_writer import write_reminder_date
                write_reminder_date(path, reminder_date)
            except Exception as exc:
                _log_exception(exc)
                # Non-fatal: capture was created; reminder is just missing
        self._invalidate_vault_cache(ctx)
        self._send_json({
            "success": True,
            "id": path.stem,
            "project_slug": project_slug or "unfiled",
        })

    def _save_with_mtime(self, target, vault_root, payload) -> None:
        if not is_path_inside(target, vault_root):
            raise _UserError(403, "That file is outside your workspace.")
        body = payload.get("body")
        if body is None:
            raise _UserError(400, "Missing the note body.")
        client_mtime = payload.get("mtime")
        if client_mtime is None:
            raise _UserError(400, "Missing the file timestamp. Reload and try again.")
        try:
            current_mtime = target.stat().st_mtime
        except OSError:
            raise _UserError(404, "We could not find that file.")
        try:
            if abs(float(client_mtime) - current_mtime) > 0.001:
                conflict_body = target.read_text(encoding="utf-8", errors="replace")
                self._send_json({
                    "current_body": conflict_body,
                    "current_mtime": current_mtime,
                    "message": "Someone else just edited this. Pick which version to keep.",
                }, status=409)
                # _send_json returned; caller knows we replied.
                # Raise to short-circuit downstream save attempt.
                raise _ResponseSent()
        except (TypeError, ValueError):
            raise _UserError(400, "The file timestamp looks wrong. Reload and try again.")
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(str(body), encoding="utf-8")
        os.replace(tmp, target)

    # ── mind journal ────────────────────────────────────────────────────────

    def api_journal_get(self) -> None:
        ctx, _ = self._context()
        _ensure_mind_journal_once(ctx.active.path, ctx.active.name)
        from mind_journal import read_journal
        try:
            data = read_journal(ctx.active.path)
        except Exception as exc:
            _log_exception(exc)
            data = {"exists": False}
        self._send_json(data)

    def api_journal_entry(self) -> None:
        ctx, _ = self._context()
        from mind_journal import VALID_MOODS, append_entry, find_journal
        payload = self._read_json_body()
        mood = (payload.get("mood") or "").strip().lower()
        if mood not in VALID_MOODS:  # R-3.4
            raise _UserError(400, "INVALID_MOOD")
        mind = (payload.get("mind") or "").strip()
        doing = (payload.get("doing") or "").strip()
        journal_path = find_journal(ctx.active.path)
        if journal_path is None:  # R-3.7
            raise _UserError(404, "NO_JOURNAL")
        try:
            append_entry(journal_path, mind, doing, mood)
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not save your journal entry.")
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True}, status=201)

    def api_journal_config(self) -> None:
        ctx, _ = self._context()
        from mind_journal import find_journal, write_config
        payload = self._read_json_body()
        interval = None
        if "interval_hours" in payload:
            try:
                interval = float(payload.get("interval_hours"))
            except (TypeError, ValueError):
                interval = -1
            if interval <= 0:  # R-3.9
                raise _UserError(400, "interval_hours must be a positive number.")
            # Keep whole numbers tidy (4 not 4.0) in frontmatter.
            interval = int(interval) if interval == int(interval) else interval
        start = payload.get("waking_start")
        end = payload.get("waking_end")
        for label, val in (("waking_start", start), ("waking_end", end)):
            if val is not None and not re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", str(val).strip()):
                raise _UserError(400, f"{label} must be HH:MM.")  # R-3.9
        journal_path = find_journal(ctx.active.path)
        if journal_path is None:
            raise _UserError(404, "NO_JOURNAL")
        try:
            write_config(
                journal_path,
                interval_hours=interval,
                waking_start=start.strip() if isinstance(start, str) else None,
                waking_end=end.strip() if isinstance(end, str) else None,
            )
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not update journal settings.")
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True})

    # ── reminders / deadlines / history / search / parakeet ────────────────

    def api_reminders(self) -> None:
        ctx, _ = self._context()
        from reminder_scanner import scan_vault_reminders
        try:
            data = scan_vault_reminders(ctx.active.path)
        except Exception:
            data = {"approaching": [], "active": []}
        self._send_json({
            "approaching": data.get("approaching", []),
            "active": data.get("active", []),
        })

    def api_reminder_dismiss(self, note_id: str) -> None:
        ctx, _ = self._context()
        note_path = _find_note(ctx.active.path, note_id)
        if note_path is None:
            raise _UserError(404, "We could not find that item.")
        from reminder_writer import dismiss_reminder
        try:
            dismiss_reminder(note_path)
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not dismiss reminder.")
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "id": note_id})

    def api_reminder_snooze(self, note_id: str) -> None:
        ctx, _ = self._context()
        note_path = _find_note(ctx.active.path, note_id)
        if note_path is None:
            raise _UserError(404, "We could not find that item.")
        payload = self._read_json_body()
        until = (payload.get("until") or "").strip()
        if not until:
            raise _UserError(400, "until date is required.")
        try:
            datetime.date.fromisoformat(until)
        except ValueError:
            raise _UserError(422, "until must be YYYY-MM-DD.")
        from reminder_writer import snooze_reminder
        try:
            snooze_reminder(note_path, until)
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not snooze reminder.")
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "id": note_id, "snoozed_until": until})

    # ── /api/quick-tasks — Quick Task Stack ─────────────────────────────────

    def api_quick_tasks_list(self) -> None:
        """GET — scan + capacity-aware wake-commit (R-2.1, R-2.7, R-4.2–R-4.5)."""
        ctx, _ = self._context()
        from quick_task_writer import collect_quick_tasks
        try:
            data = collect_quick_tasks(ctx.active.path)
        except Exception as exc:
            _log_exception(exc)
            data = {"active": [], "snoozed": [], "active_count": 0,
                    "snoozed_count": 0, "limit": 5, "return_blocked": False}
        self._send_json(data)

    def api_quick_task_create(self) -> None:
        """POST — create a Quick Task (R-1.2, R-1.3, R-1.5, R-2.3, R-2.4)."""
        ctx, _ = self._context()
        payload = self._read_json_body()
        text = (payload.get("text") or "").strip()
        if not text:
            raise _UserError(400, "Please write the quick task before saving.")
        from quick_task_writer import create_quick_task, QuickTaskError
        try:
            qt_id = create_quick_task(ctx.active.path, text)
        except QuickTaskError as e:
            if e.code == "QUICK_TASK_LIMIT_REACHED":
                # R-2.3 / R-2.4: hard cap — block until one is cleared.
                return self._send_json({"error": "QUICK_TASK_LIMIT_REACHED"}, status=409)
            raise _UserError(400, "Could not add the quick task.")
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not add the quick task. Please try again.")
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "id": qt_id}, status=201)

    def api_quick_task_complete(self, qt_id: str) -> None:
        """PATCH — mark a Quick Task done (R-3.1, R-3.6)."""
        ctx, _ = self._context()
        from quick_task_writer import complete_quick_task, resolve_quick_task_path
        path = resolve_quick_task_path(ctx.active.path, qt_id)
        if path is None:
            raise _UserError(404, "We could not find that quick task.")
        try:
            complete_quick_task(path)
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not complete the quick task.")
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "id": qt_id})

    def api_quick_task_delete(self, qt_id: str) -> None:
        """DELETE — remove a Quick Task (R-3.2, R-3.6)."""
        ctx, _ = self._context()
        from quick_task_writer import delete_quick_task, resolve_quick_task_path
        path = resolve_quick_task_path(ctx.active.path, qt_id)
        if path is None:
            raise _UserError(404, "We could not find that quick task.")
        try:
            delete_quick_task(path)
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not delete the quick task.")
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "id": qt_id})

    def api_quick_task_snooze(self, qt_id: str) -> None:
        """PATCH — snooze a Quick Task (R-3.3, R-3.4, R-3.5)."""
        ctx, _ = self._context()
        from quick_task_writer import (
            snooze_quick_task, resolve_quick_task_path, QuickTaskError,
        )
        path = resolve_quick_task_path(ctx.active.path, qt_id)
        if path is None:
            raise _UserError(404, "We could not find that quick task.")
        until = (self._read_json_body().get("until") or "1h").strip() or "1h"
        try:
            wake_iso = snooze_quick_task(path, until)
        except QuickTaskError as e:
            if e.code == "QUICK_TASK_SNOOZE_LIMIT":
                return self._send_json({"error": "QUICK_TASK_SNOOZE_LIMIT"}, status=409)
            raise _UserError(400, "Could not snooze the quick task.")
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not snooze the quick task.")
        self._invalidate_vault_cache(ctx)
        self._send_json({"success": True, "id": qt_id, "snoozed_until": wake_iso})

    def api_reveal(self) -> None:
        # The server already binds to 127.0.0.1 by default; this extra check
        # makes the contract explicit so a future --lan toggle can't silently
        # expose a shell-out endpoint to the network.
        client_host = self.client_address[0] if self.client_address else ""
        if client_host not in ("127.0.0.1", "::1"):
            raise _UserError(403, "Reveal only works on localhost.")
        ctx, _ = self._context()
        payload = self._read_json_body()
        note_id = (payload.get("id") or "").strip()
        target = _find_note(ctx.active.path, note_id)
        if target is None:
            raise _UserError(404, "We could not find that item.")
        parent = target.parent
        if not is_path_inside(parent, ctx.active.path):
            raise _UserError(400, "Path is outside the active vault.")
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(parent)], check=False)
            elif sys.platform.startswith("win"):
                subprocess.run(["explorer", str(parent)], check=False)
            else:
                subprocess.run(["xdg-open", str(parent)], check=False)
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not open the folder.")
        self._send_json({"success": True, "path": str(parent)})

    def api_deadlines(self) -> None:
        ctx, _ = self._context()
        from deadline_scanner import scan_vault_deadlines
        try:
            data = scan_vault_deadlines(ctx.active.path)
        except Exception:
            data = {"by_urgency": {}}
        groups: dict[str, list] = {"Today / Tomorrow": [], "This week": [], "Later": []}
        for lvl, items in data.get("by_urgency", {}).items():
            label = vocabulary.urgency_label(lvl)
            target = groups.setdefault(label, [])
            for it in items:
                target.append({
                    "id": it.get("id", ""),
                    "title": it.get("title", it.get("id", "")),
                    "deadline": it.get("deadline", ""),
                    "is_overdue": bool(it.get("is_overdue")),
                    "hours_left": it.get("hours_left"),
                    "days_overdue": it.get("days_overdue"),
                })
        self._send_json(
            [{"label": label, "items": items} for label, items in groups.items() if items]
            or [{"label": "Pressing", "items": []}]
        )

    def api_history(self) -> None:
        ctx, _ = self._context()
        out = []
        candidates = []
        for md in ctx.active.path.rglob("*.md"):
            rel = md.relative_to(ctx.active.path)
            if any(part.startswith(".") for part in rel.parts):
                continue
            candidates.append(md)
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for p in candidates[:30]:
            parent = p.parent.name
            is_proj_page = (p.name == f"{parent}.md")
            out.append({
                "kind": "project" if is_proj_page else "note",
                "slug": parent if is_proj_page else None,
                "note_id": None if is_proj_page else p.stem,
                "title": vocabulary.project_title(parent, ctx.active.path)
                         if is_proj_page else p.stem,
                "modified_at": p.stat().st_mtime,
            })
        self._send_json(out)

    def api_search(self) -> None:
        ctx, _ = self._context()
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        q = (qs.get("q", [""])[0] or "").strip()
        if not q:
            self._send_json([])
            return
        hits = []
        needle = q.lower()
        for md in ctx.active.path.rglob("*.md"):
            rel = md.relative_to(ctx.active.path)
            if any(part.startswith(".") for part in rel.parts):
                continue
            try:
                text = md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if needle not in text.lower():
                continue
            snippet = []
            for line in text.splitlines():
                if needle in line.lower():
                    snippet.append(line.strip())
                if len(snippet) >= 3:
                    break
            hits.append({
                "id": md.stem,
                "title": _first_title(text) or md.stem,
                "snippet_lines": snippet,
                "project_slug": md.parent.name,
            })
            if len(hits) >= 40:
                break
        self._send_json(hits)

    def api_parakeet(self) -> None:
        ctx, _ = self._context()
        self._send_json({"message": _parakeet_message_for(ctx.active.path)})

    # R-9.10 — observability for the vault-scan cache; intended for
    # troubleshooting and the manual smoke test in docs/lld/.
    def api_cache_stats(self) -> None:
        import cache
        self._send_json(cache.stats_snapshot())

    # ── /api/settings/notifications — story 5.3 ────────────────────────────

    def api_settings_notifications(self) -> None:
        payload = self._read_json_body()
        in_app = payload.get("in_app")
        os_popups = payload.get("os_popups")
        if in_app is None or os_popups is None:
            raise _UserError(400, "Both in_app and os_popups are required.")
        # R-4.1/R-4.3: sound is optional; reject anything outside the curated set.
        sound = payload.get("sound")
        if sound is not None and sound not in config_loader.VALID_NOTIFICATION_SOUNDS:
            raise _UserError(
                400,
                f"sound must be one of {list(config_loader.VALID_NOTIFICATION_SOUNDS)}.",
            )
        # R-4.2: preserve previously persisted sound when payload omits it.
        if sound is None:
            sound = config_loader.load_notifications_settings()["sound"]
        config_loader.save_notifications_settings(
            config_loader.DEFAULT_CONFIG_PATH,
            in_app=bool(in_app),
            os_popups=bool(os_popups),
            sound=sound,
        )
        self._send_json({"success": True})

    # ── /api/notifications/preview — R-3.2, R-4.5 ──────────────────────────

    def api_notifications_preview(self) -> None:
        payload = self._read_json_body()
        sound = payload.get("sound")
        if sound is None:
            raise _UserError(400, "sound is required.")
        if sound not in config_loader.VALID_NOTIFICATION_SOUNDS:
            raise _UserError(
                400,
                f"sound must be one of {list(config_loader.VALID_NOTIFICATION_SOUNDS)}.",
            )
        # Silent: ack-only, no audio.
        if sound != "Silent":
            try:
                subprocess.Popen(
                    ["afplay", f"/System/Library/Sounds/{sound}.aiff"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except OSError as e:
                # Fail-soft per R-2.4: log and ack — preview should never error
                # back to the user just because audio is broken on this system.
                logging.getLogger("squirrel.server").warning(
                    "afplay spawn failed for preview (sound=%s): %s", sound, e
                )
        self._send_json({"success": True})

    # ── /api/notifications — stories 4.1, 4.2, 4.3 ─────────────────────────

    def api_notifications_list(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        unread_only = qs.get("unread", [""])[0].lower() == "true"
        limit_raw = qs.get("limit", [None])[0]
        limit: Optional[int] = None
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except ValueError:
                raise _UserError(400, "limit must be an integer.")

        conn = db.get_conn()
        db.init_schema(conn)
        try:
            total_count = conn.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
            unread_count = conn.execute(
                "SELECT COUNT(*) FROM notifications WHERE read_at IS NULL AND dismissed_at IS NULL"
            ).fetchone()[0]
            cols = "id, type, item_id, title, body, item_url, fired_at, read_at, dismissed_at"
            if unread_only:
                q = (
                    f"SELECT {cols} FROM notifications "
                    "WHERE read_at IS NULL AND dismissed_at IS NULL "
                    "ORDER BY fired_at DESC"
                )
            else:
                q = f"SELECT {cols} FROM notifications ORDER BY fired_at DESC"
            if limit is not None:
                q += f" LIMIT {limit}"
            rows = conn.execute(q).fetchall()
        finally:
            conn.close()

        items = [
            {
                "id": r[0], "type": r[1], "item_id": r[2], "title": r[3],
                "body": r[4], "item_url": r[5], "fired_at": r[6],
                "read_at": r[7], "dismissed_at": r[8],
            }
            for r in rows
        ]
        self._send_json({"items": items, "unread_count": unread_count, "total_count": total_count})

    def api_notification_read(self, nid: str) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = db.get_conn()
        db.init_schema(conn)
        try:
            conn.execute("UPDATE notifications SET read_at = ? WHERE id = ?", (now, nid))
            conn.commit()
        finally:
            conn.close()
        self._send_json({"success": True})

    def api_notification_dismiss(self, nid: str) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = db.get_conn()
        db.init_schema(conn)
        try:
            conn.execute("UPDATE notifications SET dismissed_at = ? WHERE id = ?", (now, nid))
            conn.commit()
        finally:
            conn.close()
        self._send_json({"success": True})

    def api_notifications_read_all(self) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = db.get_conn()
        db.init_schema(conn)
        try:
            cur = conn.execute(
                "UPDATE notifications SET read_at = ? WHERE read_at IS NULL", (now,)
            )
            conn.commit()
            updated = cur.rowcount
        finally:
            conn.close()
        self._send_json({"updated": updated})

    # ── SPA shell + assets ──────────────────────────────────────────────────

    def spa_shell(self) -> None:
        # Never swallow unmatched /api/* requests with the SPA HTML — that hides
        # bugs (the client tries to parse HTML as JSON and silently shows a
        # blank page). Return an explicit JSON 404 instead.
        if self.path.startswith("/api/"):
            raise _UserError(404, "No such API route.")
        self._serve_spa_shell()

    def _serve_spa_shell(self) -> None:
        index = APP_DIST / "index.html"
        if index.is_file():
            data = index.read_bytes()
            _log_request(self.command, self.path, 200)
            self.send_response(200)
            self._send_common_headers(no_store=True)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        # Friendly fallback when the React bundle is not built yet
        msg = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Squirrel — build the UI</title></head>"
            "<body style='font-family:system-ui;padding:2rem;max-width:640px;margin:auto'>"
            "<h1>The browser UI is not built yet.</h1>"
            "<p>Run:</p>"
            "<pre style='background:#f4f4f4;padding:1rem;border-radius:8px'>"
            "cd companions/web-ui/app && npm install && npm run build"
            "</pre>"
            "<p>Then refresh this page. (The JSON API is already running — "
            "you can hit <code>/api/me</code> right now.)</p>"
            "</body></html>"
        )
        body = msg.encode("utf-8")
        _log_request(self.command, self.path, 200)
        self.send_response(200)
        self._send_common_headers(no_store=True)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def spa_asset(self, rel: str) -> None:
        target = (APP_DIST / "assets" / rel).resolve()
        if not is_path_inside(target, APP_DIST):
            raise _UserError(403, "Outside bundle.")
        if not target.is_file():
            raise _UserError(404, "Not found.")
        self._serve_static_file(target)

    def spa_icon(self, rel: str) -> None:
        target = (APP_DIST / "icons" / rel).resolve()
        if not is_path_inside(target, APP_DIST):
            raise _UserError(403, "Outside bundle.")
        if not target.is_file():
            raise _UserError(404, "Not found.")
        self._serve_static_file(target)

    def spa_favicon(self) -> None:
        cand = APP_DIST / "favicon.ico"
        if cand.is_file():
            self._serve_static_file(cand)
            return
        _log_request(self.command, self.path, 204)
        self.send_response(204)
        self._send_common_headers(no_store=False)
        self.end_headers()

    def spa_favicon_svg(self) -> None:
        cand = APP_DIST / "favicon.svg"
        if cand.is_file():
            self._serve_static_file(cand)
            return
        raise _UserError(404, "Not found.")

    def spa_squirrel_svg(self) -> None:
        cand = APP_DIST / "squirrel.svg"
        if cand.is_file():
            self._serve_static_file(cand)
            return
        raise _UserError(404, "Not found.")

    def spa_root_icon(self, name: str) -> None:
        cand = (APP_DIST / name).resolve()
        if not is_path_inside(cand, APP_DIST) or not cand.is_file():
            raise _UserError(404, "Not found.")
        self._serve_static_file(cand)

    def spa_apple_touch_icon(self) -> None:
        for cand in (APP_DIST / "apple-touch-icon.png", APP_DIST / "icon-192.png"):
            if cand.is_file():
                self._serve_static_file(cand)
                return
        raise _UserError(404, "Not found.")

    def spa_manifest(self) -> None:
        cand = APP_DIST / "manifest.webmanifest"
        if not cand.is_file():
            cand = APP_DIST / "manifest.json"
        if not cand.is_file():
            raise _UserError(404, "No manifest.")
        self._serve_static_file(cand)

    def _serve_static_file(self, target: pathlib.Path) -> None:
        ctype = _content_type(target.name)
        data = target.read_bytes()
        _log_request(self.command, self.path, 200)
        self.send_response(200)
        self._send_common_headers(no_store=False)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        # Hashed bundle paths can cache for a long time.
        self.send_header("Cache-Control", "public, max-age=31536000, immutable"
                         if "assets" in target.parts else "public, max-age=600")
        self.end_headers()
        self.wfile.write(data)


# ─── Helpers ─────────────────────────────────────────────────────────────────


class _UserError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class _ResponseSent(Exception):
    """Sentinel: a JSON response has already been written by a sub-helper."""


def _vault_to_dict(v) -> dict:
    return {"name": v.name, "path": str(v.path), "default": bool(v.default)}


def _parse_frontmatter_simple(text: str) -> dict:
    """Parse YAML frontmatter from a markdown string into a flat dict.

    Only handles simple ``key: value`` lines (no nested structure). Returns
    an empty dict if the text has no frontmatter block.
    """
    lines = text.splitlines()
    if not lines or lines[0].rstrip() != "---":
        return {}
    result: dict = {}
    for line in lines[1:]:
        if line.rstrip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].rstrip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.rstrip() == "---":
                return "\n".join(lines[i + 1 :]).lstrip("\n")
    return text


def _update_frontmatter_fields(text: str, updates: dict) -> str:
    """Return *text* with frontmatter keys set or removed per *updates*.

    A string value sets/replaces the ``key: value`` line; a ``None`` value
    removes the line if present. Keys not already in the block are appended
    just before the closing ``---``. If the text has no frontmatter block, one
    is created from the set-only updates. Only simple ``key: value`` lines are
    touched; everything else is preserved verbatim.
    """
    lines = text.split("\n")
    if not lines or lines[0].rstrip() != "---":
        fm_lines = [f"{k}: {v}" for k, v in updates.items() if v is not None]
        if not fm_lines:
            return text
        return "---\n" + "\n".join(fm_lines) + "\n---\n" + text
    close = None
    for i in range(1, len(lines)):
        if lines[i].rstrip() == "---":
            close = i
            break
    if close is None:
        return text  # malformed frontmatter — leave it alone
    remaining = dict(updates)
    out = [lines[0]]
    for line in lines[1:close]:
        key = line.partition(":")[0].strip() if ":" in line else None
        if key is not None and key in remaining:
            val = remaining.pop(key)
            if val is not None:
                out.append(f"{key}: {val}")
            # val is None → drop the line (removal)
        else:
            out.append(line)
    for key, val in remaining.items():
        if val is not None:
            out.append(f"{key}: {val}")
    out.append("---")
    out.extend(lines[close + 1:])
    return "\n".join(out)


def _find_note(vault_path: pathlib.Path, note_id: str) -> Optional[pathlib.Path]:
    # Allow mixed case to support free-form filenames (e.g. "Guia-Sistema-Completo")
    # in addition to TAG-STYLE-001 ids. Still rejects "." / "/" / "..", which is
    # what matters for path-traversal safety.
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", note_id):
        return None
    for md in vault_path.rglob(f"{note_id}.md"):
        if is_path_inside(md, vault_path):
            return md
    return None


_PROJECT_PARENT_DIRS = frozenset({
    "01-Proyectos-Activos",
    "02-Parking-Lot",
    "06-Archive",
})


def _classify_kind(vault_path: pathlib.Path, md_path: pathlib.Path) -> str:
    """Return 'project' | 'project-task' | 'note' based on the vault layout.

    Mirrors the rule used by api_history (a project page is the .md file whose
    stem equals its parent folder name and sits one level inside a known
    projects directory). Anything else in those folders is a project-task;
    files outside them are notes.
    """
    try:
        rel = md_path.relative_to(vault_path)
    except ValueError:
        return "note"
    parts = rel.parts
    if len(parts) >= 3 and parts[0] in _PROJECT_PARENT_DIRS:
        folder = parts[-2]
        return "project" if md_path.stem == folder else "project-task"
    return "note"


def _first_title(text: str) -> Optional[str]:
    body = _strip_frontmatter(text)
    for line in body.splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line.rstrip())
        if m:
            return m.group(1)
    return None


def _parakeet_message_for(vault_path: pathlib.Path) -> str:
    try:
        from deadline_scanner import scan_vault_deadlines
        data = scan_vault_deadlines(vault_path)
    except Exception:
        return ""
    by = data.get("by_urgency", {})
    overdue = by.get("overdue", []) + [
        x for x in by.get("critical", []) if x.get("is_overdue")
    ]
    if overdue:
        return f"{len(overdue)} thing(s) slipped past."
    today = [x for x in by.get("critical", []) if not x.get("is_overdue")] + by.get("urgent", [])
    if today:
        return f"{len(today)} thing(s) due today or tomorrow."
    soon = by.get("soon", [])
    if soon:
        return f"{len(soon)} thing(s) coming up this week."
    return "Nothing pressing right now."


def _content_type(name: str) -> str:
    n = name.lower()
    if n.endswith(".html"): return "text/html; charset=utf-8"
    if n.endswith(".css"):  return "text/css; charset=utf-8"
    if n.endswith(".js"):   return "application/javascript; charset=utf-8"
    if n.endswith(".svg"):  return "image/svg+xml"
    if n.endswith(".png"):  return "image/png"
    if n.endswith(".ico"):  return "image/x-icon"
    if n.endswith((".webmanifest", ".json")):
        return "application/manifest+json" if n.endswith(".webmanifest") \
            else "application/json; charset=utf-8"
    if n.endswith((".woff", ".woff2")):
        return "font/woff2"
    return "application/octet-stream"


def _detect_version() -> str:
    # plugin.json was relocated under agent-pack/ during the monorepo
    # restructure; the old _REPO/.claude-plugin path now misses, which is why
    # the sidebar showed "v?". Point at the current location.
    pj = _REPO / "agent-pack" / ".claude-plugin" / "plugin.json"
    if pj.is_file():
        try:
            return json.loads(pj.read_text()).get("version", "?")
        except (json.JSONDecodeError, OSError):
            return "?"
    return "?"




# ─── Server bootstrap ────────────────────────────────────────────────────────


class _Threaded(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _startup_init() -> None:
    """Call once at server start: ensure schema exists and close orphan sessions."""
    conn = db.get_conn()
    db.init_schema(conn)
    try:
        conn.execute(
            "UPDATE work_sessions SET checkout_at = date || 'T23:59:59'"
            " WHERE checkout_at IS NULL AND date < date('now','localtime')"
        )
        conn.commit()
    finally:
        conn.close()


def build_server(host: str, port: int) -> _Threaded:
    _startup_init()
    return _Threaded((host, port), Handler)


# Backwards-compat alias for any caller / test importing `WebUIHandler`.
WebUIHandler = Handler


def _auth_fail(check: str) -> "Any":
    """Print the failed token-file check to stderr and exit non-zero (R-2.3,
    R-2.4). Never echoes the token value itself (R-2.9)."""
    print(f"squirrel-web-ui: token auth error: {check}", file=sys.stderr)
    sys.exit(2)


def _load_token_from_file(path: pathlib.Path) -> str:
    """Read a hex token from a token-file, enforcing the R-2.2/R-2.3 checks:
    file present, owned by the running user, mode 0600, and exactly 64 hex
    chars (optionally one trailing newline). Any failure exits non-zero with a
    stderr message naming the specific check. The token value is never logged."""
    try:
        st = path.stat()
    except FileNotFoundError:
        return _auth_fail(f"--token-file not found: {path}")
    except OSError as exc:
        return _auth_fail(f"--token-file unreadable ({exc.strerror}): {path}")
    mode = st.st_mode & 0o777
    if mode != 0o600:
        return _auth_fail(f"--token-file must be mode 0600, found {oct(mode)}: {path}")
    if st.st_uid != os.geteuid():
        return _auth_fail(
            f"--token-file must be owned by uid {os.geteuid()}, found {st.st_uid}: {path}"
        )
    token = path.read_text(encoding="utf-8").rstrip("\n")
    if not _TOKEN_HEX_RE.match(token):
        return _auth_fail(f"--token-file must contain exactly 64 hex chars: {path}")
    return token


def configure_auth(token: Optional[str], token_file: Optional[str]) -> None:
    """Resolve the process auth mode from the parsed CLI flags and set the
    module-level TOKEN / DEV_MODE state (R-2.1, R-2.2, R-2.4, R-2.5).

    - both flags        → exit 2 (mutually exclusive).
    - --token <hex>     → store the token, leave dev mode off.
    - --token-file <p>  → load+verify the file, store the token, dev mode off.
    - neither           → dev mode: warn once, serve loopback without auth.
    """
    global TOKEN, DEV_MODE
    if token and token_file:
        print(
            "squirrel-web-ui: --token and --token-file are mutually exclusive",
            file=sys.stderr,
        )
        sys.exit(2)
    if token:
        TOKEN = token
        DEV_MODE = False
    elif token_file:
        TOKEN = _load_token_from_file(pathlib.Path(token_file))
        DEV_MODE = False
    else:
        TOKEN = None
        DEV_MODE = True
        logging.getLogger("squirrel.server").warning("dev mode, no token auth")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="squirrel-web-ui",
        description="Squirrel web UI JSON API + React SPA shell.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--lan", action="store_true",
                        help="Bind 0.0.0.0 (LAN-reachable). DANGEROUS — no auth.")
    parser.add_argument("--token",
                        help="64-char hex shared secret (Runtime Trust Handshake). "
                             "Mutually exclusive with --token-file.")
    parser.add_argument("--token-file",
                        help="Path to a mode-0600 file holding the hex token. "
                             "Mutually exclusive with --token.")
    args = parser.parse_args()
    configure_auth(args.token, args.token_file)
    host = LAN_HOST if args.lan else DEFAULT_HOST
    if args.lan:
        print(
            "\033[33mWARNING: --lan enabled. Server is reachable on the LAN "
            "with NO authentication.\033[0m",
            file=sys.stderr,
        )
    srv = build_server(host, args.port)
    bound_host = host if host != "0.0.0.0" else _local_ip() or "0.0.0.0"
    print(f"Squirrel web UI listening on http://{bound_host}:{args.port}")
    if not (APP_DIST / "index.html").is_file():
        print("⚠️   The React bundle is not built. Visiting / will show a "
              "build-instructions page. Build with:")
        print("       cd companions/web-ui/app && npm install && npm run build")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.server_close()


def _local_ip() -> Optional[str]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None


if __name__ == "__main__":
    main()
