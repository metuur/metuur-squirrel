#!/usr/bin/env python3
"""
test_api_me_dev_flag.py — /api/me exposes a `dev` flag so the UIs can badge
local/dev runs distinctly from the installed (tokened) app.
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
    srv = server.build_server("127.0.0.1", 0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.05)
    return srv, server, port


class ApiMeDevFlagTest(unittest.TestCase):
    def setUp(self):
        self._prev_home = os.environ.get("HOME")
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        (self.home / ".squirrel").mkdir(parents=True)
        self.vault = self.home / "vault"
        shutil.copytree(FIXTURE_VAULT, self.vault)
        (self.home / ".squirrel" / "config.toml").write_text(textwrap.dedent(f"""\
            machine_environment = "test"

            [[vaults]]
            name = "test"
            path = "{self.vault}"
            default = true
            """))
        self.srv, self.server, self.port = _spawn(self.home)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.tmp.cleanup()
        if self._prev_home is not None:
            os.environ["HOME"] = self._prev_home

    def _me(self):
        r = urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/me", timeout=3)
        return json.loads(r.read().decode("utf-8"))

    def test_me_reports_dev_true_in_dev_mode(self):
        self.server.DEV_MODE = True
        me = self._me()
        self.assertIn("dev", me)
        self.assertTrue(me["dev"])

    def test_me_reports_dev_false_when_tokened(self):
        self.server.DEV_MODE = False
        me = self._me()
        self.assertIn("dev", me)
        self.assertFalse(me["dev"])


if __name__ == "__main__":
    unittest.main()
