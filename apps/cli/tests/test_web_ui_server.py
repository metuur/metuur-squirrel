#!/usr/bin/env python3
"""
Stories 1.1, 1.3, 1.4 — integration tests for companions/web-ui/server.py.

Acceptance covered:
  R-1.1 server.py runs via stdlib only.
  R-1.3 binds 127.0.0.1 by default.
  R-1.10 access log format.
  R-1.11 zero non-stdlib deps.
  R-9.1 localhost-only binding.
  R-9.3 X-Content-Type-Options, X-Frame-Options.
  R-9.4 Cache-Control no-store on dynamic.
  R-9.5 reject `..` in paths.
  R-9.7 reject methods other than GET/POST/OPTIONS.

Strategy: each test spins up the server on an ephemeral port, makes a
request, asserts the response. Fixture vault from tests/fixtures/vault-minimal
is wired via a tmp HOME with a single-vault config pointing at it.
"""

import ast
import json
import os
import pathlib
import sys
import tempfile
import textwrap
import threading
import time
import unittest
import urllib.error
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
MONOREPO = REPO.parent.parent  # apps/cli → squirrel/
SERVER_PATH = MONOREPO / "apps" / "backend" / "server.py"
FIXTURE_VAULT = REPO / "tests" / "fixtures" / "vault-minimal"

sys.path.insert(0, str(MONOREPO / "apps" / "backend"))


def _start_server_with_fixture():
    """Start the server in-process with HOME set to a tmp dir + single-vault config."""
    tmp = tempfile.TemporaryDirectory()
    home = pathlib.Path(tmp.name)
    sq_dir = home / ".squirrel"
    sq_dir.mkdir(parents=True)
    (sq_dir / "config.toml").write_text(
        textwrap.dedent(
            f"""\
            machine_environment = "test"

            [[vaults]]
            name = "test"
            path = "{FIXTURE_VAULT}"
            default = true
            """
        )
    )
    # Override HOME so config_loader picks up the tmp config.
    os.environ["HOME"] = str(home)
    # Reload server fresh so it picks up the new config paths.
    for mod in (
        "server",
        "config_loader",
        "vocabulary",
        "capture_writer",
        "status_aggregator",
        "deadline_scanner",
    ):
        sys.modules.pop(mod, None)
    import server  # noqa: F401
    # The DEFAULT_CONFIG_PATH was set at module import — force it.
    import config_loader
    config_loader.DEFAULT_CONFIG_PATH = sq_dir / "config.toml"
    config_loader.DEFAULT_STATE_DIR = sq_dir / "state"
    srv = server.build_server("127.0.0.1", 0)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)
    return srv, port, tmp, home


def _stop(srv, tmp, prev_home):
    srv.shutdown()
    srv.server_close()
    tmp.cleanup()
    if prev_home is not None:
        os.environ["HOME"] = prev_home


class _ServerCase(unittest.TestCase):
    """Base case that owns server + temp HOME lifecycle for one test."""

    def setUp(self):
        self._prev_home = os.environ.get("HOME")
        self.srv, self.port, self.tmp, self.home = _start_server_with_fixture()

    def tearDown(self):
        _stop(self.srv, self.tmp, self._prev_home)

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _get(self, path: str, headers=None):
        req = urllib.request.Request(self._url(path), headers=headers or {})
        try:
            return urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he

    def _post(self, path: str, body: dict, headers=None):
        data = json.dumps(body).encode("utf-8")
        h = {"Content-Type": "application/json"}
        h.update(headers or {})
        req = urllib.request.Request(self._url(path), data=data, headers=h, method="POST")
        try:
            return urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he


# ─── Story 1.1 — scaffold + route table + stdlib-only ────────────────────────


