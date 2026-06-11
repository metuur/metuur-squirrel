#!/usr/bin/env python3
"""
test_vault_recovery_api.py — when a vault is configured but its directory is
missing / empty / unstructured, the backend returns a recoverable, machine-
readable error (HTTP 409 + `code`) so the UIs can guide re-setup instead of
silently returning empty data. A well-formed vault still returns 200.
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
    for mod in ("server", "config_loader"):
        sys.modules.pop(mod, None)
    import config_loader, server  # noqa: F811
    config_loader.DEFAULT_CONFIG_PATH = home / ".squirrel" / "config.toml"
    config_loader.DEFAULT_STATE_DIR = home / ".squirrel" / "state"
    server.DEV_MODE = True
    srv = server.build_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return srv, server, port


class VaultRecoveryApiTest(unittest.TestCase):
    def setUp(self):
        self._prev_home = os.environ.get("HOME")
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        (self.home / ".squirrel").mkdir(parents=True)
        self.vault = self.home / "vault"

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _write_config(self):
        (self.home / ".squirrel" / "config.toml").write_text(textwrap.dedent(f"""\
            machine_environment = "test"

            [[vaults]]
            name = "test"
            path = "{self.vault}"
            default = true
            """))

    def _start(self):
        self._write_config()
        self.srv, self.server, self.port = _spawn(self.home)

    def _me(self):
        """Return (status, parsed_body)."""
        try:
            r = urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/api/me", timeout=3)
            return r.status, json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode("utf-8"))

    def test_ok_vault_returns_200(self):
        shutil.copytree(FIXTURE_VAULT, self.vault)
        self._start()
        status, body = self._me()
        self.assertEqual(status, 200)
        self.assertEqual(body["active_workspace"]["name"], "test")

    def test_missing_vault_returns_409_vault_missing(self):
        # Configured, but the directory does not exist on disk.
        self._start()
        status, body = self._me()
        self.assertEqual(status, 409)
        self.assertEqual(body["code"], "VAULT_MISSING")
        self.assertEqual(body["vault"]["path"], str(self.vault))

    def test_empty_vault_returns_409_vault_empty(self):
        self.vault.mkdir()
        (self.vault / ".DS_Store").write_text("")  # dotfiles don't count
        self._start()
        status, body = self._me()
        self.assertEqual(status, 409)
        self.assertEqual(body["code"], "VAULT_EMPTY")

    def test_unstructured_vault_returns_409_with_migrate_command(self):
        # Has content but none of the Squirrel PARA folders (raw Obsidian vault).
        self.vault.mkdir()
        (self.vault / "00-Dashboard").mkdir()
        (self.vault / "Some Note.md").write_text("# hi\n")
        self._start()
        status, body = self._me()
        self.assertEqual(status, 409)
        self.assertEqual(body["code"], "VAULT_UNSTRUCTURED")
        self.assertEqual(body["migrate_command"], f"/sq-migrate-vault {self.vault}")


if __name__ == "__main__":
    unittest.main()
