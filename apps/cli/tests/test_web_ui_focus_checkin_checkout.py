#!/usr/bin/env python3
"""
Story 8.2 — Integration tests for POST /api/focus/checkin and POST /api/focus/checkout.
Story 8.3 — Integration tests for GET /api/focus/history.

Acceptance (8.2):
  R-3.1 — POST /api/focus/checkin inserts a work_sessions row with checkout_at IS NULL.
  R-3.2 — POST /api/focus/checkout closes the open session and returns duration_minutes.
  R-3.3 — checkout writes time_invested_minutes to the intent file frontmatter.
  R-3.4 — A second checkin→checkout accumulates correctly.
  R-3.7 — checkout returns 409 when no open session exists.

Acceptance (8.3):
  R-4.1 — GET /api/focus/history?date= returns picks and sessions for that date.
  R-4.2 — GET /api/focus/history?from=&to= returns inclusive range.
  R-4.3 — No params defaults to today.
  R-4.4 — duration_minutes is computed for closed sessions, null for open ones.
"""

import datetime
import json
import os
import pathlib
import shutil
import sqlite3
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

sys.path.insert(0, str(MONOREPO / "apps" / "backend"))
sys.path.insert(0, str(REPO / "lib"))

FIXTURE_VAULT = REPO / "tests" / "fixtures" / "vault-minimal"


def _spawn(home: pathlib.Path):
    os.environ["HOME"] = str(home)
    for mod in list(sys.modules.keys()):
        if mod in ("server", "config_loader", "vocabulary", "capture_writer",
                   "status_aggregator", "deadline_scanner", "focus_picker",
                   "intent_parser", "db"):
            del sys.modules[mod]
    # Patch config_loader BEFORE importing db/server so DEFAULT_STATE_DIR is
    # captured correctly by db.py's module-level import.
    import config_loader
    config_loader.DEFAULT_CONFIG_PATH = home / ".squirrel" / "config.toml"
    config_loader.DEFAULT_STATE_DIR = home / ".squirrel" / "state"
    import db
    db.DEFAULT_STATE_DIR = home / ".squirrel" / "state"
    import server
    srv = server.build_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return srv, port


def _make_intent(folder: pathlib.Path, slug: str, title: str = "Test Intent") -> pathlib.Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{slug}.md"
    path.write_text(textwrap.dedent(f"""\
        ---
        id: {slug}
        estado: in-progress
        ---
        # {title}
    """))
    return path


def _make_home(tmp: pathlib.Path, vault_name: str = "testvault") -> pathlib.Path:
    home = tmp / "home"
    vault = home / "vaults" / vault_name
    shutil.copytree(FIXTURE_VAULT, vault)
    config = home / ".squirrel" / "config.toml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f'[[vaults]]\nname = "{vault_name}"\npath = "{vault}"\ndefault = true\n')
    return home


def _get(port: int, path: str, cookie: str) -> dict:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        headers={"Cookie": cookie},
    )
    with urllib.request.urlopen(req, timeout=3) as r:
        return json.loads(r.read())