class TestServerScaffold(unittest.TestCase):
    def test_server_file_imports_with_no_third_party(self):
        # R-1.11 — zero non-stdlib imports
        src = SERVER_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    names.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module:
                    names.add(node.module.split(".")[0])
        own = {
            "config_loader", "vocabulary", "capture_writer",
            "status_aggregator", "deadline_scanner", "new_project_writer",
            "focus_picker", "db", "intent_parser", "reminder_scanner",
            "reminder_writer", "cache",
        }
        stdlib = {
            "__future__", "argparse", "datetime", "hmac", "html", "http", "io",
            "json", "logging", "os", "pathlib", "re", "shutil", "socket",
            "socketserver", "subprocess", "sys", "threading", "traceback",
            "urllib", "typing",
        }
        leftover = names - own - stdlib
        self.assertSetEqual(leftover, set(), f"unexpected third-party imports: {leftover}")

    def test_route_table_is_exposed_as_dict_like(self):
        sys.path.insert(0, str(MONOREPO / "apps" / "backend"))
        import server
        self.assertTrue(hasattr(server, "ROUTES"))
        self.assertGreaterEqual(len(server.ROUTES), 15)


# ─── Story 1.3 — static + access log ─────────────────────────────────────────


class TestStaticAndLogging(_ServerCase):
    # The vanilla HTML UI was replaced by a React SPA in v0.7. The Python
    # server no longer ships /static/style.css or /static/app.js — those
    # paths now fall through to the SPA shell (200 text/html). The hashed
    # /assets/* bundle paths are served instead, after `npm run build`.

    def test_unknown_static_path_falls_through_to_spa_shell(self):
        # Pre-React, /static/* served vanilla CSS/JS. Post-React, anything
        # not matching the JSON API or /assets/* gets the SPA shell so the
        # client-side router can render its own 404.
        r = self._get("/static/style.css")
        self.assertEqual(r.status, 200)
        self.assertIn("text/html", r.headers.get("Content-Type", ""))

    def test_favicon_returns_204_or_200(self):
        r = self._get("/favicon.ico")
        self.assertIn(r.status, (200, 204))

    def test_access_log_records_request_with_no_body_or_cookie(self):
        # Make a request with a cookie header — verify log line does NOT contain it.
        self._get("/static/style.css", headers={"Cookie": "secret=do-not-log"})
        log_path = self.home / ".squirrel" / "web-ui.log"
        if not log_path.is_file():
            # Diagnose: list anything under the test HOME and report HOME val
            actual_home = os.environ.get("HOME", "")
            listing = sorted(p.name for p in (self.home / ".squirrel").iterdir())
            self.fail(
                f"log not at {log_path}; HOME={actual_home}, "
                f"~/.squirrel contents={listing}"
            )
        log = log_path.read_text(encoding="utf-8")
        self.assertIn("/static/style.css 200", log)
        self.assertNotIn("secret=do-not-log", log)


# ─── Story 1.4 — security middleware ─────────────────────────────────────────


class TestSecurityHeaders(_ServerCase):
    def test_nosniff_and_frame_options_on_html(self):
        r = self._get("/")
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(r.headers.get("X-Frame-Options"), "DENY")

    def test_no_store_on_dynamic_html(self):
        r = self._get("/")
        self.assertIn("no-store", (r.headers.get("Cache-Control") or "").lower())

    def test_spa_shell_is_no_store(self):
        # The SPA shell (HTML) is dynamic — must not be cached, so route
        # changes deploy immediately. Hashed /assets/* are cached separately.
        r = self._get("/static/style.css")  # falls through to shell
        cc = (r.headers.get("Cache-Control") or "").lower()
        self.assertIn("no-store", cc)


class TestPathTraversalBlocked(_ServerCase):
    def test_dot_dot_in_path_returns_400(self):
        r = self._get("/projects/../../etc/passwd")
        self.assertEqual(r.status, 400)

    def test_dotfile_segment_returns_400(self):
        r = self._get("/static/.env")
        self.assertEqual(r.status, 400)


