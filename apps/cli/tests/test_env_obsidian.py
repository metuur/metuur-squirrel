#!/usr/bin/env python3
"""
test_env_obsidian.py — Obsidian detection (story in-app-vault-onboarding 2.1).

Covers EARS R-2.1, R-2.2, R-2.3, R-2.4, R-2.8.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest import mock

REPO = pathlib.Path(__file__).resolve().parent.parent
MONOREPO = REPO.parent.parent
sys.path.insert(0, str(MONOREPO / "apps" / "backend"))
sys.path.insert(0, str(REPO / "lib"))

import server  # noqa: E402


# ─── R-2.2 / R-2.3 / R-2.4 / R-2.8: detect_obsidian unit ─────────────────────


class TestDetectObsidian(unittest.TestCase):

    def test_app_in_applications_is_detected(self):
        # R-2.2/R-2.3: /Applications/Obsidian.app present → installed + path.
        with tempfile.TemporaryDirectory() as d:
            app = pathlib.Path(d) / "Obsidian.app"
            app.mkdir()
            installed, path = server.detect_obsidian(app_path=app)
            self.assertTrue(installed)
            self.assertEqual(path, str(app))

    def test_mdfind_fallback_when_app_absent(self):
        # R-2.2: app missing but mdfind locates a bundle → installed + path.
        missing = pathlib.Path("/nonexistent/Obsidian.app")
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="/Users/x/Obsidian.app\n", stderr=""
        )
        with mock.patch.object(server.subprocess, "run", return_value=fake):
            installed, path = server.detect_obsidian(app_path=missing)
        self.assertTrue(installed)
        self.assertEqual(path, "/Users/x/Obsidian.app")

    def test_not_found_when_app_and_mdfind_empty(self):
        # R-2.4: nothing found → installed False, path None.
        missing = pathlib.Path("/nonexistent/Obsidian.app")
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="\n", stderr="")
        with mock.patch.object(server.subprocess, "run", return_value=fake):
            installed, path = server.detect_obsidian(app_path=missing)
        self.assertFalse(installed)
        self.assertIsNone(path)

    def test_mdfind_timeout_reports_not_installed(self):
        # R-2.8: mdfind timeout → installed False (and does not raise).
        missing = pathlib.Path("/nonexistent/Obsidian.app")
        def _boom(*a, **k):
            raise subprocess.TimeoutExpired(cmd="mdfind", timeout=2.0)
        with mock.patch.object(server.subprocess, "run", side_effect=_boom):
            installed, path = server.detect_obsidian(app_path=missing)
        self.assertFalse(installed)
        self.assertIsNone(path)


# ─── R-2.1: HTTP endpoint shape ──────────────────────────────────────────────


def _spawn(home: pathlib.Path):
    os.environ["HOME"] = str(home)
    for mod in ("server", "config_loader"):
        sys.modules.pop(mod, None)
    import config_loader, server as srv_mod  # noqa: F811
    config_loader.DEFAULT_CONFIG_PATH = home / ".squirrel" / "config.toml"
    config_loader.DEFAULT_STATE_DIR = home / ".squirrel" / "state"
    srv = srv_mod.build_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return srv, srv_mod, port


class TestEnvObsidianEndpoint(unittest.TestCase):

    def setUp(self):
        self._prev_home = os.environ.get("HOME")
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        (self.home / ".squirrel").mkdir(parents=True)
        self.srv, self.srv_mod, self.port = _spawn(self.home)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _get(self, path):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", method="GET")
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))

    def test_endpoint_returns_installed_shape(self):
        with mock.patch.object(
            self.srv_mod, "detect_obsidian",
            return_value=(True, "/Applications/Obsidian.app"),
        ):
            status, data = self._get("/api/env/obsidian")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"installed": True, "path": "/Applications/Obsidian.app"})

    def test_endpoint_returns_not_installed_shape(self):
        with mock.patch.object(
            self.srv_mod, "detect_obsidian", return_value=(False, None),
        ):
            status, data = self._get("/api/env/obsidian")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"installed": False, "path": None})


if __name__ == "__main__":
    unittest.main()
