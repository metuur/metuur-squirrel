#!/usr/bin/env python3
"""
Integration tests for `squirrel vaults` subcommand group and `--vault NAME`
on existing subcommands (multi-vault-core stories 2.1, 2.2, 2.3, 2.4).

Uses subprocess with HOME overridden so the CLI's hard-coded
`~/.squirrel/config.toml` resolves to a temporary directory.
"""

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SQUIRREL = REPO_ROOT / "squirrel"


def run_cli(*args, home=None, env_extra=None):
    """Run the squirrel CLI with HOME pointed at `home` (a tempdir)."""
    env = os.environ.copy()
    if home is not None:
        env["HOME"] = str(home)
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, str(SQUIRREL), *args]
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


class TestVaultsList(unittest.TestCase):
    """R-4.2 — squirrel vaults list."""

    def test_empty_when_no_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_cli("vaults", "list", home=tmp)
            # No config → friendly message, exit 0
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertIn("no vaults configured", r.stdout)

    def test_lists_after_add(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp)
            vault_dir = home / "vault-a"
            vault_dir.mkdir()
            r = run_cli("vaults", "add", "personal", str(vault_dir), home=tmp)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            r = run_cli("vaults", "list", home=tmp)
            self.assertEqual(r.returncode, 0, msg=r.stderr)
            self.assertIn("personal", r.stdout)
            self.assertIn("(default)", r.stdout)


class TestVaultsAdd(unittest.TestCase):
    """R-4.3 — squirrel vaults add NAME PATH."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        self.vault_a = self.home / "a"
        self.vault_b = self.home / "b"
        self.vault_a.mkdir()
        self.vault_b.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_add_becomes_default(self):
        r = run_cli("vaults", "add", "first", str(self.vault_a), home=self.tmp.name)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("first", r.stdout)
        # Confirm via list
        r = run_cli("vaults", "list", home=self.tmp.name)
        self.assertIn("first", r.stdout)
        self.assertIn("(default)", r.stdout)

    def test_second_add_is_not_default(self):
        run_cli("vaults", "add", "first", str(self.vault_a), home=self.tmp.name)
        run_cli("vaults", "add", "second", str(self.vault_b), home=self.tmp.name)
        r = run_cli("vaults", "list", home=self.tmp.name)
        # Both present
        self.assertIn("first", r.stdout)
        self.assertIn("second", r.stdout)
        # First is still marked default; "(default)" appears exactly once
        self.assertEqual(r.stdout.count("(default)"), 1)

    def test_rejects_duplicate_name(self):
        run_cli("vaults", "add", "x", str(self.vault_a), home=self.tmp.name)
        r = run_cli("vaults", "add", "x", str(self.vault_b), home=self.tmp.name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("already", r.stderr.lower())

    def test_rejects_missing_path(self):
        r = run_cli(
            "vaults", "add", "bad", str(self.home / "no-such-dir"),
            home=self.tmp.name,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not exist", r.stderr)

    def test_rejects_file_instead_of_dir(self):
        not_a_dir = self.home / "afile.txt"
        not_a_dir.write_text("nope")
        r = run_cli("vaults", "add", "bad", str(not_a_dir), home=self.tmp.name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a directory", r.stderr)


class TestVaultsRemoveAndDefault(unittest.TestCase):
    """R-4.4, R-4.5 — squirrel vaults remove and default."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        self.vault_a = self.home / "a"
        self.vault_b = self.home / "b"
        self.vault_a.mkdir()
        self.vault_b.mkdir()
        run_cli("vaults", "add", "a", str(self.vault_a), home=self.tmp.name)
        run_cli("vaults", "add", "b", str(self.vault_b), home=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_remove_non_default(self):
        r = run_cli("vaults", "remove", "b", home=self.tmp.name)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        r = run_cli("vaults", "list", home=self.tmp.name)
        self.assertIn("a", r.stdout)
        self.assertNotIn("\n  b ", r.stdout)  # b removed (rough check)

    def test_remove_default_refused(self):
        r = run_cli("vaults", "remove", "a", home=self.tmp.name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("default", r.stderr)
        self.assertIn("b", r.stderr)  # mentions other available vault

    def test_remove_missing_name(self):
        r = run_cli("vaults", "remove", "ghost", home=self.tmp.name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ghost", r.stderr)

    def test_set_default_switches(self):
        # initially a is default
        r = run_cli("vaults", "default", "b", home=self.tmp.name)
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        r = run_cli("vaults", "list", home=self.tmp.name)
        # Now b is marked default
        lines = [ln for ln in r.stdout.splitlines() if "(default)" in ln]
        self.assertEqual(len(lines), 1)
        self.assertIn("b", lines[0])

    def test_set_default_unknown(self):
        r = run_cli("vaults", "default", "ghost", home=self.tmp.name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ghost", r.stderr)


class TestVaultFlagOnExistingSubcommands(unittest.TestCase):
    """R-5.6 — --vault NAME with unknown vault errors clearly."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        self.vault_a = self.home / "a"
        self.vault_a.mkdir()
        run_cli("vaults", "add", "a", str(self.vault_a), home=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_unknown_vault_errors_clearly(self):
        r = run_cli("status", "--vault", "missing", home=self.tmp.name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("missing", r.stderr)
        self.assertIn("a", r.stderr)  # mentions valid alternatives

    def test_deadlines_unknown_vault_errors(self):
        r = run_cli("deadlines", "--vault", "missing", home=self.tmp.name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("missing", r.stderr)

    def test_dashboard_unknown_vault_errors(self):
        r = run_cli("dashboard", "--vault", "missing", home=self.tmp.name)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("missing", r.stderr)


class TestVaultIndependentSubcommandsUnchanged(unittest.TestCase):
    """R-5.7 — chunk, estimate, install are not vault-aware."""

    def test_chunk_help_has_no_vault_flag(self):
        r = run_cli("chunk", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("--vault", r.stdout)

    def test_estimate_help_has_no_vault_flag(self):
        r = run_cli("estimate", "--help")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("--vault", r.stdout)


if __name__ == "__main__":
    unittest.main()
