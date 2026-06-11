#!/usr/bin/env python3
"""
Isolation regression tests for Post-it feature (tasks 6.1, 6.3).

Covers:
  R-6.5 — /api/notes/{id} returns 404 for ids under 05-Post-its/
  R-6.3 — Post-it files excluded from quick-task scanning, /api/home,
           /api/search (no 500), and project listings
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
MONOREPO = REPO.parent.parent  # apps/cli → squirrel/
FIXTURE_VAULT = REPO / "tests" / "fixtures" / "vault-minimal"

sys.path.insert(0, str(MONOREPO / "apps" / "backend"))
sys.path.insert(0, str(REPO / "lib"))


def _spawn(home: pathlib.Path):
    os.environ["HOME"] = str(home)
    for mod in (
        "server", "config_loader", "vocabulary",
        "capture_writer", "status_aggregator", "deadline_scanner",
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

        # Seed a single post-it file with deterministic content
        post_its_dir = self.vault / "05-Post-its"
        post_its_dir.mkdir()
        (post_its_dir / "PI-001.md").write_text(
            "---\nid: PI-001\ntype: post_it\nstate: active\ncolor: yellow\n"
            "label: \"\"\npinned: false\ncreated: 2026-06-11T10:00:00-05:00\nconverted_to: \"\"\n---\n\n"
            "some-unique-text-in-post-it\n",
            encoding="utf-8",
        )

        cfg = textwrap.dedent(f"""\
            machine_environment = "test"

            [[vaults]]
            name = "test"
            path = "{self.vault}"
            default = true
            """)
        (self.home / ".squirrel" / "config.toml").write_text(cfg)
        self.srv, self.port = _spawn(self.home)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _url(self, p):
        return f"http://127.0.0.1:{self.port}{p}"

    def _get(self, path):
        req = urllib.request.Request(self._url(path), method="GET")
        try:
            r = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as he:
            return he.code, he.read().decode("utf-8")
        return r.status, r.read().decode("utf-8")


class TestNoteWallOff(_Case):
    """R-6.5 — /api/notes/{id} returns 404 for Post-it ids."""

    def test_note_detail_wall_off(self):
        """GET /api/notes/PI-001 must return 404."""
        status, _ = self._get("/api/notes/PI-001")
        self.assertEqual(status, 404, "Expected 404 for Post-it id via /api/notes/")

    def test_post_its_still_served(self):
        """GET /api/post-its must return 200 and include PI-001."""
        status, body = self._get("/api/post-its")
        self.assertEqual(status, 200)
        data = json.loads(body)
        ids = [item["id"] for item in data]
        self.assertIn("PI-001", ids, "PI-001 must be served via /api/post-its")


class TestIsolationRegression(_Case):
    """R-6.3 — Post-it files must not bleed into other endpoints."""

    def test_home_no_post_its(self):
        """GET /api/home must not contain PI-001 in any task/note id fields."""
        status, body = self._get("/api/home")
        self.assertEqual(status, 200)
        data = json.loads(body)
        body_text = json.dumps(data)
        self.assertNotIn("PI-001", body_text,
                         "PI-001 must not appear in /api/home response")

    def test_quick_tasks_no_post_its(self):
        """GET /api/quick-tasks must not contain any PI- ids."""
        status, body = self._get("/api/quick-tasks")
        self.assertEqual(status, 200)
        data = json.loads(body)
        body_text = json.dumps(data)
        self.assertNotIn("PI-", body_text,
                         "No PI- ids must appear in /api/quick-tasks")

    def test_search_does_not_crash(self):
        """GET /api/search?q=<post-it-unique-text> must not return 500."""
        status, _ = self._get("/api/search?q=some-unique-text-in-post-it")
        self.assertNotEqual(status, 500,
                            "/api/search must not 500 when post-it text is queried")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
