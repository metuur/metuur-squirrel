#!/usr/bin/env python3
"""
Integration tests for the Quick Task Stack HTTP endpoints (Unit B).

Covers EARS R-1.2, R-1.3, R-1.5, R-2.3, R-2.4, R-3.1, R-3.2, R-3.3, R-3.5,
R-3.6, R-5.1 (the /api/home summary), plus 404 resolution.

Spins up server.py against a copied fixture vault (same harness shape as
test_web_ui_json_api.py). Auth is not enforced in test mode.
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
    for mod in (
        "server", "config_loader", "vocabulary", "capture_writer",
        "status_aggregator", "deadline_scanner",
        "quick_task_writer", "quick_task_scanner",
    ):
        sys.modules.pop(mod, None)
    import config_loader, server
    config_loader.DEFAULT_CONFIG_PATH = home / ".squirrel" / "config.toml"
    config_loader.DEFAULT_STATE_DIR = home / ".squirrel" / "state"
    srv = server.build_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return srv, port


class _Case(unittest.TestCase):
    def setUp(self):
        self._prev_home = os.environ.get("HOME")
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        (self.home / ".squirrel").mkdir(parents=True)
        self.vault = self.home / "vault"
        shutil.copytree(FIXTURE_VAULT, self.vault)
        (self.home / ".squirrel" / "config.toml").write_text(textwrap.dedent(f"""\
            machine_environment = "test"

            [[vaults]]
            name = "test"
            path = "{self.vault}"
            default = true
            """))
        self.srv, self.port = _spawn(self.home)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _req(self, method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=data, method=method,
            headers={"Content-Type": "application/json"} if data else {},
        )
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            body = he.read().decode("utf-8")
            return he.code, (json.loads(body) if body else {})
        body = r.read().decode("utf-8")
        return r.status, (json.loads(body) if body else {})


class TestQuickTaskCreate(_Case):
    def test_create_returns_201_and_id(self):
        status, data = self._req("POST", "/api/quick-tasks", {"text": "Reply to Ana"})
        self.assertEqual(status, 201)
        self.assertEqual(data["id"], "QT-001")

    def test_empty_text_is_400(self):
        status, _ = self._req("POST", "/api/quick-tasks", {"text": "   "})
        self.assertEqual(status, 400)

    def test_sixth_create_is_409_with_code(self):
        for i in range(5):
            self._req("POST", "/api/quick-tasks", {"text": f"Task {i}"})
        status, data = self._req("POST", "/api/quick-tasks", {"text": "Sixth"})
        self.assertEqual(status, 409)
        self.assertEqual(data["error"], "QUICK_TASK_LIMIT_REACHED")


class TestQuickTaskList(_Case):
    def test_list_is_fifo_with_limit(self):
        for t in ("A", "B", "C"):
            self._req("POST", "/api/quick-tasks", {"text": t})
        status, data = self._req("GET", "/api/quick-tasks")
        self.assertEqual(status, 200)
        self.assertEqual([t["text"] for t in data["active"]], ["A", "B", "C"])
        self.assertEqual(data["active_count"], 3)
        self.assertEqual(data["limit"], 5)


class TestQuickTaskCompleteDelete(_Case):
    def test_complete_frees_slot(self):
        for t in ("A", "B"):
            self._req("POST", "/api/quick-tasks", {"text": t})
        status, _ = self._req("PATCH", "/api/quick-task/QT-001/complete")
        self.assertEqual(status, 200)
        _, data = self._req("GET", "/api/quick-tasks")
        self.assertEqual(data["active_count"], 1)
        self.assertNotIn("QT-001", [t["id"] for t in data["active"]])

    def test_delete_frees_slot(self):
        for t in ("A", "B"):
            self._req("POST", "/api/quick-tasks", {"text": t})
        status, _ = self._req("DELETE", "/api/quick-task/QT-002")
        self.assertEqual(status, 200)
        _, data = self._req("GET", "/api/quick-tasks")
        self.assertEqual(data["active_count"], 1)

    def test_unknown_id_is_404(self):
        status, _ = self._req("PATCH", "/api/quick-task/QT-999/complete")
        self.assertEqual(status, 404)


class TestQuickTaskSnooze(_Case):
    def test_snooze_moves_to_snoozed_and_frees_slot(self):
        for t in ("A", "B"):
            self._req("POST", "/api/quick-tasks", {"text": t})
        status, data = self._req("PATCH", "/api/quick-task/QT-001/snooze", {"until": "1h"})
        self.assertEqual(status, 200)
        self.assertIn("snoozed_until", data)
        _, listing = self._req("GET", "/api/quick-tasks")
        self.assertEqual(listing["active_count"], 1)
        self.assertEqual([t["id"] for t in listing["snoozed"]], ["QT-001"])

    def test_snooze_limit_is_409(self):
        self._req("POST", "/api/quick-tasks", {"text": "A"})
        # Snooze, wake (it stays snoozed until due) — instead push count to cap via
        # two snoozes: snooze→count1, snooze again still snoozed→count2, third→409.
        self._req("PATCH", "/api/quick-task/QT-001/snooze", {"until": "1h"})
        self._req("PATCH", "/api/quick-task/QT-001/snooze", {"until": "1h"})
        status, data = self._req("PATCH", "/api/quick-task/QT-001/snooze", {"until": "1h"})
        self.assertEqual(status, 409)
        self.assertEqual(data["error"], "QUICK_TASK_SNOOZE_LIMIT")


class TestHomeQuickTasksSummary(_Case):
    def test_home_includes_quick_tasks_block(self):
        for t in ("First", "Second"):
            self._req("POST", "/api/quick-tasks", {"text": t})
        status, home = self._req("GET", "/api/home")
        self.assertEqual(status, 200)
        self.assertIn("quick_tasks", home)
        qt = home["quick_tasks"]
        self.assertEqual(qt["active_count"], 2)
        self.assertEqual(qt["oldest"]["text"], "First")
        self.assertIn("return_blocked", qt)
        # R-6.2: existing home fields remain present.
        for key in ("focus", "pressing", "projects", "reminders"):
            self.assertIn(key, home)


if __name__ == "__main__":
    unittest.main()
