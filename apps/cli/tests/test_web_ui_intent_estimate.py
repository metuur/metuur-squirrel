#!/usr/bin/env python3
"""
PUT /api/intent/estimate — persist / clear an intent's time estimate.

Acceptance:
  R-2.3 — accept {project_slug, intent_slug, minutes}; persist; return stored estimate.
  R-1.7 — accept {clear: true}; remove the three estimate keys.
  R-1.5 — unknown intent → 404, no mutation.
  R-2.7 — missing/bad/oversized minutes → 400, no mutation.
  R-3.5 — variance surfaces in /api/home manual_focus once estimate + actual exist.
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
        "server", "config_loader", "vocabulary",
        "capture_writer", "status_aggregator", "deadline_scanner",
        "focus_picker", "intent_parser", "estimate_buffer",
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


def _make_intent(folder, slug, frontmatter, title="An Intent"):
    folder.mkdir(parents=True, exist_ok=True)
    fm = {"id": slug, "status": "in-progress"}
    fm.update(frontmatter)
    fm_text = "\n".join(f"{k}: {v}" for k, v in fm.items()) + "\n"
    content = "---\n" + fm_text + "---\n" + f"\n# {title}\n\nbody\n"
    p = folder / f"{slug}.md"
    p.write_text(content, encoding="utf-8")
    return p


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
        self.proj = self.vault / "01-Active-Projects" / "TEST-PROJECT"
        self.srv, self.port = _spawn(self.home)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _url(self, p):
        return f"http://127.0.0.1:{self.port}{p}"

    def _put(self, path, body):
        req = urllib.request.Request(
            self._url(path), data=json.dumps(body).encode(), method="PUT",
            headers={"Content-Type": "application/json"},
        )
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode())
        return r.status, json.loads(r.read().decode())


class TestIntentEstimate(_Case):
    # R-2.3
    def test_put_persists_estimate(self):
        p = _make_intent(self.proj, "TEST-PROJECT-e01", {})
        status, body = self._put(
            "/api/intent/estimate",
            {"project_slug": "TEST-PROJECT", "intent_slug": "TEST-PROJECT-e01", "minutes": 45},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["estimate"]["estimate_user_minutes"], 45)
        text = p.read_text()
        self.assertIn("estimate_user_minutes: 45", text)
        self.assertIn("estimate_minutes:", text)

    # R-1.7
    def test_clear_removes_estimate(self):
        p = _make_intent(self.proj, "TEST-PROJECT-e02", {})
        self._put("/api/intent/estimate",
                  {"project_slug": "TEST-PROJECT", "intent_slug": "TEST-PROJECT-e02", "minutes": 30})
        status, _ = self._put(
            "/api/intent/estimate",
            {"project_slug": "TEST-PROJECT", "intent_slug": "TEST-PROJECT-e02", "clear": True},
        )
        self.assertEqual(status, 200)
        self.assertNotIn("estimate_minutes", p.read_text())

    # R-1.5
    def test_unknown_intent_404(self):
        status, body = self._put(
            "/api/intent/estimate",
            {"project_slug": "TEST-PROJECT", "intent_slug": "NOPE", "minutes": 30},
        )
        self.assertEqual(status, 404)

    # R-2.7
    def test_bad_minutes_400(self):
        _make_intent(self.proj, "TEST-PROJECT-e03", {})
        for bad in (0, -1, 99999, "abc"):
            status, _ = self._put(
                "/api/intent/estimate",
                {"project_slug": "TEST-PROJECT", "intent_slug": "TEST-PROJECT-e03", "minutes": bad},
            )
            self.assertEqual(status, 400, f"minutes={bad!r} should be rejected")


if __name__ == "__main__":
    unittest.main()
