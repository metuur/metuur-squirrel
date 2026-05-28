#!/usr/bin/env python3
"""
Story 5.3 — re-migration robustness.

Acceptance (from docs/ears/multi-vault-core.md):
  R-9.3: IF a user reverts to a legacy config.toml after migration (e.g.,
         restores from backup with no [[vaults]]), THE SYSTEM SHALL run
         migration again on next load.
  R-9.4: THE SYSTEM SHALL not require any user to manually run a migration
         command.
  R-9.5: WHILE migration is running, THE SYSTEM SHALL not produce output to
         stderr (it is a silent transparent rewrite). The single observable
         artifact is the # Auto-migrated <ISO-date> comment in the rewritten
         file.

Verify (from docs/tasks/multi-vault-core.md story 5.3):
  take a migrated config, manually overwrite it with the legacy form
  (`vault_path = ...`), load via any CLI command, observe that [[vaults]]
  is rebuilt and the `# Auto-migrated` comment is present. No stderr output
  during migration.
"""

import contextlib
import io
import pathlib
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))

from config_loader import (  # noqa: E402  (sys.path mutated above)
    list_vaults,
    migrate_legacy,
)


LEGACY_CONFIG = textwrap.dedent(
    """\
    vault_path = "/tmp"
    environment_name = "personal"
    default_email = "u@x"

    [compliance]
    strict = false
    """
)


class TestRemigrationAfterLegacyRevert(unittest.TestCase):
    """R-9.3 — migration runs again when the user reverts to the legacy form."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)
        self.cfg = self.tmp_path / "config.toml"
        self.state_dir = self.tmp_path / "state"

    def tearDown(self):
        self.tmp.cleanup()

    def test_legacy_revert_triggers_fresh_migration(self):
        # Step 1: initial migration produces [[vaults]] + auto-migrated comment
        self.cfg.write_text(LEGACY_CONFIG)
        migrate_legacy(config_path=self.cfg, state_dir=self.state_dir)
        migrated_once = self.cfg.read_text()
        self.assertIn("[[vaults]]", migrated_once)
        self.assertIn("# Auto-migrated", migrated_once)

        # Step 2: user restores legacy form from backup (different env name)
        self.cfg.write_text(LEGACY_CONFIG.replace("personal", "work"))
        self.assertNotIn("[[vaults]]", self.cfg.read_text())

        # Step 3: next load via list_vaults must transparently re-migrate
        vaults = list_vaults(config_path=self.cfg)
        rewritten = self.cfg.read_text()
        self.assertIn("[[vaults]]", rewritten)
        self.assertIn("# Auto-migrated", rewritten)
        self.assertEqual(vaults[0].name, "work")
        self.assertTrue(vaults[0].default)


class TestMigrationSilentOnStderr(unittest.TestCase):
    """R-9.5 — migration produces zero stderr output (silent rewrite)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)
        self.cfg = self.tmp_path / "config.toml"
        self.state_dir = self.tmp_path / "state"
        self.cfg.write_text(LEGACY_CONFIG)

    def tearDown(self):
        self.tmp.cleanup()

    def test_migrate_legacy_writes_nothing_to_stderr(self):
        buf_err = io.StringIO()
        with contextlib.redirect_stderr(buf_err):
            ran = migrate_legacy(
                config_path=self.cfg, state_dir=self.state_dir
            )
        self.assertTrue(ran)
        self.assertEqual(
            buf_err.getvalue(),
            "",
            msg="R-9.5: migration must be silent on stderr",
        )

    def test_list_vaults_migrates_without_stderr(self):
        # The realistic call path: any CLI command -> list_vaults -> lazy migrate
        buf_err = io.StringIO()
        with contextlib.redirect_stderr(buf_err):
            vaults = list_vaults(config_path=self.cfg)
        self.assertEqual(vaults[0].name, "personal")
        self.assertEqual(
            buf_err.getvalue(),
            "",
            msg="R-9.5: implicit migration during list_vaults must be silent",
        )


class TestNoManualMigrationCommandRequired(unittest.TestCase):
    """R-9.4 — migration happens automatically on the first read; no manual command."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self.tmp.name)
        self.cfg = self.tmp_path / "config.toml"
        self.state_dir = self.tmp_path / "state"
        self.cfg.write_text(LEGACY_CONFIG)

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_list_vaults_does_the_migration(self):
        # No explicit migrate_legacy call by the caller — just list_vaults.
        # The user never has to know migration exists.
        before = self.cfg.read_text()
        self.assertNotIn("[[vaults]]", before)
        self.assertNotIn("# Auto-migrated", before)

        vaults = list_vaults(config_path=self.cfg)
        after = self.cfg.read_text()

        self.assertEqual(vaults[0].name, "personal")
        self.assertIn("[[vaults]]", after)
        self.assertIn("# Auto-migrated", after)


if __name__ == "__main__":
    unittest.main()
