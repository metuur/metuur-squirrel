#!/usr/bin/env python3
"""
Story 1.1 — verify lib/db.py schema and connection behaviour.

Acceptance:
  R-2.1 — get_conn opens squirrel.db with WAL journal mode.
  R-2.2 — init_schema creates focus_picks and work_sessions tables.
  R-2.3 — init_schema is idempotent (safe to call twice).
"""

import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from db import get_conn, init_schema  # noqa: E402


class TestGetConn(unittest.TestCase):
    def test_returns_connection_to_db_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            conn = get_conn(tmp_path)
            try:
                db_file = tmp_path / "squirrel.db"
                self.assertTrue(db_file.exists(), "squirrel.db should be created")
            finally:
                conn.close()

    def test_wal_journal_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            conn = get_conn(tmp_path)
            try:
                row = conn.execute("PRAGMA journal_mode").fetchone()
                self.assertEqual(row[0], "wal")
            finally:
                conn.close()

    def test_each_call_returns_new_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            conn1 = get_conn(tmp_path)
            conn2 = get_conn(tmp_path)
            try:
                self.assertIsNot(conn1, conn2)
            finally:
                conn1.close()
                conn2.close()

    def test_state_dir_created_if_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            nested = pathlib.Path(tmp) / "new" / "nested"
            conn = get_conn(nested)
            try:
                self.assertTrue(nested.exists())
            finally:
                conn.close()


class TestInitSchema(unittest.TestCase):
    def _tables(self, conn):
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return {r[0] for r in rows}

    def test_creates_both_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = get_conn(pathlib.Path(tmp))
            try:
                init_schema(conn)
                tables = self._tables(conn)
                self.assertIn("focus_picks", tables)
                self.assertIn("work_sessions", tables)
            finally:
                conn.close()

    def test_idempotent_double_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = get_conn(pathlib.Path(tmp))
            try:
                init_schema(conn)
                init_schema(conn)  # second call must not raise
                tables = self._tables(conn)
                self.assertIn("focus_picks", tables)
                self.assertIn("work_sessions", tables)
            finally:
                conn.close()

    def test_focus_picks_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = get_conn(pathlib.Path(tmp))
            try:
                init_schema(conn)
                cols = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(focus_picks)").fetchall()
                }
                expected = {
                    "id", "vault", "slot", "date",
                    "project_slug", "intent_slug", "picked_at", "cleared_at",
                }
                self.assertEqual(cols, expected)
            finally:
                conn.close()

    def test_work_sessions_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = get_conn(pathlib.Path(tmp))
            try:
                init_schema(conn)
                cols = {
                    row[1]
                    for row in conn.execute(
                        "PRAGMA table_info(work_sessions)"
                    ).fetchall()
                }
                expected = {
                    "id", "vault", "slot", "date",
                    "project_slug", "intent_slug", "checkin_at", "checkout_at",
                }
                self.assertEqual(cols, expected)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
