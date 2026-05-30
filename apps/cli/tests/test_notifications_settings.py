#!/usr/bin/env python3
"""
Story 5.1 — test load_notifications_settings / save_notifications_settings
in lib/config_loader.py.

Acceptance: R-5.4
"""

import pathlib
import sys
import tempfile
import textwrap
import unittest

_LIB = pathlib.Path(__file__).resolve().parent.parent / "lib"
sys.path.insert(0, str(_LIB))

from config_loader import (  # noqa: E402
    load_notifications_settings,
    save_notifications_settings,
)


class TestLoadNotificationsSettings(unittest.TestCase):
    def _write_config(self, tmp: pathlib.Path, text: str) -> pathlib.Path:
        cfg = tmp / "config.toml"
        cfg.write_text(textwrap.dedent(text))
        return cfg

    def test_defaults_when_section_absent(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._write_config(
                pathlib.Path(td),
                """\
                [[vaults]]
                name = "test"
                path = "/tmp/v"
                default = true
                """,
            )
            result = load_notifications_settings(cfg)
            self.assertEqual(result, {"in_app": True, "os_popups": False})

    def test_reads_existing_section(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._write_config(
                pathlib.Path(td),
                """\
                [[vaults]]
                name = "test"
                path = "/tmp/v"
                default = true

                [notifications]
                in_app = false
                os_popups = true
                """,
            )
            result = load_notifications_settings(cfg)
            self.assertEqual(result, {"in_app": False, "os_popups": True})

    def test_partial_section_fills_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._write_config(
                pathlib.Path(td),
                """\
                [[vaults]]
                name = "test"
                path = "/tmp/v"
                default = true

                [notifications]
                in_app = false
                """,
            )
            result = load_notifications_settings(cfg)
            self.assertEqual(result, {"in_app": False, "os_popups": False})


class TestSaveNotificationsSettings(unittest.TestCase):
    def test_writes_section_to_config(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = pathlib.Path(td) / "config.toml"
            cfg.write_text(
                textwrap.dedent("""\
                    [[vaults]]
                    name = "test"
                    path = "/tmp/v"
                    default = true
                """)
            )
            save_notifications_settings(cfg, in_app=True, os_popups=False)
            result = load_notifications_settings(cfg)
            self.assertEqual(result, {"in_app": True, "os_popups": False})

    def test_overwrites_existing_section(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = pathlib.Path(td) / "config.toml"
            cfg.write_text(
                textwrap.dedent("""\
                    [[vaults]]
                    name = "test"
                    path = "/tmp/v"
                    default = true

                    [notifications]
                    in_app = true
                    os_popups = true
                """)
            )
            save_notifications_settings(cfg, in_app=False, os_popups=False)
            result = load_notifications_settings(cfg)
            self.assertEqual(result, {"in_app": False, "os_popups": False})

    def test_write_is_atomic(self):
        """save_notifications_settings must produce a valid TOML file."""
        with tempfile.TemporaryDirectory() as td:
            cfg = pathlib.Path(td) / "config.toml"
            cfg.write_text(
                textwrap.dedent("""\
                    [[vaults]]
                    name = "test"
                    path = "/tmp/v"
                    default = true
                """)
            )
            save_notifications_settings(cfg, in_app=True, os_popups=True)
            text = cfg.read_text()
            self.assertIn("[notifications]", text)
            self.assertIn("in_app = true", text)
            self.assertIn("os_popups = true", text)


if __name__ == "__main__":
    unittest.main()
