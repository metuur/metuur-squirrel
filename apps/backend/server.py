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
import http.server
import json
import os
import pathlib
import re
import socket
import socketserver
import sys
import traceback
import urllib.parse
from typing import Any, Callable, Optional

# Import squirrel lib (apps/cli/lib) by walking up from apps/backend/server.py to the repo root.
_REPO = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO / "apps" / "cli" / "lib"))

import config_loader  # noqa: E402
import vocabulary  # noqa: E402


# ─── Paths / constants ───────────────────────────────────────────────────────

DEFAULT_PORT = 3939
DEFAULT_HOST = "127.0.0.1"
LAN_HOST = "0.0.0.0"

# The SPA build output (Vite emits to dist/). Falls back to a friendly
# "build the app first" page when the bundle is missing.
APP_DIST = pathlib.Path(__file__).resolve().parent / "app" / "dist"

WORKSPACE_COOKIE = "squirrel_vault"
THEME_COOKIE = "squirrel_theme"

# ─── Lazy log path ───────────────────────────────────────────────────────────


def _log_path() -> pathlib.Path:
    return pathlib.Path("~/.squirrel/web-ui.log").expanduser()


LOG_PATH = _log_path()
PID_PATH = pathlib.Path("~/.squirrel/web-ui.pid").expanduser()


def _write_log_line(line: str) -> None:
    p = _log_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
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


# ─── Route table ─────────────────────────────────────────────────────────────


