#!/usr/bin/env python3
"""
test_config_vault_api.py — POST /api/config/vault (story in-app-vault-onboarding 3.1).

Covers EARS R-3.3, R-3.4, R-3.5, R-3.6, R-3.7, R-3.10, R-3.11, R-3.12, R-3.13.
"""

import json
import os
import pathlib
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


def _spawn(home: pathlib.Path):
    os.environ["HOME"] = str(home)
    for mod in ("server", "config_loader"):
        sys.modules.pop(mod, None)
    import config_loader, server  # noqa: F811
    config_loader.DEFAULT_CONFIG_PATH = home / ".squirrel" / "config.toml"
    config_loader.DEFAULT_STATE_DIR = home / ".squirrel" / "state"
    srv = server.build_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return srv, config_loader, port


class ConfigVaultApiTest(unittest.TestCase):

    def setUp(self):
        self._prev_home = os.environ.get("HOME")
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        (self.home / ".squirrel").mkdir(parents=True)
        # Seed config like install.sh does: a default vault named "personal".
        cfg = textwrap.dedent(f"""\
            default_email = "u@example.com"
            machine_environment = "personal"

            [[vaults]]
            name = "personal"
            path = "{self.home}/seeded-vault"
            default = true
            """)
        (self.home / ".squirrel" / "config.toml").write_text(cfg)
        (self.home / "seeded-vault").mkdir()
        self.srv, self.config_loader, self.port = _spawn(self.home)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _req(self, method, path, payload=None):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if data else {}
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=data,
            headers=headers, method=method)
        try:
            r = urllib.request.urlopen(req, timeout=3)
        except urllib.error.HTTPError as he:
            return he.code, json.loads(he.read().decode("utf-8"))
        return r.status, json.loads(r.read().decode("utf-8"))

    def _vault_names_and_default(self):
        vaults = self.config_loader.list_vaults(
            config_path=self.home / ".squirrel" / "config.toml")
        names = sorted(v.name for v in vaults)
        defaults = [v.name for v in vaults if v.default]
        return names, defaults

    # ── R-3.4 / R-3.6 / R-3.7 / R-3.11: create + idempotent upsert ───────────
    def test_create_new_folder_and_persist_default(self):
        target = self.home / "fresh-vault"
        status, data = self._req("POST", "/api/config/vault",
                                  {"path": str(target), "create": True})
        self.assertEqual(status, 200)
        self.assertTrue(target.is_dir())          # R-3.4 folder created
        self.assertEqual(data["name"], "personal")  # R-3.7 default name
        self.assertTrue(data["default"])
        names, defaults = self._vault_names_and_default()
        self.assertEqual(names, ["personal"])
        self.assertEqual(defaults, ["personal"])  # R-3.11 idempotent upsert
        # path updated to the new folder
        self.assertEqual(str(pathlib.Path(data["path"])), str(target.resolve()))

    def test_idempotent_repeat_post(self):
        target = self.home / "fresh-vault"
        target.mkdir()
        s1, _ = self._req("POST", "/api/config/vault", {"path": str(target)})
        s2, _ = self._req("POST", "/api/config/vault", {"path": str(target)})
        self.assertEqual((s1, s2), (200, 200))
        _, defaults = self._vault_names_and_default()
        self.assertEqual(defaults, ["personal"])

    def test_new_named_vault_becomes_sole_default(self):
        target = self.home / "research"
        target.mkdir()
        status, data = self._req("POST", "/api/config/vault",
                                  {"name": "research", "path": str(target)})
        self.assertEqual(status, 200)
        names, defaults = self._vault_names_and_default()
        self.assertEqual(names, ["personal", "research"])
        self.assertEqual(defaults, ["research"])  # R-3.10 sole default

    # ── R-3.12: path sandbox ─────────────────────────────────────────────────
    def test_relative_path_rejected(self):
        status, data = self._req("POST", "/api/config/vault",
                                  {"path": "../../etc/evil", "create": True})
        self.assertEqual(status, 400)
        self.assertFalse((self.home / ".." / ".." / "etc" / "evil").exists())

    def test_absolute_path_outside_home_rejected(self):
        outside = "/tmp/squirrel-escape-test-xyz"
        status, data = self._req("POST", "/api/config/vault",
                                  {"path": outside, "create": True})
        self.assertEqual(status, 400)
        self.assertFalse(pathlib.Path(outside).exists())

    # ── R-3.13: name charset ─────────────────────────────────────────────────
    def test_name_with_space_rejected(self):
        target = self.home / "x"
        target.mkdir()
        status, _ = self._req("POST", "/api/config/vault",
                              {"name": "bad name", "path": str(target)})
        self.assertEqual(status, 400)

    def test_name_with_quote_rejected(self):
        target = self.home / "y"
        target.mkdir()
        status, _ = self._req("POST", "/api/config/vault",
                              {"name": 'evil";x', "path": str(target)})
        self.assertEqual(status, 400)

    # ── R-3.5: missing/non-dir path ──────────────────────────────────────────
    def test_missing_path_rejected(self):
        status, _ = self._req("POST", "/api/config/vault", {"name": "x"})
        self.assertEqual(status, 400)

    def test_nonexistent_without_create_rejected(self):
        target = self.home / "does-not-exist"
        status, _ = self._req("POST", "/api/config/vault",
                              {"path": str(target), "create": False})
        self.assertEqual(status, 400)
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