def _post(port: int, path: str, cookie: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json", "Cookie": cookie},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


class TestCheckinCheckout(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        vault_name = "testvault"
        self.home = _make_home(self.tmp, vault_name)
        self.vault = self.home / "vaults" / vault_name
        # Create a test intent
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        _make_intent(proj, "TEST-001")
        self.srv, self.port = _spawn(self.home)
        self.cookie = f"squirrel_vault={vault_name}"

    def tearDown(self):
        self.srv.shutdown()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _db_conn(self) -> sqlite3.Connection:
        db_path = self.home / ".squirrel" / "state" / "squirrel.db"
        return sqlite3.connect(str(db_path))

    def test_checkin_inserts_open_session(self):
        res = _post(self.port, "/api/focus/checkin", self.cookie, {
            "project_slug": "TEST-PROJECT",
            "intent_slug": "TEST-001",
            "slot": "today",
        })
        self.assertIn("session_id", res)

        conn = self._db_conn()
        row = conn.execute(
            "SELECT checkout_at FROM work_sessions WHERE id = ?",
            (res["session_id"],),
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row, "session row should exist")
        self.assertIsNone(row[0], "checkout_at should be NULL for open session")

    def test_checkout_closes_session_and_returns_duration(self):
        checkin_res = _post(self.port, "/api/focus/checkin", self.cookie, {
            "project_slug": "TEST-PROJECT",
            "intent_slug": "TEST-001",
            "slot": "today",
        })
        session_id = checkin_res["session_id"]

        checkout_res = _post(self.port, "/api/focus/checkout", self.cookie)
        self.assertEqual(checkout_res["session_id"], session_id)
        self.assertGreaterEqual(checkout_res["duration_minutes"], 0)
        self.assertIn("time_invested_minutes", checkout_res)

        conn = self._db_conn()
        row = conn.execute(
            "SELECT checkout_at FROM work_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row[0], "checkout_at should be set after checkout")

    def test_checkout_writes_time_invested_to_frontmatter(self):
        _post(self.port, "/api/focus/checkin", self.cookie, {
            "project_slug": "TEST-PROJECT",
            "intent_slug": "TEST-001",
            "slot": "today",
        })
        _post(self.port, "/api/focus/checkout", self.cookie)

        intent_path = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT" / "TEST-001.md"
        content = intent_path.read_text()
        self.assertIn("time_invested_minutes", content)

    def test_accumulated_time_invested_across_sessions(self):
        for _ in range(2):
            _post(self.port, "/api/focus/checkin", self.cookie, {
                "project_slug": "TEST-PROJECT",
                "intent_slug": "TEST-001",
                "slot": "today",
            })
            res = _post(self.port, "/api/focus/checkout", self.cookie)

        self.assertGreaterEqual(res["time_invested_minutes"], 0)
        conn = self._db_conn()
        count = conn.execute(
            "SELECT COUNT(*) FROM work_sessions WHERE project_slug = 'TEST-PROJECT'"
            " AND intent_slug = 'TEST-001' AND checkout_at IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        self.assertEqual(count, 2)

    def test_checkout_returns_409_when_no_open_session(self):
        res = _post(self.port, "/api/focus/checkout", self.cookie)
        self.assertEqual(res.get("error"), "no_open_session")

    def test_checkin_requires_project_and_intent(self):
        res = _post(self.port, "/api/focus/checkin", self.cookie, {})
        self.assertIn("error", res)


class TestFocusHistory(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        vault_name = "testvault"
        self.home = _make_home(self.tmp, vault_name)
        self.vault = self.home / "vaults" / vault_name
        proj = self.vault / "01-Proyectos-Activos" / "TEST-PROJECT"
        _make_intent(proj, "TEST-001")
        self.srv, self.port = _spawn(self.home)
        self.cookie = f"squirrel_vault={vault_name}"

    def tearDown(self):
        self.srv.shutdown()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _seed_session(self, date: str, checked_out: bool = True):
        """Insert a work_sessions row directly for a specific date."""
        db_path = self.home / ".squirrel" / "state" / "squirrel.db"
        conn = sqlite3.connect(str(db_path))
        checkin = f"{date}T10:00:00+00:00"
        checkout = f"{date}T10:30:00+00:00" if checked_out else None
        conn.execute(
            "INSERT INTO work_sessions (vault, slot, date, project_slug, intent_slug, checkin_at, checkout_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("testvault", "today", date, "TEST-PROJECT", "TEST-001", checkin, checkout),
        )
        conn.commit()
        conn.close()

    def test_history_defaults_to_today(self):
        res = _get(self.port, "/api/focus/history", self.cookie)
        self.assertIn("picks", res)
        self.assertIn("sessions", res)

    def test_history_date_filter(self):
        self._seed_session("2026-01-15")
        self._seed_session("2026-01-16")
        res = _get(self.port, "/api/focus/history?date=2026-01-15", self.cookie)
        self.assertEqual(len(res["sessions"]), 1)
        self.assertEqual(res["sessions"][0]["date"], "2026-01-15")

    def test_history_range_filter(self):
        self._seed_session("2026-02-01")
        self._seed_session("2026-02-03")
        self._seed_session("2026-02-05")
        res = _get(self.port, "/api/focus/history?from=2026-02-01&to=2026-02-03", self.cookie)
        self.assertEqual(len(res["sessions"]), 2)

    def test_duration_minutes_computed_for_closed_session(self):
        self._seed_session("2026-03-01", checked_out=True)
        res = _get(self.port, "/api/focus/history?date=2026-03-01", self.cookie)
        self.assertEqual(len(res["sessions"]), 1)
        self.assertEqual(res["sessions"][0]["duration_minutes"], 30)

    def test_duration_minutes_null_for_open_session(self):
        self._seed_session("2026-03-02", checked_out=False)
        res = _get(self.port, "/api/focus/history?date=2026-03-02", self.cookie)
        self.assertIsNone(res["sessions"][0]["duration_minutes"])


if __name__ == "__main__":
    unittest.main()
