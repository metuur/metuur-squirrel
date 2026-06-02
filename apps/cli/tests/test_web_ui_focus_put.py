#!/usr/bin/env python3
"""
Story 3.2 — PUT /api/focus/today and PUT /api/focus/week.

Acceptance:
  R-3.3 — Accept {project_slug, intent_slug}.
  R-3.4 — Accept {clear: true}.
  R-3.5 — Clear removes the slot's key from every intent carrying it with the
          current token; response shows updated {today, week}.
  R-3.6 — Unknown project/intent → 404 {"error": "intent_not_found"}, no mutation.
  R-3.7 — Missing both project_slug and clear → 400 {"error": "bad_request"}.
  R-3.8 — Binding stays 127.0.0.1 (inherits existing).
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


def _snapshot_vault(vault: pathlib.Path) -> dict:
    """Return {relpath: bytes} for every file under vault — used to verify
    no-mutation invariants."""
    out = {}
    for p in sorted(vault.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(vault))] = p.read_bytes()
    return out


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

    def _put_json(self, path: str, body: dict) -> tuple[int, dict]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self._url(path),
            data=data,
            method="PUT",
            headers={"Content-Type": "application/json"},
        )
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))


class TestFocusPut(_Case):
    def test_put_today_with_valid_pair_sets_focus(self):
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-i01", {}, title="Today candidate")

        status, body = self._put_json(
            "/api/focus/today",
            {"project_slug": "TEST-PROJECT", "intent_slug": "TEST-PROJECT-i01"},
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(body["today"])
        self.assertEqual(body["today"]["intent_slug"], "TEST-PROJECT-i01")

        # Round-trip via GET.
        get_status, get_body = self._get_json("/api/focus")
        self.assertEqual(get_status, 200)
        self.assertIsNotNone(get_body["today"])
        self.assertEqual(get_body["today"]["intent_slug"], "TEST-PROJECT-i01")

    def test_put_today_with_clear_removes_focus(self):
        today = datetime.date.today().isoformat()
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        intent_path = _make_intent(proj, "TEST-PROJECT-i02",
                                   {"focus_today": today},
                                   title="To clear")

        status, body = self._put_json("/api/focus/today", {"clear": True})
        self.assertEqual(status, 200)
        self.assertIsNone(body["today"])

        # GET confirms null.
        _, get_body = self._get_json("/api/focus")
        self.assertIsNone(get_body["today"])

        # File on disk no longer carries focus_today.
        text = intent_path.read_text(encoding="utf-8")
        self.assertNotIn("focus_today:", text)

    def test_put_unknown_slug_returns_404_no_mutation(self):
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-i03", {}, title="Untouched")

        before = _snapshot_vault(self.vault)
        status, body = self._put_json(
            "/api/focus/today",
            {"project_slug": "NOPE", "intent_slug": "NOPE"},
        )
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "intent_not_found"})

        after = _snapshot_vault(self.vault)
        self.assertEqual(before, after)

    def test_put_empty_body_returns_400(self):
        before = _snapshot_vault(self.vault)
        status, body = self._put_json("/api/focus/today", {})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "bad_request"})

        after = _snapshot_vault(self.vault)
        self.assertEqual(before, after)

    def test_put_week_with_valid_pair_sets_week_focus(self):
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-w01", {}, title="Week candidate")

        status, body = self._put_json(
            "/api/focus/week",
            {"project_slug": "TEST-PROJECT", "intent_slug": "TEST-PROJECT-w01"},
        )
        self.assertEqual(status, 200)
        self.assertIsNotNone(body["week"])
        self.assertEqual(body["week"]["intent_slug"], "TEST-PROJECT-w01")
        expected_token = datetime.date.today().strftime("%G-W%V")
        self.assertEqual(body["week"]["picked_on"], expected_token)

    def test_put_today_does_not_touch_week_slot(self):
        week_token = datetime.date.today().strftime("%G-W%V")
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        _make_intent(proj, "TEST-PROJECT-wkeep",
                     {"focus_week": week_token}, title="Keep week")
        _make_intent(proj, "TEST-PROJECT-tnew", {}, title="New today")

        status, _ = self._put_json(
            "/api/focus/today",
            {"project_slug": "TEST-PROJECT", "intent_slug": "TEST-PROJECT-tnew"},
        )
        self.assertEqual(status, 200)

        get_status, get_body = self._get_json("/api/focus")
        self.assertEqual(get_status, 200)
        self.assertIsNotNone(get_body["today"])
        self.assertEqual(get_body["today"]["intent_slug"], "TEST-PROJECT-tnew")
        self.assertIsNotNone(get_body["week"])
        self.assertEqual(get_body["week"]["intent_slug"], "TEST-PROJECT-wkeep")


if __name__ == "__main__":
    unittest.main()
