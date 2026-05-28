#!/usr/bin/env python3
"""
Story 1.2 + 9.1 — verify the `squirrel web` subcommand group.

Acceptance:
  R-1.2  start writes PID file and prints URL.
  R-1.5  --port accepted.
  R-1.6  stop sends SIGTERM, removes PID file.
  R-1.7  status prints 'running on <URL>' (exit 0) or 'not running' (exit 1).
  R-1.9  uninstall stops + cleans PID file + launchd plist.
  R-14.1 uninstall stops the server, removes PID + plist.
  R-14.3 removing the entire companions/web-ui/ directory does NOT break
         any other squirrel command.
"""

import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
SQUIRREL = REPO / "squirrel"
FIXTURE_VAULT = REPO / "tests" / "fixtures" / "vault-minimal"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _run(home: pathlib.Path, *args: str, timeout: float = 10):
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(SQUIRREL), *args],
        capture_output=True, text=True, env=env, cwd=str(REPO),
        timeout=timeout,
    )


class _CliCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        (self.home / ".squirrel").mkdir(parents=True)
        (self.home / ".squirrel" / "config.toml").write_text(
            textwrap.dedent(
                f"""\
                machine_environment = "test"

                [[vaults]]
                name = "test"
                path = "{FIXTURE_VAULT}"
                default = true
                """
            )
        )

    def tearDown(self):
        # Always try to stop a server that might still be alive
        _run(self.home, "web", "stop", timeout=10)
        self.tmp.cleanup()


class TestWebCliLifecycle(_CliCase):
    def test_start_writes_pid_and_status_reports_running(self):
        port = _free_port()
        r = _run(self.home, "web", "start", "--port", str(port))
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("http://", r.stdout)
        pid_file = self.home / ".squirrel" / "web-ui.pid"
        self.assertTrue(pid_file.is_file())
        time.sleep(0.3)  # let server bind
        s = _run(self.home, "web", "status")
        # R-1.7: exit 0 when running, prints 'running on <URL>'
        self.assertEqual(s.returncode, 0, msg=s.stdout + s.stderr)
        self.assertIn("running", s.stdout)

    def test_stop_removes_pid_file(self):
        port = _free_port()
        _run(self.home, "web", "start", "--port", str(port))
        time.sleep(0.2)
        r = _run(self.home, "web", "stop")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertFalse((self.home / ".squirrel" / "web-ui.pid").is_file())

    def test_status_when_not_running_exits_1(self):
        r = _run(self.home, "web", "status")
        self.assertEqual(r.returncode, 1)
        self.assertIn("not running", r.stdout)

    def test_uninstall_removes_pid_and_plist(self):
        port = _free_port()
        _run(self.home, "web", "start", "--port", str(port))
        time.sleep(0.2)
        # Fabricate a fake launchd plist to verify cleanup
        plist_dir = self.home / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True)
        plist = plist_dir / "org.squirrel.web-ui.plist"
        plist.write_text("<?xml version='1.0'?><plist><dict></dict></plist>")
        r = _run(self.home, "web", "uninstall")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertFalse((self.home / ".squirrel" / "web-ui.pid").is_file())
        self.assertFalse(plist.is_file())


class TestSquirrelStillWorksWithoutWebUIDir(unittest.TestCase):
    """R-14.3 — removing companions/web-ui/ does not break other commands."""

    def test_squirrel_chunk_succeeds_when_web_ui_dir_absent(self):
        # Don't actually rm -rf the real dir; copy the squirrel CLI to a
        # detached location and run it from there.
        tmp = tempfile.TemporaryDirectory()
        try:
            staging = pathlib.Path(tmp.name) / "squirrel-no-web"
            staging.mkdir()
            shutil.copy(SQUIRREL, staging / "squirrel")
            shutil.copytree(REPO / "lib", staging / "lib")
            # Vault-independent command — needs no config:
            r = subprocess.run(
                [sys.executable, str(staging / "squirrel"), "chunk", "--minutes", "60"],
                capture_output=True, text=True, cwd=str(staging), timeout=10,
            )
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertIn("chunks", r.stdout)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
