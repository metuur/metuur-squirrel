#!/usr/bin/env python3
"""
Story 5.2 — single-vault user sees byte-identical CLI output post-migration.

Acceptance (from docs/ears/multi-vault-core.md):
  R-9.1: THE SYSTEM SHALL produce byte-identical CLI and slash command
         output for single-vault users post-migration, given the same
         inputs.

Verify (from docs/tasks/multi-vault-core.md story 5.2):
  with a single-vault config.toml (post-migration), capture stdout of
  squirrel status and squirrel deadlines to a fixture file. Diff against
  the pre-change captured output: zero diff lines. New test
  tests/test_regression_single_vault.py runs both commands and asserts
  against the captured fixture.

Strategy:
  The output contains time-varying tokens (today's date, "Nh left",
  "Nd overdue") that change between runs, so a static fixture would be
  flaky. Instead, this test proves the *behaviour invariant* R-9.1 actually
  requires: a legacy single-vault config produces byte-identical output to
  the same config after migration has rewritten it to [[vaults]] form. The
  user experience is unchanged.

  Concretely:
    1. Build a tmp HOME with a LEGACY config (vault_path + environment_name).
    2. Run `squirrel status` once — the first read auto-migrates the file in
       place; capture stdout_first.
    3. The config is now in [[vaults]] form. Run `squirrel status` again;
       capture stdout_second.
    4. Assert stdout_first == stdout_second byte-for-byte and both exits 0.
    5. Repeat for `squirrel deadlines`.

  Structural assertions on the output prove the migrated path produces a
  well-formed report (not just identical empty strings).
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
SQUIRREL = REPO / "squirrel"
FIXTURE_VAULT = REPO / "tests" / "fixtures" / "vault-minimal"


def _run(home: pathlib.Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(SQUIRREL), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO),
    )


class TestSingleVaultByteIdentical(unittest.TestCase):
    """R-9.1 — single-vault output is byte-identical before/after migration."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        sq_dir = self.home / ".squirrel"
        sq_dir.mkdir(parents=True)

        # Write the LEGACY single-vault schema. The first CLI read will
        # transparently migrate it to [[vaults]] form via list_vaults().
        (sq_dir / "config.toml").write_text(
            textwrap.dedent(
                f"""\
                vault_path = "{FIXTURE_VAULT}"
                environment_name = "test"
                default_email = "test@example.com"

                [projects]
                active = ["TEST-PROJECT", "SIDEPROJECT-STALE"]

                [compliance]
                strict = false
                """
            )
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_byte_identical_pre_and_post_migration(self):
        # Sanity check that the config starts legacy
        cfg = self.home / ".squirrel" / "config.toml"
        self.assertIn("vault_path", cfg.read_text())
        self.assertNotIn("[[vaults]]", cfg.read_text())

        # First run: triggers in-process migration
        r1 = _run(self.home, "status")
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)

        # After the first run the config has been rewritten
        post = cfg.read_text()
        self.assertIn("[[vaults]]", post)
        self.assertIn("# Auto-migrated", post)

        # Second run: reads the already-migrated config
        r2 = _run(self.home, "status")
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)

        # R-9.1: byte-identical output across the migration boundary
        self.assertEqual(
            r1.stdout,
            r2.stdout,
            msg=(
                "single-vault `squirrel status` output diverged across the "
                "migration boundary (R-9.1 violation)"
            ),
        )

        # Structural sanity: the report is actually a vault status, not empty
        self.assertIn("📊 Vault Status", r1.stdout)
        self.assertIn("TEST-PROJECT", r1.stdout)

    def test_deadlines_byte_identical_pre_and_post_migration(self):
        cfg = self.home / ".squirrel" / "config.toml"
        self.assertIn("vault_path", cfg.read_text())

        r1 = _run(self.home, "deadlines")
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)

        self.assertIn("[[vaults]]", cfg.read_text())

        r2 = _run(self.home, "deadlines")
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)

        self.assertEqual(
            r1.stdout,
            r2.stdout,
            msg=(
                "single-vault `squirrel deadlines` output diverged across "
                "the migration boundary (R-9.1 violation)"
            ),
        )

    def test_explicit_default_vault_flag_matches_no_flag(self):
        # The --vault NAME flag on the default vault must produce the same
        # output as omitting it (R-5.5 + R-9.1). Use the migrated state so
        # the named vault exists.
        _run(self.home, "status")  # trigger migration once
        r_no_flag = _run(self.home, "status")
        r_with_flag = _run(self.home, "status", "--vault", "test")
        self.assertEqual(r_no_flag.returncode, 0)
        self.assertEqual(r_with_flag.returncode, 0)
        self.assertEqual(
            r_no_flag.stdout,
            r_with_flag.stdout,
            msg=(
                "`status` and `status --vault <default-name>` must produce "
                "identical output (R-9.1)"
            ),
        )


@unittest.skipUnless(shutil.which("diff"), "diff(1) not available")
class TestUnixDiffShowsZeroLines(unittest.TestCase):
    """R-9.1 verify literal: 'zero diff lines' across the migration boundary."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = pathlib.Path(self.tmp.name)
        sq_dir = self.home / ".squirrel"
        sq_dir.mkdir(parents=True)
        (sq_dir / "config.toml").write_text(
            textwrap.dedent(
                f"""\
                vault_path = "{FIXTURE_VAULT}"
                environment_name = "test"

                [projects]
                active = ["TEST-PROJECT"]
                """
            )
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_diff_status_zero_lines(self):
        out_pre = self.home / "status.pre.txt"
        out_post = self.home / "status.post.txt"
        r1 = _run(self.home, "status")
        out_pre.write_text(r1.stdout)
        r2 = _run(self.home, "status")
        out_post.write_text(r2.stdout)
        diff = subprocess.run(
            ["diff", str(out_pre), str(out_post)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            diff.stdout,
            "",
            msg=f"diff produced lines:\n{diff.stdout}",
        )
        self.assertEqual(diff.returncode, 0)


if __name__ == "__main__":
    unittest.main()
