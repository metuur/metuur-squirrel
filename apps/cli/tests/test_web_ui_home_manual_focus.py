#!/usr/bin/env python3
"""
Story 4.1 — GET /api/home exposes `manual_focus`.

Acceptance:
  R-4.1 — Response carries `manual_focus: {today, week}`.
  R-4.2 — Existing `focus` field shape unchanged; still populated by heuristic.
  R-4.3 / R-4.4 — Presence of a manual pick does NOT modify `focus` / `pressing[]`.
  R-4.5 — Unset / stale slot is exactly `null` (not a missing key).
  R-9.1 — Stale `focus_today` YAML on disk → null at API boundary.
  R-10.2 — `focus`, `pressing[]`, `projects[]` byte-identical with or without
           a manual pick.
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
    """Write a minimal valid intent .md and return its path."""
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


class TestHomeManualFocus(_Case):
    def test_home_includes_manual_focus_both_null_when_unset(self):
        # R-4.1 / R-4.5: key is present, both slots null.
        status, data = self._get_json("/api/home")
        self.assertEqual(status, 200)
        self.assertIn("manual_focus", data)
        self.assertEqual(data["manual_focus"], {"today": None, "today_pm": None, "week": None})
        # R-10.2 shape preservation smoke check.
        for k in ("focus", "pressing", "projects", "parakeet"):
            self.assertIn(k, data)

    def test_home_includes_today_pick_when_set(self):
        today = datetime.date.today().isoformat()
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-FOCUS-T01",
                     {"focus_today": today}, title="Today focus")

        status, data = self._get_json("/api/home")
        self.assertEqual(status, 200)
        self.assertIsNotNone(data["manual_focus"]["today"])
        self.assertEqual(
            data["manual_focus"]["today"]["intent_slug"],
            "TEST-PROJECT-FOCUS-T01",
        )
        self.assertEqual(data["manual_focus"]["today"]["picked_on"], today)
        self.assertIsNone(data["manual_focus"]["week"])

    def test_home_focus_field_unchanged_when_manual_pick_set(self):
        # R-4.2 / R-4.3 / R-10.2: manual pick does not perturb the heuristic
        # `focus` field or `pressing[]`.
        status, before = self._get_json("/api/home")
        self.assertEqual(status, 200)
        focus_snapshot = json.dumps(before["focus"], sort_keys=True)
        pressing_snapshot = json.dumps(before["pressing"], sort_keys=True)

        # Seed a manual pick on TEST-PROJECT (the canonical fixture project).
        today = datetime.date.today().isoformat()
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-MANUAL-T01",
                     {"focus_today": today}, title="Manually picked")

        status, after = self._get_json("/api/home")
        self.assertEqual(status, 200)
        # Byte-identical heuristic fields.
        self.assertEqual(
            json.dumps(after["focus"], sort_keys=True), focus_snapshot,
        )
        self.assertEqual(
            json.dumps(after["pressing"], sort_keys=True), pressing_snapshot,
        )
        # And the manual pick surfaces on the new sibling field.
        self.assertEqual(
            after["manual_focus"]["today"]["project_slug"], "TEST-PROJECT",
        )

    def test_home_returns_null_for_stale_focus_today_yaml_still_on_disk(self):
        # R-9.1: read-time expiry — stale YAML value yields null at HTTP boundary
        # without mutating the file.
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        intent_path = _make_intent(
            proj, "TEST-PROJECT-FOCUS-STALE",
            {"focus_today": "2020-01-01"}, title="Stale pick",
        )

        status, data = self._get_json("/api/home")
        self.assertEqual(status, 200)
        self.assertIsNone(data["manual_focus"]["today"])

        # File on disk still carries the stale token verbatim.
        on_disk = intent_path.read_text(encoding="utf-8")
        self.assertIn("focus_today: 2020-01-01", on_disk)


if __name__ == "__main__":
    unittest.main()