class TestMethodNotAllowed(_ServerCase):
    def test_delete_returns_405(self):
        req = urllib.request.Request(self._url("/"), method="DELETE")
        try:
            urllib.request.urlopen(req, timeout=3)
            self.fail("expected 405")
        except urllib.error.HTTPError as he:
            self.assertEqual(he.code, 405)

    def test_put_to_unknown_api_returns_404(self):
        # Story 3.2 enabled PUT dispatch for /api/focus/today and
        # /api/focus/week. Other API paths still 404 (no route matches).
        req = urllib.request.Request(self._url("/api/unknown"), method="PUT")
        try:
            urllib.request.urlopen(req, timeout=3)
            self.fail("expected 404")
        except urllib.error.HTTPError as he:
            self.assertEqual(he.code, 404)


class TestCorsPreflight(_ServerCase):
    """The webview sends the custom ``X-Squirrel-Token`` header cross-origin, so
    a non-simple request triggers a CORS preflight. The preflight OPTIONS
    response MUST list ``X-Squirrel-Token`` in ``Access-Control-Allow-Headers`` —
    otherwise the browser blocks every authenticated request before it is sent
    (root cause of the onboarding "Obsidian not found" failure). ``curl`` never
    performs a preflight, so only a browser (and this test) catches it."""

    def _preflight(self, path):
        req = urllib.request.Request(
            self._url(path),
            method="OPTIONS",
            headers={
                "Origin": "tauri://localhost",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-squirrel-token, content-type",
            },
        )
        try:
            return urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he

    def test_preflight_allows_x_squirrel_token_header(self):
        r = self._preflight("/api/env/obsidian")
        allow = (r.headers.get("Access-Control-Allow-Headers") or "").lower()
        self.assertIn(
            "x-squirrel-token", allow,
            f"preflight must allow the auth header so the webview fetch is not "
            f"blocked; got Access-Control-Allow-Headers={allow!r}",
        )

    def test_preflight_still_allows_content_type(self):
        r = self._preflight("/api/env/obsidian")
        allow = (r.headers.get("Access-Control-Allow-Headers") or "").lower()
        self.assertIn("content-type", allow)


# ─── Bind address (R-1.3) ────────────────────────────────────────────────────


class TestDefaultBind(unittest.TestCase):
    def test_default_host_is_localhost(self):
        sys.path.insert(0, str(MONOREPO / "apps" / "backend"))
        import server
        self.assertEqual(server.DEFAULT_HOST, "127.0.0.1")
        self.assertEqual(server.LAN_HOST, "0.0.0.0")


# ─── Story 2.1 — POST /api/intents ───────────────────────────────────────────


class TestIntentCreate(_ServerCase):
    def test_201_creates_intent_file(self):
        r = self._post("/api/intents", {
            "project_slug": "TEST-PROJECT",
            "tag": "NEW-TASK",
            "title": "A new task",
        })
        self.assertEqual(r.status, 201)
        data = json.loads(r.read())
        self.assertIn("path", data)
        intent_file = FIXTURE_VAULT / "01-Proyectos-Activos" / "TEST-PROJECT" / "NEW-TASK.md"
        self.assertTrue(intent_file.is_file(), "intent file should have been written")
        intent_file.unlink()

    def test_404_for_unknown_project(self):
        r = self._post("/api/intents", {
            "project_slug": "DOES-NOT-EXIST",
            "tag": "SOME-TASK",
            "title": "title",
        })
        self.assertEqual(r.status, 404)

    def test_409_for_duplicate_tag(self):
        r = self._post("/api/intents", {
            "project_slug": "TEST-PROJECT",
            "tag": "TEST-PROJECT-AUTH-001",
            "title": "duplicate",
        })
        self.assertEqual(r.status, 409)

    def test_422_for_invalid_tag(self):
        r = self._post("/api/intents", {
            "project_slug": "TEST-PROJECT",
            "tag": "bad tag!",
            "title": "bad tag test",
        })
        self.assertEqual(r.status, 422)


# ─── Story 3.1 — GET /api/_handshake (R-3.1..R-3.4) ──────────────────────────


