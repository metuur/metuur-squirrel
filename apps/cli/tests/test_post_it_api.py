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


class _CaseWithGet(_Case):
    def _get_json(self, path):
        req = urllib.request.Request(self._url(path), method="GET")
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))


class TestPostItList(_CaseWithGet):

    def test_get_post_its_empty(self):
        """R-2.1 — fresh vault with no post-its returns 200 empty list."""
        status, data = self._get_json("/api/post-its")
        self.assertEqual(status, 200)
        self.assertEqual(data, [])

    def test_get_post_its_returns_items(self):
        """R-2.1 — two items returned; pinned one is first."""
        _, d1 = self._post_json("/api/post-its", {"text": "first note"})
        _, d2 = self._post_json("/api/post-its", {"text": "pinned note"})
        pi_id_pinned = d2["id"]
        # Directly set pinned: true in frontmatter
        pi_file = self.vault / "05-Post-its" / f"{pi_id_pinned}.md"
        text = pi_file.read_text(encoding="utf-8")
        pi_file.write_text(text.replace("pinned: false", "pinned: true"), encoding="utf-8")

        status, data = self._get_json("/api/post-its")
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 2)
        self.assertTrue(data[0]["pinned"], "pinned item should be first")
        self.assertEqual(data[0]["id"], pi_id_pinned)

    def test_get_post_its_two_items_no_layout_distinct_positions(self):
        """R-1.5 — two items without stored layout get distinct default positions."""
        self._post_json("/api/post-its", {"text": "note alpha"})
        self._post_json("/api/post-its", {"text": "note beta"})
        status, data = self._get_json("/api/post-its")
        self.assertEqual(status, 200)
        self.assertEqual(len(data), 2)
        pos0 = (data[0]["layout"]["x"], data[0]["layout"]["y"])
        pos1 = (data[1]["layout"]["x"], data[1]["layout"]["y"])
        self.assertNotEqual(pos0, pos1, "two items should have different default layout positions")

    def test_get_post_its_deterministic(self):
        """R-1.5 — layout is deterministic: two GET calls return identical values."""
        self._post_json("/api/post-its", {"text": "stable layout"})
        _, data1 = self._get_json("/api/post-its")
        _, data2 = self._get_json("/api/post-its")
        self.assertEqual(data1[0]["layout"], data2[0]["layout"])

    def test_get_post_its_include_archived(self):
        """R-2.2 — archived item absent by default; present with ?include=archived."""
        _, d = self._post_json("/api/post-its", {"text": "will be archived"})
        pi_id = d["id"]
        # Directly set state: archived in the file
        pi_file = self.vault / "05-Post-its" / f"{pi_id}.md"
        text = pi_file.read_text(encoding="utf-8")
        pi_file.write_text(text.replace("state: active", "state: archived"), encoding="utf-8")

        status_default, data_default = self._get_json("/api/post-its")
        self.assertEqual(status_default, 200)
        ids_default = [item["id"] for item in data_default]
        self.assertNotIn(pi_id, ids_default, "archived item should not appear in default list")

        status_arch, data_arch = self._get_json("/api/post-its?include=archived")
        self.assertEqual(status_arch, 200)
        ids_arch = [item["id"] for item in data_arch]
        self.assertIn(pi_id, ids_arch, "archived item should appear with ?include=archived")


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
