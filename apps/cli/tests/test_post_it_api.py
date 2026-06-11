#!/usr/bin/env python3
"""
Integration tests for POST /api/post-its (task 2.2).

Covers:
  R-2.3 — valid text → 201 with created item; empty/missing text → 400
  R-2.9 — file is written to vault after successful POST
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

    def _post_json(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url(path), data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))


class TestPostItCreate(_Case):

    def test_post_it_create_success(self):
        """R-2.3 — valid text returns 201 with id starting 'PI-'."""
        status, data = self._post_json("/api/post-its", {"text": "hello world"})
        self.assertEqual(status, 201)
        self.assertIn("id", data)
        self.assertTrue(data["id"].startswith("PI-"), f"id was {data['id']!r}")

    def test_post_it_create_file_created(self):
        """R-2.9 — vault file exists after successful POST."""
        status, data = self._post_json("/api/post-its", {"text": "remember this"})
        self.assertEqual(status, 201)
        pi_id = data["id"]
        expected = self.vault / "05-Post-its" / f"{pi_id}.md"
        self.assertTrue(expected.exists(), f"Expected file not found: {expected}")

    def test_post_it_create_empty_text(self):
        """R-2.3 — empty text returns 400 with no write."""
        status, data = self._post_json("/api/post-its", {"text": ""})
        self.assertEqual(status, 400)
        # Verify no files were written
        post_its_dir = self.vault / "05-Post-its"
        count = len(list(post_its_dir.glob("PI-*.md"))) if post_its_dir.exists() else 0
        self.assertEqual(count, 0)

    def test_post_it_create_missing_text(self):
        """R-2.3 — missing text key returns 400 with no write."""
        status, data = self._post_json("/api/post-its", {})
        self.assertEqual(status, 400)
        post_its_dir = self.vault / "05-Post-its"
        count = len(list(post_its_dir.glob("PI-*.md"))) if post_its_dir.exists() else 0
        self.assertEqual(count, 0)


if __name__ == "__main__":
    unittest.main()
