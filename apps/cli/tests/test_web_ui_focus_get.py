#!/usr/bin/env python3
"""
Story 3.1 — GET /api/focus.

Acceptance:
  R-3.1 — Endpoint exists; returns {today: ManualPick|null, week: ManualPick|null}.
  R-3.2 — `picked_on` is the verbatim YAML value.
  R-3.8 — Bound to 127.0.0.1 (inherited; verified at spawn).
"""

import datetime
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
        "focus_picker", "intent_parser",
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


def _make_intent(folder: pathlib.Path, slug: str, frontmatter: dict,
                 title: str = "An Intent") -> pathlib.Path:
    """Write a minimal valid intent .md and return its path. Mirrors
    apps/cli/tests/test_focus_picker.py's helper."""
    folder.mkdir(parents=True, exist_ok=True)
    fm = {"id": slug, "status": "in-progress"}
    fm.update(frontmatter)
    fm_text = "\n".join(f"{k}: {v}" for k, v in fm.items()) + "\n"
    content = (
        "---\n"
        + fm_text
        + "---\n"
        + f"\n# {title}\n"
        + "\n## Shutdown Notes\n"
        + "\n### 2026-05-28 10:00\n"
        + "- **Estado**: in-progress\n"
        + "- **Next**: continue building\n"
    )
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
        self.srv, self.port = _spawn(self.home)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _url(self, p): return f"http://127.0.0.1:{self.port}{p}"

    def _get_json(self, path: str) -> tuple[int, dict]:
        req = urllib.request.Request(self._url(path))
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))


class TestFocusGet(_Case):
    def test_focus_get_returns_both_null_when_nothing_picked(self):
        # The fixture vault has projects + intents but no focus_today / focus_week
        # frontmatter keys, so both slots are null.
        status, data = self._get_json("/api/focus")
        self.assertEqual(status, 200)
        self.assertEqual(data, {"today": None, "today_pm": None, "week": None})

    def test_focus_get_returns_today_pick_when_set(self):
        today = datetime.date.today().isoformat()
        proj = self.vault / "01-Active-Projects" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-FOCUS-T01",
                     {"focus_today": today}, title="Today focus")

        status, data = self._get_json("/api/focus")
        self.assertEqual(status, 200)
        self.assertIsNotNone(data["today"])
        self.assertEqual(data["today"]["intent_slug"], "TEST-PROJECT-FOCUS-T01")
        self.assertEqual(data["today"]["picked_on"], today)
        self.assertEqual(data["today"]["project_slug"], "TEST-PROJECT")
        self.assertIsNone(data["week"])

    def test_focus_get_returns_week_pick_when_set(self):
        week = datetime.date.today().strftime("%G-W%V")
        proj = self.vault / "01-Active-Projects" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-FOCUS-W01",
                     {"focus_week": week}, title="Week focus")

        status, data = self._get_json("/api/focus")
        self.assertEqual(status, 200)
        self.assertIsNotNone(data["week"])
        self.assertEqual(data["week"]["intent_slug"], "TEST-PROJECT-FOCUS-W01")
        self.assertEqual(data["week"]["picked_on"], week)
        self.assertEqual(data["week"]["project_slug"], "TEST-PROJECT")
        self.assertIsNone(data["today"])

    def test_focus_get_ignores_stale_today_token(self):
        # R-1.4 wired through the HTTP boundary.
        proj = self.vault / "01-Active-Projects" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-FOCUS-STALE",
                     {"focus_today": "2020-01-01"}, title="Stale pick")

        status, data = self._get_json("/api/focus")
        self.assertEqual(status, 200)
        self.assertIsNone(data["today"])


if __name__ == "__main__":
    unittest.main()