class TestHandshake(_ServerCase):
    GOOD = "d" * 64

    def setUp(self):
        super().setUp()
        import server
        self.server_mod = server

    def tearDown(self):
        self.server_mod.TOKEN = None
        self.server_mod.DEV_MODE = False
        super().tearDown()

    def _normal(self):
        self.server_mod.TOKEN = self.GOOD
        self.server_mod.DEV_MODE = False

    def _dev(self):
        self.server_mod.TOKEN = None
        self.server_mod.DEV_MODE = True

    # ── normal mode ──────────────────────────────────────────────────────────
    def test_normal_matching_header_echoes_token(self):
        self._normal()
        r = self._get("/api/_handshake", headers={"X-Squirrel-Token": self.GOOD})
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(r.read())["token_echo"], self.GOOD)

    def test_normal_missing_header_401_empty(self):
        self._normal()
        r = self._get("/api/_handshake")
        self.assertEqual(r.status, 401)
        self.assertEqual(r.read(), b"")  # R-3.4 — no token leaked

    def test_normal_mismatch_header_401_empty(self):
        self._normal()
        r = self._get("/api/_handshake", headers={"X-Squirrel-Token": "e" * 64})
        self.assertEqual(r.status, 401)
        self.assertEqual(r.read(), b"")

    # ── dev mode ─────────────────────────────────────────────────────────────
    def test_dev_matching_header_returns_mode_dev(self):
        self._dev()
        r = self._get("/api/_handshake", headers={"X-Squirrel-Token": self.GOOD})
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(r.read()), {"mode": "dev"})

    def test_dev_missing_header_returns_mode_dev(self):
        self._dev()
        r = self._get("/api/_handshake")
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(r.read()), {"mode": "dev"})

    def test_dev_mismatch_header_returns_mode_dev(self):
        self._dev()
        r = self._get("/api/_handshake", headers={"X-Squirrel-Token": "f" * 64})
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(r.read()), {"mode": "dev"})


# ─── Story 2.2 — X-Squirrel-Token enforcement (R-2.6..R-2.9) ─────────────────


class TestTokenEnforcement(_ServerCase):
    """Spins up a server, then marks it as token-configured by setting the
    module globals (build_server does not call configure_auth). Exercises the
    auth gate on a real request path."""

    GOOD = "b" * 64

    def setUp(self):
        super().setUp()
        import server
        self.server_mod = server
        server.TOKEN = self.GOOD
        server.DEV_MODE = False

    def tearDown(self):
        self.server_mod.TOKEN = None
        self.server_mod.DEV_MODE = False
        super().tearDown()

    def test_missing_header_returns_401(self):
        r = self._get("/api/me")
        self.assertEqual(r.status, 401)

    def test_bad_header_returns_401(self):
        r = self._get("/api/me", headers={"X-Squirrel-Token": "c" * 64})
        self.assertEqual(r.status, 401)

    def test_matching_header_returns_200(self):
        r = self._get("/api/me", headers={"X-Squirrel-Token": self.GOOD})
        self.assertEqual(r.status, 200)

    def test_static_asset_is_also_gated(self):
        # R-2.6 decision: the SPA shell / static routes are gated too, so a
        # squatter cannot serve a hostile bundle.
        r = self._get("/")
        self.assertEqual(r.status, 401)

    def test_handshake_path_is_exempt_from_gate(self):
        # The handshake is exempt from the generic gate and runs its own
        # contract: a matching header yields 200 + token_echo (R-3.1), proving
        # the handler ran rather than being blanket-401'd by the gate.
        r = self._get("/api/_handshake", headers={"X-Squirrel-Token": self.GOOD})
        self.assertEqual(r.status, 200)
        self.assertEqual(json.loads(r.read())["token_echo"], self.GOOD)

    def test_dev_mode_bypasses_enforcement(self):
        # R-2.8 — flip to dev mode: requests succeed with no header.
        self.server_mod.TOKEN = None
        self.server_mod.DEV_MODE = True
        r = self._get("/api/me")
        self.assertEqual(r.status, 200)

    def test_token_value_never_appears_in_log(self):
        # R-2.9 — a refused request must not leak the token into the log.
        self._get("/api/me")  # no header → 401
        log_path = self.home / ".squirrel" / "web-ui.log"
        if log_path.is_file():
            self.assertNotIn(self.GOOD, log_path.read_text(encoding="utf-8"))


