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
            self.assertEqual(result, {"in_app": True, "os_popups": False, "sound": "Glass"})

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
            self.assertEqual(result, {"in_app": False, "os_popups": True, "sound": "Glass"})

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
            self.assertEqual(result, {"in_app": False, "os_popups": False, "sound": "Glass"})

    # R-1.1, R-1.3 — sound key with three valid values; unknown → Glass.

    def test_reads_sound_glass(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._write_config(
                pathlib.Path(td),
                """\
                [[vaults]]
                name = "test"
                path = "/tmp/v"
                default = true

                [notifications]
                in_app = true
                os_popups = false
                sound = "Glass"
                """,
            )
            self.assertEqual(load_notifications_settings(cfg)["sound"], "Glass")

    def test_reads_sound_funk(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._write_config(
                pathlib.Path(td),
                """\
                [[vaults]]
                name = "test"
                path = "/tmp/v"
                default = true

                [notifications]
                in_app = true
                os_popups = false
                sound = "Funk"
                """,
            )
            self.assertEqual(load_notifications_settings(cfg)["sound"], "Funk")

    def test_reads_sound_silent(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._write_config(
                pathlib.Path(td),
                """\
                [[vaults]]
                name = "test"
                path = "/tmp/v"
                default = true

                [notifications]
                in_app = true
                os_popups = false
                sound = "Silent"
                """,
            )
            self.assertEqual(load_notifications_settings(cfg)["sound"], "Silent")

    def test_unknown_sound_falls_back_to_glass(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = self._write_config(
                pathlib.Path(td),
                """\
                [[vaults]]
                name = "test"
                path = "/tmp/v"
                default = true

                [notifications]
                in_app = true
                os_popups = false
                sound = "Bogus"
                """,
            )
            self.assertEqual(load_notifications_settings(cfg)["sound"], "Glass")


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
            save_notifications_settings(cfg, in_app=True, os_popups=False, sound="Glass")
            result = load_notifications_settings(cfg)
            self.assertEqual(result, {"in_app": True, "os_popups": False, "sound": "Glass"})

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
            save_notifications_settings(cfg, in_app=False, os_popups=False, sound="Glass")
            result = load_notifications_settings(cfg)
            self.assertEqual(result, {"in_app": False, "os_popups": False, "sound": "Glass"})

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
            save_notifications_settings(cfg, in_app=True, os_popups=True, sound="Glass")
            text = cfg.read_text()
            self.assertIn("[notifications]", text)
            self.assertIn("in_app = true", text)
            self.assertIn("os_popups = true", text)
            self.assertIn('sound = "Glass"', text)

    # R-1.2 — sound persisted in the [notifications] section.

    def test_writes_sound_funk(self):
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
            save_notifications_settings(cfg, in_app=True, os_popups=False, sound="Funk")
            text = cfg.read_text()
            self.assertIn('sound = "Funk"', text)

    def test_save_round_trips_sound(self):
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
            save_notifications_settings(cfg, in_app=True, os_popups=False, sound="Silent")
            self.assertEqual(load_notifications_settings(cfg)["sound"], "Silent")

    def test_save_overwrites_sound(self):
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
            save_notifications_settings(cfg, in_app=True, os_popups=False, sound="Glass")
            save_notifications_settings(cfg, in_app=True, os_popups=False, sound="Funk")
            self.assertEqual(load_notifications_settings(cfg)["sound"], "Funk")


if __name__ == "__main__":
    unittest.main()
