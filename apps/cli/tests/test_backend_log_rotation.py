#!/usr/bin/env python3
"""
Tests that apps/backend/server.py rotates ~/.squirrel/web-ui.log when it
exceeds LOG_MAX_BYTES, and that prior write-line semantics are preserved.

Prior behavior: each call to _write_log_line appended to an unbounded
file. New behavior (this round): RotatingFileHandler with maxBytes=10MB
and backupCount=3 — at most 4 files (.log, .log.1, .log.2, .log.3) per
user.
"""

import importlib
import os
import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
MONOREPO = REPO.parent.parent
sys.path.insert(0, str(MONOREPO / "apps" / "backend"))


def _fresh_server_with_home(home: pathlib.Path):
    """Reload server with HOME pointed at a tempdir and a tiny maxBytes
    threshold so rotation is observable inside a unit test."""
    os.environ["HOME"] = str(home)
    sys.modules.pop("server", None)
    import server as srv
    srv.LOG_MAX_BYTES = 200  # tiny — rotates after a few lines
    # Bust any cached handler from a prior test
    srv._LOG_HANDLER = None
    srv._LOG_HANDLER_PATH = None
    return srv


class WriteLogLineWritesToConfiguredPath(unittest.TestCase):
    def test_writes_appear_in_web_ui_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            srv = _fresh_server_with_home(home)
            srv._write_log_line("hello world")
            srv._get_log_handler().flush()
            log = home / ".squirrel" / "web-ui.log"
            self.assertTrue(log.is_file(), "primary log file should exist")
            self.assertIn("hello world", log.read_text(encoding="utf-8"))


class RotationCreatesBackupFiles(unittest.TestCase):
    def test_log_rotates_when_maxbytes_exceeded(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            srv = _fresh_server_with_home(home)
            # Each line is ~30 bytes; with maxBytes=200, several lines force
            # at least one rotation (creates web-ui.log.1).
            for i in range(50):
                srv._write_log_line(f"line-{i:04d} padded with extra text")
            srv._get_log_handler().flush()
            squirrel_dir = home / ".squirrel"
            files = sorted(p.name for p in squirrel_dir.iterdir() if p.name.startswith("web-ui.log"))
            # We expect web-ui.log plus at least one backup (.log.1).
            self.assertIn("web-ui.log", files, f"primary missing; got {files}")
            backups = [f for f in files if f.startswith("web-ui.log.")]
            self.assertGreaterEqual(
                len(backups), 1, f"expected at least one rotated backup, got {files}"
            )

    def test_backup_count_caps_total_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            srv = _fresh_server_with_home(home)
            # Generous burst — far more than enough to exceed backupCount.
            for i in range(2000):
                srv._write_log_line(f"line-{i:04d} padded with extra text")
            srv._get_log_handler().flush()
            squirrel_dir = home / ".squirrel"
            files = sorted(p.name for p in squirrel_dir.iterdir() if p.name.startswith("web-ui.log"))
            # backupCount=3 means at most web-ui.log + .log.1 + .log.2 + .log.3 = 4 files.
            self.assertLessEqual(
                len(files), 4,
                f"rotation should cap at 4 files (1 primary + 3 backups), got {files}",
            )


class HandlerIsCachedAcrossCalls(unittest.TestCase):
    def test_same_handler_returned_for_same_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            srv = _fresh_server_with_home(home)
            first = srv._get_log_handler()
            second = srv._get_log_handler()
            self.assertIs(first, second, "cache must return same handler for unchanged path")

    def test_handler_rebuilds_when_path_changes(self):
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            srv = _fresh_server_with_home(pathlib.Path(tmp1))
            first = srv._get_log_handler()
            # Flip HOME — emulates test isolation across cases
            os.environ["HOME"] = tmp2
            second = srv._get_log_handler()
            self.assertIsNot(first, second, "handler must rebuild after path change")


if __name__ == "__main__":
    unittest.main()
