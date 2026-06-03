#!/usr/bin/env python3
"""
JSON API integration tests for the Mind Journal endpoints.

Covers:
  GET   /api/journal          — R-3.1, R-3.2, R-1.1 (seeded on bootstrap)
  POST  /api/journal/entry    — R-3.3, R-3.4, R-3.5, R-3.6, R-3.7
  PATCH /api/journal/config   — R-3.8, R-3.9
  GET   /api/home (journal)   — R-3.10
  delete → not recreated      — R-1.5, R-1.7
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile
import textwrap
import threading
import time
import unittest
import urllib.error
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
MONOREPO = REPO.parent.parent
FIXTURE_VAULT = REPO / "tests" / "fixtures" / "vault-minimal"

sys.path.insert(0, str(MONOREPO / "apps" / "backend"))
sys.path.insert(0, str(REPO / "lib"))


def _spawn(home: pathlib.Path):
    os.environ["HOME"] = str(home)
    for mod in ("server", "config_loader", "vocabulary", "capture_writer",
                "status_aggregator", "deadline_scanner", "mind_journal",
                "new_project_writer"):
        sys.modules.pop(mod, None)
    import config_loader, server
    config_loader.DEFAULT_CONFIG_PATH = home / ".squirrel" / "config.toml"
    config_loader.DEFAULT_STATE_DIR = home / ".squirrel" / "state"
    srv = server.build_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return srv, port


class JournalApiTest(unittest.TestCase):
    def setUp(self):
        self._prev_home = os.environ.get("HOME")
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        (self.home / ".squirrel").mkdir(parents=True)
        self.vault = self.home / "vault"
        shutil.copytree(FIXTURE_VAULT, self.vault)
        cfg = textwrap.dedent(f"""\
            machine_environment = "test"

            [[vaults]]
            name = "test"
            path = "{self.vault}"
            default = true
            """)
        (self.home / ".squirrel" / "config.toml").write_text(cfg)
        self.srv, self.port = _spawn(self.home)
        # Bootstrap triggers seeding (R-1.1).
        self._req("GET", "/api/me")

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _req(self, method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=data,
            headers=headers, method=method)
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))

    def _journal_file(self):
        return self.vault / "01-Proyectos-Activos" / "SCRATCH-PAD" / "MIND-JOURNAL.md"

    # ── R-3.1 / R-1.1 ──────────────────────────────────────────────────────
    def test_get_journal_seeded(self):
        self.assertTrue(self._journal_file().exists())
        status, data = self._req("GET", "/api/journal")
        self.assertEqual(status, 200)
        self.assertTrue(data["exists"])
        self.assertEqual(data["task"]["id"], "MIND-JOURNAL")
        for key in ("due", "next_due", "interval_hours", "waking"):
            self.assertIn(key, data)
        self.assertEqual(data["interval_hours"], 4)

    # ── R-3.3 / R-3.5 / R-3.6 ──────────────────────────────────────────────
    def test_post_entry_appends_and_resets(self):
        status, data = self._req("POST", "/api/journal/entry",
                                 {"mind": "focused", "doing": "tests", "mood": "happy"})
        self.assertEqual(status, 201)
        self.assertTrue(data["success"])
        _, jget = self._req("GET", "/api/journal")
        self.assertEqual(len(jget["entries"]), 1)
        self.assertEqual(jget["entries"][0]["mood"], "happy")
        self.assertEqual(jget["entries"][0]["mind"], "focused")
        self.assertFalse(jget["due"])  # clock reset → not due now

    # ── R-3.4 ──────────────────────────────────────────────────────────────
    def test_invalid_mood_rejected(self):
        status, data = self._req("POST", "/api/journal/entry",
                                 {"mind": "x", "doing": "y", "mood": "angry"})
        self.assertEqual(status, 400)
        self.assertEqual(data.get("error"), "INVALID_MOOD")

    # ── R-3.8 / R-3.9 ──────────────────────────────────────────────────────
    def test_config_update(self):
        status, _ = self._req("PATCH", "/api/journal/config",
                              {"interval_hours": 6, "waking_start": "07:00"})
        self.assertEqual(status, 200)
        _, jget = self._req("GET", "/api/journal")
        self.assertEqual(jget["interval_hours"], 6)
        self.assertEqual(jget["waking"]["start"], "07:00")

    def test_config_invalid_interval(self):
        status, _ = self._req("PATCH", "/api/journal/config", {"interval_hours": 0})
        self.assertEqual(status, 400)

    def test_config_invalid_time(self):
        status, _ = self._req("PATCH", "/api/journal/config", {"waking_start": "99:99"})
        self.assertEqual(status, 400)

    # ── R-3.10 ─────────────────────────────────────────────────────────────
    def test_home_includes_journal_block(self):
        status, data = self._req("GET", "/api/home")
        self.assertEqual(status, 200)
        self.assertIn("journal", data)
        self.assertIn("due", data["journal"])
        self.assertIn("next_due", data["journal"])

    # ── R-3.2 / R-3.7 / R-1.5 ──────────────────────────────────────────────
    def test_deleted_journal_not_recreated(self):
        self._journal_file().unlink()
        status, data = self._req("GET", "/api/journal")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"exists": False})
        self.assertFalse(self._journal_file().exists())  # GET did not recreate it
        status, data = self._req("POST", "/api/journal/entry",
                                 {"mind": "x", "doing": "y", "mood": "happy"})
        self.assertEqual(status, 404)
        self.assertEqual(data.get("error"), "NO_JOURNAL")


if __name__ == "__main__":
    unittest.main()