# ─── Story 2.1 — token / token-file argparse + dev mode (R-2.1..R-2.5) ────────


class TestTokenConfig(unittest.TestCase):
    """Unit tests for server.configure_auth + _load_token_from_file. These
    exercise the five branches without spawning a process: --token, valid
    --token-file, the three R-2.3 file failures, mutual exclusion, and the
    no-flags dev-mode path."""

    GOOD = "a" * 64  # 64 hex chars — readable test fixture per the plan

    def setUp(self):
        sys.path.insert(0, str(MONOREPO / "apps" / "backend"))
        import server
        self.server = server
        # Reset auth state so tests don't leak into one another.
        server.TOKEN = None
        server.DEV_MODE = False
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self.server.TOKEN = None
        self.server.DEV_MODE = False
        self._tmp.cleanup()

    def _write_token_file(self, content: str, mode: int = 0o600) -> pathlib.Path:
        p = self._dir / "launchd-token"
        p.write_text(content, encoding="utf-8")
        os.chmod(p, mode)
        return p

    # R-2.1 — --token loads TOKEN, dev mode off.
    def test_token_flag_sets_token_and_disables_dev_mode(self):
        self.server.configure_auth(self.GOOD, None)
        self.assertEqual(self.server.TOKEN, self.GOOD)
        self.assertFalse(self.server.DEV_MODE)

    # R-2.2 — valid --token-file loads TOKEN, dev mode off.
    def test_token_file_valid_loads_token(self):
        p = self._write_token_file(self.GOOD + "\n")  # trailing newline allowed
        self.server.configure_auth(None, str(p))
        self.assertEqual(self.server.TOKEN, self.GOOD)
        self.assertFalse(self.server.DEV_MODE)

    # R-2.3 — missing file → exit 2.
    def test_token_file_missing_exits_2(self):
        with self.assertRaises(SystemExit) as cm:
            self.server.configure_auth(None, str(self._dir / "nope"))
        self.assertEqual(cm.exception.code, 2)

    # R-2.3 — wrong mode → exit 2.
    def test_token_file_wrong_mode_exits_2(self):
        p = self._write_token_file(self.GOOD, mode=0o644)
        with self.assertRaises(SystemExit) as cm:
            self.server.configure_auth(None, str(p))
        self.assertEqual(cm.exception.code, 2)

    # R-2.3 — wrong owner → exit 2 (simulate by faking geteuid).
    def test_token_file_wrong_owner_exits_2(self):
        from unittest import mock
        p = self._write_token_file(self.GOOD)
        fake_uid = os.geteuid() + 1
        with mock.patch.object(self.server.os, "geteuid", return_value=fake_uid):
            with self.assertRaises(SystemExit) as cm:
                self.server.configure_auth(None, str(p))
        self.assertEqual(cm.exception.code, 2)

    # R-2.3 — malformed content → exit 2.
    def test_token_file_malformed_exits_2(self):
        p = self._write_token_file("not-hex-garbage")
        with self.assertRaises(SystemExit) as cm:
            self.server.configure_auth(None, str(p))
        self.assertEqual(cm.exception.code, 2)

    # R-2.4 — both flags → exit 2.
    def test_both_flags_exit_2(self):
        p = self._write_token_file(self.GOOD)
        with self.assertRaises(SystemExit) as cm:
            self.server.configure_auth(self.GOOD, str(p))
        self.assertEqual(cm.exception.code, 2)

    # R-2.5 — neither flag → dev mode, no token.
    def test_neither_flag_enters_dev_mode(self):
        self.server.configure_auth(None, None)
        self.assertIsNone(self.server.TOKEN)
        self.assertTrue(self.server.DEV_MODE)


if __name__ == "__main__":
    unittest.main()
