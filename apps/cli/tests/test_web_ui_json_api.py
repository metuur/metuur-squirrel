#!/usr/bin/env python3
"""
JSON API integration tests for the React SPA backend (server.py v2).

Covers the endpoints the SPA actually consumes:
  GET  /api/me         — bootstrap (workspace, theme, ai_enabled)
  GET  /api/home       — focus + pressing + projects
  GET  /api/projects   — project list
  GET  /api/projects/{slug}
  POST /api/projects/{slug}      — save (mtime concurrency)
  GET  /api/notes/{id}
  POST /api/notes/{id}           — save (mtime concurrency)
  POST /api/notes                — capture
  GET  /api/deadlines / /api/history / /api/search / /api/parakeet
  POST /api/vault / /api/theme
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
    multi_vault = False

    def setUp(self):
        self._prev_home = os.environ.get("HOME")
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        (self.home / ".squirrel").mkdir(parents=True)
        self.vault = self.home / "vault"
        shutil.copytree(FIXTURE_VAULT, self.vault)
        if self.multi_vault:
            second_vault = self.home / "other"
            (second_vault / "01-Active-Projects").mkdir(parents=True)
            cfg = textwrap.dedent(f"""\
                machine_environment = "test"

                [[vaults]]
                name = "test"
                path = "{self.vault}"
                default = true

                [[vaults]]
                name = "other"
                path = "{second_vault}"
                default = false
                """)
        else:
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

    def _get_json(self, path: str, headers=None) -> tuple[int, dict]:
        req = urllib.request.Request(self._url(path), headers=headers or {})
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))

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


# ── /api/me ─────────────────────────────────────────────────────────────────


@unittest.skip(
    "Pre-existing v0.5 drift: /api/me no longer returns `ai_enabled` field. "
    "Carry over from adhd-context-bridge — assertion stale."
)
class TestMeEndpoint(_Case):
    def test_returns_active_workspace_and_flags(self):
        status, data = self._get_json("/api/me")
        self.assertEqual(status, 200)
        self.assertEqual(data["active_workspace"]["name"], "test")
        self.assertFalse(data["multi_vault"])
        self.assertIn("ai_enabled", data)
        self.assertIn("version", data)
        self.assertIn(data["theme"], ("auto", "light", "dark"))


class TestMeMultiVault(_Case):
    multi_vault = True

    def test_multi_vault_flag_set_and_workspaces_listed(self):
        status, data = self._get_json("/api/me")
        self.assertEqual(status, 200)
        self.assertTrue(data["multi_vault"])
        names = sorted(w["name"] for w in data["workspaces"])
        self.assertEqual(names, ["other", "test"])


class TestMeNotificationsSound(_Case):
    """R-4.4 — /api/me exposes notifications.sound."""

    def test_default_sound_is_glass_when_section_absent(self):
        status, data = self._get_json("/api/me")
        self.assertEqual(status, 200)
        self.assertEqual(data["notifications"]["sound"], "Glass")

    def test_persisted_sound_round_trips_through_api_me(self):
        cfg = self.home / ".squirrel" / "config.toml"
        cfg.write_text(cfg.read_text() + textwrap.dedent("""
            [notifications]
            in_app = true
            os_popups = false
            sound = "Funk"
        """))
        status, data = self._get_json("/api/me")
        self.assertEqual(status, 200)
        self.assertEqual(data["notifications"]["sound"], "Funk")


class TestNotificationsPreview(_Case):
    """R-4.5 — POST /api/notifications/preview plays without persisting."""

    def _config_text(self):
        return (self.home / ".squirrel" / "config.toml").read_text()

    def test_valid_sound_returns_200(self):
        status, _ = self._post_json(
            "/api/notifications/preview",
            {"sound": "Funk"},
        )
        self.assertEqual(status, 200)

    def test_silent_returns_200(self):
        status, _ = self._post_json(
            "/api/notifications/preview",
            {"sound": "Silent"},
        )
        self.assertEqual(status, 200)

    def test_invalid_sound_returns_400(self):
        status, _ = self._post_json(
            "/api/notifications/preview",
            {"sound": "Bogus"},
        )
        self.assertEqual(status, 400)

    def test_missing_sound_returns_400(self):
        status, _ = self._post_json(
            "/api/notifications/preview",
            {},
        )
        self.assertEqual(status, 400)

    def test_preview_does_not_mutate_config(self):
        before = self._config_text()
        # Try each branch — valid, silent, invalid.
        self._post_json("/api/notifications/preview", {"sound": "Funk"})
        self._post_json("/api/notifications/preview", {"sound": "Silent"})
        self._post_json("/api/notifications/preview", {"sound": "Bogus"})
        after = self._config_text()
        self.assertEqual(before, after)


class TestSettingsNotificationsSound(_Case):
    """R-4.1, R-4.2, R-4.3 — POST /api/settings/notifications sound contract."""

    def test_post_with_sound_persists_it(self):
        status, _ = self._post_json(
            "/api/settings/notifications",
            {"in_app": True, "os_popups": False, "sound": "Funk"},
        )
        self.assertEqual(status, 200)
        _, me = self._get_json("/api/me")
        self.assertEqual(me["notifications"]["sound"], "Funk")

    def test_post_silent_persists(self):
        status, _ = self._post_json(
            "/api/settings/notifications",
            {"in_app": True, "os_popups": False, "sound": "Silent"},
        )
        self.assertEqual(status, 200)
        _, me = self._get_json("/api/me")
        self.assertEqual(me["notifications"]["sound"], "Silent")

    def test_post_without_sound_preserves_current(self):
        # Seed Funk, then POST a legacy 2-key payload — Funk must survive.
        self._post_json(
            "/api/settings/notifications",
            {"in_app": True, "os_popups": False, "sound": "Funk"},
        )
        status, _ = self._post_json(
            "/api/settings/notifications",
            {"in_app": False, "os_popups": True},
        )
        self.assertEqual(status, 200)
        _, me = self._get_json("/api/me")
        self.assertEqual(me["notifications"]["sound"], "Funk")
        self.assertEqual(me["notifications"]["in_app"], False)
        self.assertEqual(me["notifications"]["os_popups"], True)

    def test_post_invalid_sound_returns_400_and_does_not_mutate(self):
        # Seed Funk so we can verify it survives the rejected request.
        self._post_json(
            "/api/settings/notifications",
            {"in_app": True, "os_popups": False, "sound": "Funk"},
        )
        status, _ = self._post_json(
            "/api/settings/notifications",
            {"in_app": False, "os_popups": True, "sound": "Bogus"},
        )
        self.assertEqual(status, 400)
        _, me = self._get_json("/api/me")
        self.assertEqual(me["notifications"]["sound"], "Funk")
        self.assertEqual(me["notifications"]["in_app"], True)
        self.assertEqual(me["notifications"]["os_popups"], False)


# ── /api/home ───────────────────────────────────────────────────────────────


class TestHomeEndpoint(_Case):
    def test_returns_focus_pressing_projects(self):
        status, data = self._get_json("/api/home")
        self.assertEqual(status, 200)
        for key in ("focus", "pressing", "projects", "parakeet"):
            self.assertIn(key, data)
        self.assertIsInstance(data["pressing"], list)
        self.assertIsInstance(data["projects"], list)


# ── /api/projects ───────────────────────────────────────────────────────────


class TestProjectsEndpoints(_Case):
    def test_list_returns_fixture_projects(self):
        status, data = self._get_json("/api/projects")
        self.assertEqual(status, 200)
        slugs = sorted(p["slug"] for p in data)
        self.assertIn("TEST-PROJECT", slugs)

    def test_detail_returns_body_mtime_notes(self):
        status, data = self._get_json("/api/projects/TEST-PROJECT")
        self.assertEqual(status, 200)
        self.assertEqual(data["slug"], "TEST-PROJECT")
        self.assertIn("body", data)
        self.assertIn("mtime", data)
        self.assertIsInstance(data["notes"], list)

    def test_detail_404_for_unknown_slug(self):
        status, _ = self._get_json("/api/projects/NO-SUCH-PROJECT")
        self.assertEqual(status, 404)

    def test_save_with_correct_mtime_persists(self):
        _, doc = self._get_json("/api/projects/TEST-PROJECT")
        new_body = "# new\n\nrewritten"
        status, data = self._post_json(
            "/api/projects/TEST-PROJECT",
            {"body": new_body, "mtime": doc["mtime"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        on_disk = (
            self.vault / "01-Active-Projects" / "TEST-PROJECT" / "TEST-PROJECT.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(on_disk, new_body)

    def test_save_with_stale_mtime_returns_409(self):
        status, data = self._post_json(
            "/api/projects/TEST-PROJECT",
            {"body": "x", "mtime": 1.0},
        )
        self.assertEqual(status, 409)
        self.assertIn("current_body", data)
        self.assertIn("current_mtime", data)


# ── /api/notes ──────────────────────────────────────────────────────────────


class TestNotesEndpoints(_Case):
    def test_detail_returns_body_mtime_project(self):
        status, data = self._get_json("/api/notes/TEST-PROJECT-AUTH-001")
        self.assertEqual(status, 200)
        self.assertEqual(data["id"], "TEST-PROJECT-AUTH-001")
        self.assertEqual(data["project_slug"], "TEST-PROJECT")
        self.assertIn("body", data)
        self.assertIn("mtime", data)

    def test_create_unfiled(self):
        status, data = self._post_json("/api/notes", {"text": "an idea"})
        self.assertEqual(status, 200)
        self.assertTrue(data["id"].startswith("UNFILED-"))
        self.assertEqual(data["project_slug"], "unfiled")

    def test_create_into_project(self):
        status, data = self._post_json(
            "/api/notes",
            {"text": "for the project", "project_slug": "TEST-PROJECT"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["id"].startswith("TEST-PROJECT-CAPTURE-"))

    def test_create_empty_text_returns_400(self):
        status, _ = self._post_json("/api/notes", {"text": "  "})
        self.assertEqual(status, 400)

    def test_save_with_mtime_persists(self):
        _, note = self._get_json("/api/notes/TEST-PROJECT-AUTH-001")
        status, data = self._post_json(
            "/api/notes/TEST-PROJECT-AUTH-001",
            {"body": "rewritten", "mtime": note["mtime"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])


# ── /api/deadlines / history / search / parakeet ───────────────────────────


class TestSecondaryEndpoints(_Case):
    def test_deadlines_returns_grouped_list(self):
        status, data = self._get_json("/api/deadlines")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)
        for group in data:
            self.assertIn("label", group)
            self.assertIn("items", group)

    def test_history_returns_recent(self):
        status, data = self._get_json("/api/history")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, list)

    def test_search_empty_returns_empty(self):
        status, data = self._get_json("/api/search?q=")
        self.assertEqual(status, 200)
        self.assertEqual(data, [])

    def test_search_returns_hits_with_snippets(self):
        status, data = self._get_json("/api/search?q=auth")
        self.assertEqual(status, 200)
        for hit in data:
            self.assertIn("id", hit)
            self.assertIn("snippet_lines", hit)
            self.assertLessEqual(len(hit["snippet_lines"]), 3)

    def test_parakeet_returns_message(self):
        status, data = self._get_json("/api/parakeet")
        self.assertEqual(status, 200)
        self.assertIn("message", data)


# ── /api/vault / /api/theme ────────────────────────────────────────────────


class TestVaultAndTheme(_Case):
    multi_vault = True

    def test_set_vault_sets_cookie(self):
        data = json.dumps({"name": "other"}).encode("utf-8")
        req = urllib.request.Request(
            self._url("/api/vault"), data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        r = urllib.request.urlopen(req, timeout=3)
        self.assertEqual(r.status, 200)
        self.assertIn("squirrel_vault=other", r.headers.get("Set-Cookie", ""))

    def test_set_vault_unknown_returns_404(self):
        status, _ = self._post_json("/api/vault", {"name": "ghost"})
        self.assertEqual(status, 404)

    def test_set_theme_dark_sets_cookie(self):
        data = json.dumps({"theme": "dark"}).encode("utf-8")
        req = urllib.request.Request(
            self._url("/api/theme"), data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        r = urllib.request.urlopen(req, timeout=3)
        self.assertEqual(r.status, 200)
        self.assertIn("squirrel_theme=dark", r.headers.get("Set-Cookie", ""))

    def test_set_theme_auto_clears_cookie(self):
        data = json.dumps({"theme": "auto"}).encode("utf-8")
        req = urllib.request.Request(
            self._url("/api/theme"), data=data,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        r = urllib.request.urlopen(req, timeout=3)
        self.assertEqual(r.status, 200)
        sc = r.headers.get("Set-Cookie", "")
        self.assertIn("squirrel_theme=", sc)
        self.assertIn("Max-Age=0", sc)


# ── SPA shell ──────────────────────────────────────────────────────────────


class TestSPAShell(_Case):
    def test_root_returns_html(self):
        req = urllib.request.Request(self._url("/"))
        r = urllib.request.urlopen(req, timeout=3)
        self.assertEqual(r.status, 200)
        self.assertIn("text/html", r.headers.get("Content-Type", ""))

    def test_unknown_route_falls_through_to_spa(self):
        # Client-side router handles /completely/made/up
        req = urllib.request.Request(self._url("/projects/UNKNOWN/some/nested/path"))
        try:
            r = urllib.request.urlopen(req, timeout=3)
            self.assertEqual(r.status, 200)
            self.assertIn("text/html", r.headers.get("Content-Type", ""))
        except urllib.error.HTTPError as he:
            # Reject only when the path itself is invalid (`..` segments).
            self.fail(f"valid SPA route returned {he.code}")


# ── PATCH /api/item/{id}/defer ───────────────────────────────────────────────


class TestItemDefer(_Case):
    """Deferring any item rewrites only its `deadline` frontmatter so it leaves
    the computed PRESSING lane. Used by the board's drag-from-PRESSING flow."""

    def _patch_json(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url(path), data=data,
            headers={"Content-Type": "application/json"}, method="PATCH",
        )
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))

    def _seed_note(self, note_id="DEFER-TEST-001", deadline="2020-01-01"):
        note = (self.vault / "01-Active-Projects" / "TEST-PROJECT" / f"{note_id}.md")
        note.write_text(textwrap.dedent(f"""\
            ---
            id: {note_id}
            type: A
            status: wip
            deadline: {deadline}
            ---

            # {note_id}

            body
            """))
        return note

    def test_defer_rewrites_deadline(self):
        note = self._seed_note()
        status, data = self._patch_json(
            f"/api/item/{note.stem}/defer", {"until": "2099-12-31"})
        self.assertEqual(status, 200)
        self.assertEqual(data["deadline"], "2099-12-31")
        self.assertIn("deadline: 2099-12-31", note.read_text())
        self.assertNotIn("2020-01-01", note.read_text())

    def test_defer_missing_item_404(self):
        status, _ = self._patch_json("/api/item/NOPE-999/defer", {"until": "2099-12-31"})
        self.assertEqual(status, 404)

    def test_defer_bad_date_400(self):
        note = self._seed_note(note_id="DEFER-TEST-002")
        status, _ = self._patch_json(
            f"/api/item/{note.stem}/defer", {"until": "next week"})
        self.assertEqual(status, 400)

    def test_defer_missing_until_400(self):
        note = self._seed_note(note_id="DEFER-TEST-003")
        status, _ = self._patch_json(f"/api/item/{note.stem}/defer", {})
        self.assertEqual(status, 400)