ROUTES: list[tuple[str, "re.Pattern[str]", str]] = [
    # ── JSON API ────────────────────────────────────────────────────────────
    ("GET",  re.compile(r"^/api/me$"),                                "api_me"),
    ("GET",  re.compile(r"^/api/vaults$"),                            "api_vaults_list"),
    ("POST", re.compile(r"^/api/vault$"),                             "api_set_vault"),
    ("GET",  re.compile(r"^/api/home$"),                              "api_home"),
    ("GET",  re.compile(r"^/api/focus$"),                             "api_focus_get"),
    ("PUT",  re.compile(r"^/api/focus/today$"),                       "api_focus_put_today"),
    ("PUT",  re.compile(r"^/api/focus/week$"),                        "api_focus_put_week"),
    ("GET",  re.compile(r"^/api/projects$"),                          "api_projects_list"),
    ("GET",  re.compile(r"^/api/projects/(?P<slug>[A-Z0-9][A-Z0-9_-]*)$"),
                                                                       "api_project_detail"),
    ("POST", re.compile(r"^/api/projects$"),                          "api_project_create"),
    ("POST", re.compile(r"^/api/projects/(?P<slug>[A-Z0-9][A-Z0-9_-]*)$"),
                                                                       "api_project_save"),
    ("GET",  re.compile(r"^/api/notes/(?P<note_id>[A-Za-z0-9][A-Za-z0-9_-]*)$"),
                                                                       "api_note_detail"),
    ("POST", re.compile(r"^/api/notes/(?P<note_id>[A-Za-z0-9][A-Za-z0-9_-]*)$"),
                                                                       "api_note_save"),
    ("POST", re.compile(r"^/api/notes$"),                             "api_note_create"),
    ("GET",  re.compile(r"^/api/deadlines$"),                         "api_deadlines"),
    ("GET",  re.compile(r"^/api/history$"),                           "api_history"),
    ("GET",  re.compile(r"^/api/search$"),                            "api_search"),
    ("GET",  re.compile(r"^/api/parakeet$"),                          "api_parakeet"),
    ("POST", re.compile(r"^/api/theme$"),                             "api_set_theme"),
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
        self.send_header("Allow", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()
        _log_request("OPTIONS", self.path, 204)
    def do_HEAD(self) -> None: self._method_not_allowed("HEAD")
    def do_PUT(self) -> None: self._dispatch("PUT")
    def do_DELETE(self) -> None: self._method_not_allowed("DELETE")
    def do_PATCH(self) -> None: self._method_not_allowed("PATCH")

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

    def _dispatch(self, method: str) -> None:
        path = self.path
        if not is_safe_request_path(path):
            return self._send_plain_error(400, "Bad path.")
        bare = path.split("?", 1)[0]
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

    # ── /api/me — bootstrap ─────────────────────────────────────────────────

    def api_me(self) -> None:
        ctx, cookies = self._context()
        payload = {
            "active_workspace": _vault_to_dict(ctx.active),
            "workspaces": [_vault_to_dict(v) for v in ctx.all],
            "multi_vault": ctx.multi,
            "theme": cookies.get(THEME_COOKIE) or "auto",
            "version": _detect_version(),
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

        try:
            status = aggregate_status(ctx.active.path)
        except Exception:
            status = {"wip": {"projects": []}, "recommended_focus": None}
        try:
            deadlines = scan_vault_deadlines(ctx.active.path)
        except Exception:
            deadlines = {"by_urgency": {}}

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
                pressing.append({
                    "id": item.get("id", ""),
                    "title": item.get("title", item.get("id", "")),
                    "deadline": item.get("deadline", ""),
                    "urgency": lvl,
                    "urgency_label": vocabulary.urgency_label(lvl),
                    "is_overdue": bool(item.get("is_overdue")),
                    "hours_left": item.get("hours_left"),
                    "days_overdue": item.get("days_overdue"),
                    "last_worked": last_worked,
                })

        projects = []
        for p in status.get("wip", {}).get("projects", []):
            slug = p.get("id", "")
            projects.append({
                "slug": slug,
                "title": vocabulary.project_title(slug, ctx.active.path),
                "percent_done": p.get("intents", {}).get("percent_done", 0),
                "deadline": p.get("deadline"),
                "last_activity": p.get("last_activity"),
                "active_intent": p.get("active_intent"),
            })

        self._send_json({
            "focus": focus_payload,
            "pressing": pressing[:5],
            "projects": projects,
            "parakeet": _parakeet_message_for(ctx.active.path),
        })

    # ── /api/focus — manual picks ───────────────────────────────────────────

    def api_focus_get(self) -> None:
        ctx, _ = self._context()
        from focus_picker import get_manual_focus
        try:
            focus = get_manual_focus(ctx.active.path)
        except Exception:
            focus = {"today": None, "week": None}
        self._send_json({"today": focus.get("today"), "week": focus.get("week")})

    def api_focus_put_today(self) -> None:
        self._api_focus_put("today")

    def api_focus_put_week(self) -> None:
        self._api_focus_put("week")

    def _api_focus_put(self, slot: str) -> None:
        ctx, _ = self._context()
        body = self._read_json_body()
        from focus_picker import (
            set_manual_focus, clear_manual_focus, get_manual_focus,
            IntentNotFound,
        )
        if body.get("clear") is True:
            clear_manual_focus(ctx.active.path, slot)
        elif body.get("project_slug") and body.get("intent_slug"):
            try:
                set_manual_focus(
                    ctx.active.path, slot,
                    body["project_slug"], body["intent_slug"],
                )
            except IntentNotFound:
                self._send_json_error(404, "intent_not_found")
                return
        else:
            self._send_json_error(400, "bad_request")
            return
        focus = get_manual_focus(ctx.active.path)
        self._send_json({"today": focus.get("today"), "week": focus.get("week")})

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
        tipo = (payload.get("tipo") or "").strip()
        if not tag or not tipo:
            raise _UserError(400, "tag and tipo are required.")
        from new_project_writer import NewProjectError, create_project
        try:
            result = create_project(
                tag=tag,
                tipo=tipo,
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
        self._send_json({
            "success": True,
            "slug": result["tag"],
            "tipo": result["tipo"],
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
        self._send_json({"success": True, "slug": slug,
                         "mtime": proj_md.stat().st_mtime})

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
        })

    def api_note_save(self, note_id: str) -> None:
        ctx, _ = self._context()
        note_path = _find_note(ctx.active.path, note_id)
        if note_path is None:
            raise _UserError(404, "We could not find that note.")
        self._save_with_mtime(note_path, ctx.active.path, self._read_json_body())
        self._send_json({"success": True, "id": note_id,
                         "mtime": note_path.stat().st_mtime})

    def api_note_create(self) -> None:
        ctx, _ = self._context()
        payload = self._read_json_body()
        text = (payload.get("text") or "").strip()
        if not text:
            raise _UserError(400, "Please write something before saving.")
        project_slug = payload.get("project_slug")
        if project_slug in ("", "unfiled", None):
            project_slug = None
        from capture_writer import write_capture
        try:
            path = write_capture(ctx.active.path, project_slug, text)
        except Exception as exc:
            _log_exception(exc)
            raise _UserError(500, "Could not save your note. Please try again.")
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

    # ── deadlines / history / search / parakeet ─────────────────────────────

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


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].rstrip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.rstrip() == "---":
                return "\n".join(lines[i + 1 :]).lstrip("\n")
    return text


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
    pj = _REPO / ".claude-plugin" / "plugin.json"
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


def build_server(host: str, port: int) -> _Threaded:
    return _Threaded((host, port), Handler)


# Backwards-compat alias for any caller / test importing `WebUIHandler`.
WebUIHandler = Handler


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="squirrel-web-ui",
        description="Squirrel web UI JSON API + React SPA shell.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--lan", action="store_true",
                        help="Bind 0.0.0.0 (LAN-reachable). DANGEROUS — no auth.")
    args = parser.parse_args()
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
