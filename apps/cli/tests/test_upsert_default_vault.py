#!/usr/bin/env python3
"""
test_upsert_default_vault.py — Tests for config_loader.upsert_default_vault
and TOML-safe escaping in _format_vault_entry.

Story: in-app-vault-onboarding 1.1
Covers EARS: R-3.8, R-3.10, R-3.11, R-3.13 (escaping portion).
"""

import pathlib
import sys
import tempfile
import unittest

_LIB = pathlib.Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(_LIB))

import config_loader  # noqa: E402
from config_loader import (  # noqa: E402
    Vault,
    list_vaults,
    upsert_default_vault,
    _format_vault_entry,
    _load_toml,
)


CONFIG_TWO_VAULTS = """\
default_email = "user@example.com"
machine_environment = "personal"

[[vaults]]
name = "personal"
path = "~/vault-squirrel"
default = true

[[vaults]]
name = "work"
path = "/abs/work-vault"
default = false

[projects]
active = ["A", "B"]
"""

CONFIG_SCALARS_NO_VAULTS = """\
default_email = "u@example.com"
machine_environment = "work"
"""


def _write_tmp_config(text: str) -> pathlib.Path:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".toml", delete=False, encoding="utf-8"
    )
    f.write(text)
    f.close()
    return pathlib.Path(f.name)


# ─── R-3.11: idempotent upsert of an existing vault ──────────────────────────


class TestUpsertExisting(unittest.TestCase):

    def setUp(self):
        self.path = _write_tmp_config(CONFIG_TWO_VAULTS)

    def tearDown(self):
        self.path.unlink()

    def test_existing_name_updates_path_and_keeps_sole_default(self):
        # R-3.11 + R-3.10: updating "personal" must not raise on duplicate name,
        # must update its path, and leave exactly one default.
        v = upsert_default_vault("personal", "/new/personal", config_path=self.path)
        self.assertIsInstance(v, Vault)
        self.assertTrue(v.default)

        vaults = list_vaults(config_path=self.path)
        by_name = {x.name: x for x in vaults}
        self.assertEqual(str(by_name["personal"].path), "/new/personal")
        defaults = [x.name for x in vaults if x.default]
        self.assertEqual(defaults, ["personal"])

    def test_existing_non_default_becomes_sole_default(self):
        # R-3.10: promoting "work" flips "personal" to non-default.
        upsert_default_vault("work", "/abs/work-vault", config_path=self.path)
        vaults = list_vaults(config_path=self.path)
        defaults = [x.name for x in vaults if x.default]
        self.assertEqual(defaults, ["work"])

    def test_preserves_other_keys_and_entries(self):
        # R-3.8: scalars, the other vault, and the [projects] section survive.
        upsert_default_vault("personal", "/new/personal", config_path=self.path)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn('default_email = "user@example.com"', text)
        self.assertIn('machine_environment = "personal"', text)
        self.assertIn("[projects]", text)
        self.assertIn('active = ["A", "B"]', text)
        # The other vault entry is intact
        cfg = _load_toml(self.path)
        names = [v["name"] for v in cfg["vaults"]]
        self.assertEqual(sorted(names), ["personal", "work"])


# ─── R-3.10: append a brand-new vault as sole default ────────────────────────


class TestUpsertNew(unittest.TestCase):

    def test_new_name_appended_as_sole_default(self):
        path = _write_tmp_config(CONFIG_TWO_VAULTS)
        try:
            v = upsert_default_vault("research", "/r/vault", config_path=path)
            self.assertTrue(v.default)
            vaults = list_vaults(config_path=path)
            names = sorted(x.name for x in vaults)
            self.assertEqual(names, ["personal", "research", "work"])
            defaults = [x.name for x in vaults if x.default]
            self.assertEqual(defaults, ["research"])
        finally:
            path.unlink()

    def test_bootstrap_into_config_with_scalars_no_vaults(self):
        path = _write_tmp_config(CONFIG_SCALARS_NO_VAULTS)
        try:
            v = upsert_default_vault("personal", "/p/vault", config_path=path)
            self.assertTrue(v.default)
            text = path.read_text(encoding="utf-8")
            # Pre-existing scalars preserved
            self.assertIn('default_email = "u@example.com"', text)
            self.assertIn('machine_environment = "work"', text)
            vaults = list_vaults(config_path=path)
            self.assertEqual(len(vaults), 1)
            self.assertEqual(vaults[0].name, "personal")
            self.assertTrue(vaults[0].default)
        finally:
            path.unlink()


# ─── R-3.8: comment preservation ─────────────────────────────────────────────


class TestCommentPreservation(unittest.TestCase):

    def test_comment_line_preserved(self):
        cfg = "# hand-written note\n" + CONFIG_TWO_VAULTS
        path = _write_tmp_config(cfg)
        try:
            upsert_default_vault("work", "/abs/work-vault", config_path=path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("# hand-written note", text)
        finally:
            path.unlink()


# ─── R-3.13: TOML-safe escaping ──────────────────────────────────────────────


class TestTomlSafeEscaping(unittest.TestCase):

    def test_format_vault_entry_escapes_quotes(self):
        # A value containing a double-quote must not break the TOML.
        entry = _format_vault_entry('ev"il', '/tmp/a"b', default=True)
        # The raw text must contain escaped quotes, not bare ones.
        self.assertIn('\\"', entry)

    def test_escaped_entry_reparses_to_original(self):
        # Write an entry with special chars and confirm it round-trips through
        # the real TOML loader (Python 3.11+ tomllib).
        entry = _format_vault_entry('a"b', '/tmp/c"d', default=True)
        path = _write_tmp_config('default_email = "x@y.z"\n\n' + entry)
        try:
            cfg = _load_toml(path)
            self.assertEqual(cfg["vaults"][0]["name"], 'a"b')
            self.assertEqual(cfg["vaults"][0]["path"], '/tmp/c"d')
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