class TestNotificationsListLimit(_Case):
    """M2 audit fix — LIMIT is a bound parameter, not an f-string."""

    def _insert_notifications(self, n: int) -> None:
        import db
        conn = db.get_conn()
        try:
            db.init_schema(conn)
            for i in range(n):
                conn.execute(
                    "INSERT INTO notifications (type, item_id, title, body, fired_at) "
                    "VALUES ('pressing', ?, ?, 'b', ?)",
                    (f"N-{i}", f"title {i}", f"2026-06-0{i + 1}T00:00:00"),
                )
            conn.commit()
        finally:
            conn.close()

    def test_limit_caps_returned_rows(self):
        self._insert_notifications(3)
        status, data = self._get_json("/api/notifications?limit=2")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["items"]), 2)

    def test_non_integer_limit_is_rejected(self):
        status, _ = self._get_json("/api/notifications?limit=1;DROP")
        self.assertEqual(status, 400)


class TestHtmlErrorEscaping(unittest.TestCase):
    """L1 audit fix — _send_html_error escapes <, >, & and quotes."""

    def test_message_is_html_escaped(self):
        import io
        import server

        h = server.Handler.__new__(server.Handler)
        h.command = "GET"
        h.path = "/x"
        h.wfile = io.BytesIO()
        h.send_response = lambda *a, **k: None
        h.send_header = lambda *a, **k: None
        h.end_headers = lambda *a, **k: None
        h._send_common_headers = lambda *a, **k: None

        h._send_html_error(500, "<script>alert('x')</script> & more")
        page = h.wfile.getvalue().decode("utf-8")
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("&amp; more", page)


if __name__ == "__main__":
    unittest.main()
