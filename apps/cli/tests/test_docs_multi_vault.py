#!/usr/bin/env python3
"""
Stories 6.1 + 6.2 — verify docs cover the multi-vault story.

Acceptance (from docs/ears/multi-vault-core.md):
  R-10.1: THE SYSTEM SHALL document the new [[vaults]] schema in INSTALL.md.
  R-10.2: THE SYSTEM SHALL add a "Multiple vaults" section to
          docs/guides/getting-started.md covering: when to use multiple
          vaults, squirrel vaults add/list/remove/default, and --vault NAME
          on slash commands.
  R-10.3: THE SYSTEM SHALL document the migration behavior (lazy,
          idempotent, the comment marker) in both files above.
"""

import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
INSTALL_MD = REPO / "INSTALL.md"
GETTING_STARTED_MD = REPO / "docs" / "guides" / "getting-started.md"


class TestInstallMdDocumentsMultiVault(unittest.TestCase):
    """R-10.1 / R-10.3 — INSTALL.md covers new schema, vaults CLI, migration."""

    def setUp(self):
        self.text = INSTALL_MD.read_text(encoding="utf-8")

    def test_documents_vaults_array_schema(self):
        self.assertIn(
            "[[vaults]]",
            self.text,
            msg="INSTALL.md must show the [[vaults]] array schema (R-10.1)",
        )
        for key in ("name = ", "path = ", "default = true"):
            with self.subTest(key=key):
                self.assertIn(
                    key,
                    self.text,
                    msg=f"INSTALL.md must show the {key!r} field (R-10.1)",
                )

    def test_documents_machine_environment_rename(self):
        self.assertIn(
            "machine_environment",
            self.text,
            msg=(
                "INSTALL.md must show the environment_name -> "
                "machine_environment rename (R-10.1)"
            ),
        )

    def test_documents_migration_behaviour(self):
        # R-10.3: lazy + idempotent + the # Auto-migrated marker
        for hint in ("Auto-migrated", "migra", "idempotent"):
            with self.subTest(hint=hint):
                self.assertIn(
                    hint,
                    self.text,
                    msg=(
                        f"INSTALL.md must mention {hint!r} when describing "
                        f"the migration behaviour (R-10.3)"
                    ),
                )

    def test_documents_vaults_cli_one_liner(self):
        for cli in (
            "squirrel vaults add",
            "squirrel vaults list",
            "squirrel vaults remove",
            "squirrel vaults default",
        ):
            with self.subTest(cli=cli):
                self.assertIn(
                    cli,
                    self.text,
                    msg=f"INSTALL.md must mention `{cli}` (R-10.1)",
                )


class TestGettingStartedMultiVaultSection(unittest.TestCase):
    """R-10.2 / R-10.3 — getting-started has the Multiple vaults section."""

    def setUp(self):
        self.text = GETTING_STARTED_MD.read_text(encoding="utf-8")

    def test_section_titled_working_with_multiple_workspaces(self):
        pattern = re.compile(
            r"^##\s+\d+\.\s+Working with multiple workspaces\s*$",
            re.MULTILINE,
        )
        self.assertRegex(
            self.text,
            pattern,
            msg=(
                "getting-started.md must have a numbered section titled "
                "'Working with multiple workspaces' (R-10.2)"
            ),
        )

    def test_section_sits_between_first_setup_and_everyday_use(self):
        # Find the line offsets of the three section headings and assert order.
        lines = self.text.splitlines()
        offsets = {"first_setup": None, "multi": None, "everyday": None}
        for i, line in enumerate(lines):
            if re.match(r"^##\s+\d+\.\s+First Setup\s*$", line):
                offsets["first_setup"] = i
            elif re.match(
                r"^##\s+\d+\.\s+Working with multiple workspaces\s*$", line
            ):
                offsets["multi"] = i
            elif re.match(r"^##\s+\d+\.\s+Everyday Use", line):
                offsets["everyday"] = i
        for name, off in offsets.items():
            self.assertIsNotNone(
                off, msg=f"missing section {name!r} in getting-started.md"
            )
        self.assertLess(
            offsets["first_setup"],
            offsets["multi"],
            msg="multi-vault section must come AFTER First Setup",
        )
        self.assertLess(
            offsets["multi"],
            offsets["everyday"],
            msg="multi-vault section must come BEFORE Everyday Use",
        )

    def test_covers_when_to_use_multiple(self):
        # "When to use multiple vaults" subsection or equivalent prose
        self.assertRegex(
            self.text,
            re.compile(r"###\s+When to use multiple vaults", re.MULTILINE),
            msg=(
                "multi-vault section must explain WHEN to use more than one "
                "vault (R-10.2)"
            ),
        )

    def test_covers_vaults_cli(self):
        for cli in (
            "squirrel vaults add",
            "squirrel vaults list",
            "squirrel vaults remove",
            "squirrel vaults default",
        ):
            with self.subTest(cli=cli):
                self.assertIn(
                    cli,
                    self.text,
                    msg=(
                        f"getting-started.md multi-vault section must show "
                        f"`{cli}` (R-10.2)"
                    ),
                )

    def test_covers_vault_flag_on_slash_commands(self):
        self.assertIn(
            "--vault",
            self.text,
            msg=(
                "getting-started.md must explain the --vault NAME flag on "
                "slash commands (R-10.2)"
            ),
        )
        self.assertIn(
            "/sq-init --add-vault",
            self.text,
            msg=(
                "getting-started.md must mention /sq-init --add-vault as the "
                "interactive add path (R-10.2)"
            ),
        )

    def test_says_migration_is_automatic_for_existing_users(self):
        # R-10.2 (...and that migration is automatic for existing users) + R-10.3
        self.assertRegex(
            self.text,
            r"[Mm]igration is automatic",
            msg=(
                "getting-started.md must state migration is automatic for "
                "existing users (R-10.2)"
            ),
        )
        self.assertIn(
            "# Auto-migrated",
            self.text,
            msg=(
                "getting-started.md must mention the # Auto-migrated "
                "comment marker (R-10.3)"
            ),
        )


if __name__ == "__main__":
    unittest.main()
